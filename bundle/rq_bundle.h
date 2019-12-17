#ifndef RQ_BUNDLE_H
#define RQ_BUNDLE_H

#include <pthread.h>
#include <sys/types.h>
#include <atomic>
#include <mutex>
#include "common_bundle.h"
#include "plaf.h"
#include "rq_debugging.h"

#define CPU_RELAX asm volatile("pause\n" ::: "memory")
#define BUNDLE_CLEANUP_SLEEP 0

#define DEBUG_PRINT(str)                         \
  if ((i + 1) % 10000 == 0) {                    \
    std::cout << str << std::endl << std::flush; \
  }                                              \
  ++i;

enum op {
  NOP,
  INSERT,
  REMOVE
};

template <typename NodeType>
class BundleEntry {
 public:
  volatile timestamp_t ts_;
  NodeType *volatile ptr_;
  BundleEntry *volatile next_;
  volatile timestamp_t deleted_ts_;
  op op_;

  explicit BundleEntry(timestamp_t ts, NodeType *ptr, BundleEntry *next, op o)
      : ts_(ts), ptr_(ptr), next_(next), op_(o) {
    deleted_ts_ = BUNDLE_NULL_TIMESTAMP;
  }

  void set_ts(const timestamp_t ts) { ts_ = ts; }
  void set_ptr(NodeType *const ptr) { ptr_ = ptr; }
  void set_next(BundleEntry *const next) { next_ = next; }
  void mark(timestamp_t ts) { deleted_ts_ = ts; }
  timestamp_t marked() { return deleted_ts_; }

  inline void validate() {
    if (ts_ < next_->ts_) {
      std::cout << "Invalid bundle" << std::endl;
      exit(1);
    }
  }
};

// A bundle has two sources of sycnrhonization. The first is the lock that
// protects the bundle head and ensures that two updates synchronize correctly.
// It is primarily used to make sure that the list maintains linearization time
// order. The second is the timestamp in a bundle entry and ensures that
// concurrent range queries are linearized correctly.
template <typename NodeType>
class Bundle {
 private:
  std::atomic<BundleEntry<NodeType> *> head_;
  BundleEntry<NodeType> *volatile tail_;
  volatile int updates = 0;
  BundleEntry<NodeType> *volatile last_recycled = nullptr;
  volatile int oldest_edge = 0;

 public:
  explicit Bundle(long k) {
    tail_ = new BundleEntry<NodeType>(BUNDLE_NULL_TIMESTAMP, nullptr,
                                      (BundleEntry<NodeType> * volatile) k, NOP);
    head_ = tail_;
  }

  ~Bundle() {
    BundleEntry<NodeType> *curr = head_;
    BundleEntry<NodeType> *next;
    while (curr != tail_) {
      next = curr->next_;
      delete curr;
      curr = next;
    }
    delete tail_;
  }

  inline BundleEntry<NodeType> *getHead() { return head_; }

  void markAllEntries() {
    BundleEntry<NodeType> *curr = head_;
    while (curr != tail_) {
      curr->mark(-1);
      curr = curr->next_;
    }
  }

  // Returns a reference to the node that immediately followed at timestamp ts.
  inline NodeType *volatile getPtrByTimestamp(timestamp_t ts) {
    // Start at head and work backwards until edge is found.
    BundleEntry<NodeType> *curr = head_;
    long i = 0;
    while (curr->ts_ == BUNDLE_PENDING_TIMESTAMP) {
       // DEBUG_PRINT("getPtrByTimestamp");
      CPU_RELAX;
    }
    while (curr != tail_ && curr->ts_ > ts) {
      assert(curr->ts_ != BUNDLE_NULL_TIMESTAMP);
      curr = curr->next_;
    }
    if (curr->marked()) {
      std::cout << dump(0) << std::flush;
      exit(1);
    }
    return curr->ptr_;
  }

  // Inserts a new rq_bundle_node at the head of the bundle.
  inline void insertAtHead(BundleEntry<NodeType> *const new_entry) {
    BundleEntry<NodeType> *expected;
    while (true) {
      expected = head_;
      new_entry->next_ = expected;
      long i = 0;
      while (expected->ts_ == BUNDLE_PENDING_TIMESTAMP) {
         // DEBUG_PRINT("insertAtHead");
        CPU_RELAX;
      }
      if (head_.compare_exchange_weak(expected, new_entry)) {
        ++updates;
        return;
      }
    }
  }

  // [UNSAFE] Returns the number of bundle entries.
  int getSize() {
    int size = 0;
    BundleEntry<NodeType> *curr = head_;
    while (curr != tail_) {
      if (curr->marked()) {
        std::cout << "taking a dump" << std::endl << std::flush;
        std::cout << dump(0) << std::flush;
        exit(1);
      }
      ++size;
      curr = curr->next_;
      if (curr == nullptr) {
        std::cout << dump(0) << std::flush;
        exit(1);
      }
    }
    return size;
  }

