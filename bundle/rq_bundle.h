#ifndef BUNDLE_RQ_BUNDLE_H
#define BUNDLE_RQ_BUNDLE_H

#ifdef BUNDLE_CLEANUP_BACKGROUND
#ifndef BUNDLE_CLEANUP_SLEEP
#error BUNDLE_CLEANUP_SLEEP NOT DEFINED
#endif
#endif

#if defined BUNDLE_CIRCULAR_BUNDLE
#include "circular_bundle.h"
#elif defined BUNDLE_LINKED_BUNDLE
#include "linked_bundle.h"
#elif defined BUNDLE_UNSAFE_BUNDLE
#include "unsafe_linked_bundle.h"
#else
#error NO BUNDLE TYPE DEFINED
#endif

// NOTES ON IMPLEMENTATION DETAILS.
// --------------------------------
// The active RQ array is now the number of processes allowed to accomodate
// any number of range query threads. Snapshots are still taken by iterating
// over the list. For now, we iterate over the entire list but there is room
// for optimizations here (i.e., maintin number of active RQs and map the tid
// to the next slot in array).

// Ensures consistent view of data structure for range queries by augmenting
// updates to keep track of their linearization points and observe any active
// range queries.
template <typename K, typename V, typename NodeType, typename DataStructure,
          typename RecordManager, bool logicalDeletion,
          bool canRetireNodesLogicallyDeletedByOtherProcesses>
class RQProvider {
 private:
#define __THREAD_DATA_SIZE 1024
  // Used to announce an active range query and its linearization point.
  union __rq_thread_data {
    struct {
      volatile timestamp_t rq_lin_time;
      volatile char pad0[PREFETCH_SIZE_BYTES];
      std::atomic<bool> rq_flag;
#ifdef BUNDLE_TIMESTAMP_RELAXATION
      volatile char pad1[PREFETCH_SIZE_BYTES];
      volatile long local_timestamp;
#endif
    } data;
    volatile char bytes[__THREAD_DATA_SIZE];
  } __attribute__((aligned(__THREAD_DATA_SIZE)));

  // Timestamp used by range queries to linearize accesses.
  std::atomic<timestamp_t> curr_timestamp_;
  volatile char pad0[PREFETCH_SIZE_BYTES];
  // Array of RQ announcements. One per thread.
  __rq_thread_data *rq_thread_data_;
  // Number of processes concurrently operating on the data structure.
  const int num_processes_;

  DataStructure *ds_;
  RecordManager *const recmgr_;

  int init_[MAX_TID_POW2] = {
      0,
  };

// Metadata for cleaning up with an independent thread.
#ifdef BUNDLE_CLEANUP_BACKGROUND
  struct cleanup_args {
    std::atomic<bool> *const stop;
    DataStructure *const ds;
    int tid;
  };

  pthread_t cleanup_thread_;
  struct cleanup_args *cleanup_args_;
  std::atomic<bool> stop_cleanup_;
#endif

 public:
  RQProvider(const int num_processes, DataStructure *ds, RecordManager *recmgr)
      : num_processes_(num_processes), ds_(ds), recmgr_(recmgr) {
    rq_thread_data_ = new __rq_thread_data[num_processes];
    for (int i = 0; i < num_processes; ++i) {
      rq_thread_data_[i].data.rq_lin_time = BUNDLE_NULL_TIMESTAMP;
      rq_thread_data_[i].data.rq_flag = false;
    }
    curr_timestamp_ = BUNDLE_MIN_TIMESTAMP;

#ifdef BUNDLE_CLEANUP_BACKGROUND
    cleanup_args_ = new cleanup_args{&stop_cleanup_, ds_, num_processes_ - 1};
    if (pthread_create(&cleanup_thread_, nullptr, cleanup_run,
                       (void *)cleanup_args_)) {
      cerr << "ERROR: could not create thread" << endl;
      exit(-1);
    }
    std::stringstream ss;
    ss << "Cleanup started: 0x" << std::hex << cleanup_thread_ << std::endl;
    std::cout << ss.str() << std::flush;
#endif
  }

  ~RQProvider() {
#ifdef BUNDLE_CLEANUP_BACKGROUND
    std::cout << "Stopping cleanup..." << std::endl << std::flush;
    stop_cleanup_ = true;
    if (pthread_join(cleanup_thread_, nullptr)) {
      cerr << "ERROR: could not join thread" << endl;
      exit(-1);
    }
    delete cleanup_args_;
#endif
    delete[] rq_thread_data_;
  }

  // Initializes a thread and registers as an range query thread if it will
  // perform range queries.
  void initThread(const int tid) {
    if (init_[tid])
      return;
    else
      init_[tid] = !init_[tid];
  }

  void deinitThread(const int tid) {
    if (!init_[tid])
      return;
    else
      init_[tid] = !init_[tid];
  }

  void initBundle(int tid, Bundle<NodeType> &bundle, long k) {
    // bundle = Bundle<NodeType>();

    SOFTWARE_BARRIER;
  }

  void deinitBundle(int tid, Bundle<NodeType> *bundle) { delete bundle; }