  // Reclaims any edges that are older than ts. At the moment this should be
  // ordered before adding a new entry to the bundle.
  inline void reclaimEntries(timestamp_t ts) {
    // Obtain a reference to the pred non-reclaimable entry and first
    // reclaimable one.
    BundleEntry<NodeType> *pred = head_;
    long i = 0;
    while (pred->ts_ == BUNDLE_PENDING_TIMESTAMP) {
       // DEBUG_PRINT("reclaimEntries");
      CPU_RELAX;
    }
    SOFTWARE_BARRIER;
    BundleEntry<NodeType> *curr = pred->next_;
    if (pred == tail_ || curr == tail_) {
      return;  // Nothing to do.
    }

    // If there are no active RQs then we can recycle all edges, but the
    // newest (i.e., head). Similarly if the oldest active RQ is newer than
    // the newest entry, we can reclaim all older entries.
    if (ts == BUNDLE_NULL_TIMESTAMP || pred->ts_ <= ts) {
      pred->next_ = tail_;
    } else {
      // Traverse from head and remove nodes that are lower than ts.
      while (curr != tail_ && curr->ts_ > ts) {
        pred = curr;
        curr = curr->next_;
      }
      if (curr != tail_) {
        // Curr points to the entry required by the oldest timestamp. This entry
        // will become the last entry in the bundle.
        pred = curr;
        curr = curr->next_;
        pred->next_ = tail_;
      }
    }
    last_recycled = curr;
    oldest_edge = pred->ts_;

// Reclaim nodes.
    assert(curr != head_ && pred->next_ == tail_);
    while (curr != tail_) {
      pred = curr;
      curr = curr->next_;
      pred->mark(ts);
#ifndef BUNDLE_CLEANUP_NO_FREE
      delete pred;
#endif
    }
    if (curr != tail_) {
      std::cout << curr << std::endl;
      std::cout << dump(ts) << std::flush;
      exit(1);
    }
  }