  inline void physical_deletion_succeeded(const int tid,
                                          NodeType *const *const deletedNodes) {
    int i;
    for (i = 0; deletedNodes[i]; ++i) {
      recmgr_->retire(tid, deletedNodes[i]);
    }
  }

#define BUNDLE_INIT_CLEANUP(provider) \
  const timestamp_t ts = provider->get_oldest_active_rq();
#define BUNDLE_CLEAN_BUNDLE(bundle) bundle->reclaimEntries(ts)

  // Creates a snapshot of the current state of active RQs.
  inline timestamp_t get_oldest_active_rq() {
    timestamp_t oldest_active = curr_timestamp_;
    timestamp_t curr_rq;
    for (int i = 0; i < num_processes_; ++i) {
      while (rq_thread_data_[i].data.rq_flag == true)
        ;  // Wait until RQ linearizes itself.
      curr_rq = rq_thread_data_[i].data.rq_lin_time;
      if (curr_rq != BUNDLE_NULL_TIMESTAMP && curr_rq < oldest_active) {
        oldest_active = curr_rq;  // Update oldest.
      }
    }
    return oldest_active;
  }

  void startCleanup() {}

  void stopCleanup() {}

 private:
#ifdef BUNDLE_CLEANUP_BACKGROUND
  static void *cleanup_run(void *args) {
    std::cout << "Staring cleanup" << std::endl << std::flush;
    struct cleanup_args *c = (struct cleanup_args *)args;
    long i = 0;
    while (!(*(c->stop))) {
      usleep(BUNDLE_CLEANUP_SLEEP);
      c->ds->cleanup(c->tid);
    }
    pthread_exit(nullptr);
  }
#endif

  inline timestamp_t get_update_lin_time(int tid) {
#ifndef BUNDLE_UNSAFE_BUNDLE
#ifdef BUNDLE_TIMESTAMP_RELAXATION
    if (((rq_thread_data_[tid].data.local_timestamp + 1) %
         BUNDLE_TIMESTAMP_RELAXATION) == 0) {
      ++rq_thread_data_[tid].data.local_timestamp;
      return curr_timestamp_.fetch_add(1) + 1;
    } else {
      ++rq_thread_data_[tid].data.local_timestamp;
      return curr_timestamp_;
    }
#else
    return curr_timestamp_.fetch_add(1) + 1;
#endif
#else
    return BUNDLE_MIN_TIMESTAMP;
#endif
  }

 public:
  // Write the range query linearization time so updates do not recycle any
  // edges needed by this range query.
  inline timestamp_t start_traversal(int tid) {
// Atomic loads on rq_flag have acquire semantics.
#ifndef BUNDLE_UNSAFE_BUNDLE
    rq_thread_data_[tid].data.rq_flag = true;
    rq_thread_data_[tid].data.rq_lin_time = curr_timestamp_;
    rq_thread_data_[tid].data.rq_flag = false;
    return rq_thread_data_[tid].data.rq_lin_time;
#else
    return BUNDLE_MIN_TIMESTAMP;
#endif
  }

  // Reset the range query linearization time so that updates may recycle an
  // edge we needed.
  inline void end_traversal(int tid) {
#ifndef BUNDLE_UNSAFE_BUNDLE
    rq_thread_data_[tid].data.rq_lin_time = BUNDLE_NULL_TIMESTAMP;
#endif
  }

  // Prepares bundles by calling prepare on each provided bundle-pointer pair.
  inline void prepare_bundles(Bundle<NodeType> **bundles,
                              NodeType *const *const ptrs) {
    // PENDING_TIMESTAMP blocks all RQs that might see the update, ensuring that
    // the update is visible (i.e., get and RQ have the same linearization
    // point).
    int i = 0;
    Bundle<NodeType> *curr_bundle = bundles[0];
    NodeType *curr_ptr = ptrs[0];
    while (curr_bundle != nullptr) {
      curr_bundle->prepare(curr_ptr);
#ifdef BUNDLE_CLEANUP_UPDATE
      curr_bundle->reclaimEntries(get_oldest_active_rq());
#endif
      ++i;
      curr_bundle = bundles[i];
      curr_ptr = ptrs[i];
    }
  }

  inline void finalize_bundles(Bundle<NodeType> **bundles, timestamp_t ts) {
    int i = 0;
    Bundle<NodeType> *curr_bundle = bundles[0];
    while (curr_bundle != nullptr) {
      curr_bundle->finalize(ts);
      ++i;
      curr_bundle = bundles[i];
    }
  }

  // Find and update the newest reference in the predecesor's bundle. If this
  // operation is an insert, then the new nodes bundle must also be
  // initialized. Any node whose bundle is passed here must be locked.
  template <typename T>
  inline timestamp_t linearize_update_at_write(const int tid,
                                               T volatile *const lin_addr,
                                               const T &lin_newval) {
    // Get update linearization timestamp.
    timestamp_t lin_time = get_update_lin_time(tid);
    *lin_addr = lin_newval;  // Original linearization point.
    SOFTWARE_BARRIER;
    return lin_time;
  }
};

#endif