  string __attribute__((noinline)) dump(timestamp_t ts) {
    BundleEntry<NodeType> *curr = head_;
    std::stringstream ss;
    ss << "(ts=" << ts << ") : ";
    long i = 0;
    while (curr != nullptr && curr != tail_) {
      ss << "<" << curr->ts_ << "," << curr->ptr_ << "," << curr->next_ << ">"
         << "-->";
      curr = curr->next_;
    }
    if (curr == tail_) {
      ss << "(tail)<" << curr->ts_ << "," << curr->ptr_ << ","
         << (long)curr->next_ << ">";
    } else {
      ss << "(unexpected end)";
    }
    ss << " [updates=" << updates << ", last_recycled=" << last_recycled
       << ", oldest_edge=" << oldest_edge << "]" << std::endl;
    return ss.str();
  }
};

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

  struct cleanup_args {
    std::atomic<bool> *const stop;
    DataStructure *const ds;
    int tid;
  };

  pthread_t cleanup_thread_;
  struct cleanup_args *cleanup_args_;
  std::atomic<bool> stop_cleanup_;

 public:
  RQProvider(const int num_processes, DataStructure *ds, RecordManager *recmgr)
      : num_processes_(num_processes), ds_(ds), recmgr_(recmgr) {
    rq_thread_data_ = new __rq_thread_data[num_processes];
    for (int i = 0; i < num_processes; ++i) {
      rq_thread_data_[i].data.rq_lin_time = BUNDLE_NULL_TIMESTAMP;
      rq_thread_data_[i].data.rq_flag = false;
    }
    curr_timestamp_ = BUNDLE_MIN_TIMESTAMP;
  }

  ~RQProvider() { delete[] rq_thread_data_; }

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

  void initBundle(int tid, Bundle<NodeType> *volatile *bundle, long k) {
    *bundle = new Bundle<NodeType>(k);
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

#ifdef BUNDLE_CLEANUP
#define BUNDLE_INIT_CLEANUP(provider)                      \
  const timestamp_t ts = provider->get_oldest_active_rq();
#define BUNDLE_CLEAN_BUNDLE(bundle) bundle->reclaimEntries(ts)
#else
#define BUNDLE_INIT_CLEANUP(x)
#define BUNDLE_CLEAN_BUNDLE(x)
#endif

  // Creates a snapshot of the current state of active RQs.
  inline timestamp_t get_oldest_active_rq() {
    timestamp_t oldest_active = BUNDLE_MAX_TIMESTAMP;
    timestamp_t curr_rq;
    for (int i = 0; i < num_processes_; ++i) {
      while (rq_thread_data_[i].data.rq_flag == true)
        ;  // Wait until RQ linearizes itself.
      curr_rq = rq_thread_data_[i].data.rq_lin_time;
      if (curr_rq != BUNDLE_NULL_TIMESTAMP) {
        if (curr_rq < oldest_active) {
          oldest_active = curr_rq;  // Update oldest.
        }
      }
    }
    // Set oldest to NULL_TIMESTAMP if there are no active RQs.
    if (oldest_active == BUNDLE_MAX_TIMESTAMP) {
      oldest_active = BUNDLE_NULL_TIMESTAMP;
    }
    return oldest_active;
  }

  void startCleanup() {
    cleanup_args_ = new cleanup_args{&stop_cleanup_, ds_, num_processes_ - 1};
    if (pthread_create(&cleanup_thread_, nullptr, cleanup_run,
                       (void *)cleanup_args_)) {
      cerr << "ERROR: could not create thread" << endl;
      exit(-1);
    }
    std::stringstream ss;
    ss << "Cleanup started: 0x" << std::hex << pthread_self() << std::endl;
    std::cout << ss.str() << std::flush;
  }

  void stopCleanup() {
    std::cout << "Stopping cleanup..." << std::endl << std::flush;
    stop_cleanup_ = true;
    if (pthread_join(cleanup_thread_, nullptr)) {
      cerr << "ERROR: could not join thread" << endl;
      exit(-1);
    }
    delete cleanup_args_;
  }

 private:
  static void *cleanup_run(void *args) {
    std::cout << "Staring cleanup" << std::endl << std::flush;
    struct cleanup_args *c = (struct cleanup_args *)args;
    long i = 0;
    while (!(*(c->stop))) {
      usleep(BUNDLE_CLEANUP_SLEEP);
       // DEBUG_PRINT("cleanup_run");
      c->ds->cleanup(c->tid);
    }
    // Final cleanup.
    c->ds->cleanup(c->tid);
    pthread_exit(nullptr);
  }

  inline timestamp_t get_update_lin_time(int tid) {
    assert(curr_timestamp_ >= 0);
#ifdef BUNDLE_TIMESTAMP_RELAXATION
    if ((rq_thread_data_[tid].data.local_timestamp %
             BUNDLE_TIMESTAMP_RELAXATION -
         1) == 0) {
      return curr_timestamp_.fetch_add(1);
    } else {
      ++rq_thread_data_[tid].data.local_timestamp;
    }
#else
    return curr_timestamp_.fetch_add(1);
#endif
  }

 public:
  // Write the range query linearization time so updates do not recycle any
  // edges needed by this range query.
  inline timestamp_t start_traversal(int tid) {
    // Atomic loads on rq_flag have acquire semantics.
    rq_thread_data_[tid].data.rq_flag = true;
    rq_thread_data_[tid].data.rq_lin_time = curr_timestamp_;
    rq_thread_data_[tid].data.rq_flag = false;
    return rq_thread_data_[tid].data.rq_lin_time;
  }

  // Reset the range query linearization time so that updates may recycle an
  // edge we needed.
  inline void end_traversal(int tid) {
    rq_thread_data_[tid].data.rq_lin_time = BUNDLE_NULL_TIMESTAMP;
  }

  // Find and update the newest reference in the predecesor's bundle. If this
  // operation is an insert, then the new nodes bundle must also be
  // initialized. Any node whose bundle is passed here must be locked.
  template <typename T>
  inline T linearize_update_at_write(const int tid, T volatile *const lin_addr,
                                     const T &lin_newval,
                                     Bundle<NodeType> *const *const bundles,
                                     NodeType *const *const ptrs, op o) {
    // PENDING_TIMESTAMP blocks all RQs that might see the update, ensuring that
    // the update is visible (i.e., get and RQ have the same linearization
    // point).
    int i = 0;
    Bundle<NodeType> *curr_bundle = bundles[i];
    BundleEntry<NodeType> *entries[BUNDLE_MAX_BUNDLES_UPDATED + 1] = {
        nullptr,
    };
    while (curr_bundle != nullptr) {
      entries[i] =
          new BundleEntry<NodeType>(BUNDLE_PENDING_TIMESTAMP, ptrs[i], nullptr, o);
      curr_bundle->insertAtHead(entries[i]);
      curr_bundle = bundles[++i];
    }
    SOFTWARE_BARRIER;

    // Get update linearization timestamp.
    timestamp_t lin_time = get_update_lin_time(tid);
    SOFTWARE_BARRIER;
    *lin_addr = lin_newval;  // Original linearization point.
    SOFTWARE_BARRIER;

    // Unblock waiting RQs.
    i = 0;
    BundleEntry<NodeType> *curr_entry = entries[i];
    while (curr_entry != nullptr) {
      curr_entry->set_ts(lin_time);
      curr_entry->validate();
      curr_entry = entries[++i];
    }
  }
};

#endif  // RQ_BUNDLE_H