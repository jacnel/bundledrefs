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
#define BUNDLE_INIT_CAPACITY 5


#define NORMAL_STATE 0
#define PENDING_STATE 1
#define RESIZE_STATE 2
#define RECLAIM_STATE 4
#define RQ_STATE 8

#define DEBUG_PRINT(str)                         \
  if ((i + 1) % 10000 == 0) {                    \
    std::cout << str << std::endl << std::flush; \
  }                                              \
  ++i;

enum op { NOP, INSERT, REMOVE };
// Stores pointers to nodes and associated timestamps.

template <typename NodeType>
class Bundle : public BundleInterface<NodeType> {
 private:
  // Entry.
  struct BundleEntry {
    NodeType *ptr_;
    timestamp_t ts_;
  };

  // Entry array and metadata.
  std::atomic<int> state_;
  int base_;                       // Index of oldest entry.
  int curr_;                       // Index of newest entry.
  int capacity_;                   // Maximum number of entries.
  std::atomic<int> rqs_;           // Number of RQs using bundle.
  struct BundleEntry *volatile entries_;  // Bundle entry array

  // Doubles the capacity of the bundle. Only called when a new entry is added,
  // meaning no updates will be lost although some cleanup may be missed.
  void grow() {
    int expected;
    assert(!(state_ & RESIZE_STATE));
    while (true) {
      while (state_ & (RECLAIM_STATE | RQ_STATE))
        ;  // Wait for a concurrent reclaimer or rq.
      // Move state from pending to pending and resizing to block reclaimers and
      // range queries.
      expected = state_;
      if (state_.compare_exchange_weak(expected,
                                       PENDING_STATE | RESIZE_STATE)) {
        break;
      }
    }

    BundleEntry *new_entries = new BundleEntry[capacity_ * 2];
    int i = base_;
    int end = curr_;
    if (i > end) {
      // Buffer wraps so take into account.
      end = capacity_ + end;
    }
    for (; i < end; ++i) {
      // Copy entries to new array.
      new_entries[i] = entries_[i % capacity_];
    }

    // Finish the resize.
    capacity_ = capacity_ * 2;
    SOFTWARE_BARRIER;
    BundleEntry *old_entries = entries_;  // Swap entry arrays.
    entries_ = new_entries;
    delete[] old_entries;

    state_.fetch_and(~RESIZE_STATE);
  }

  void shrink() {
    // TODO
  }

 public:
  // Empty bundle with initial capacity.
  explicit Bundle()
      : state_(NORMAL_STATE),
        base_(0),
        curr_(-1),
        capacity_(BUNDLE_INIT_CAPACITY) {
    entries_ = new BundleEntry[BUNDLE_INIT_CAPACITY];
  }

  ~Bundle() { delete[] entries_; }

  // Returns a reference to the node that satisfies the snapshot at the given
  // timestamp. If all
  inline NodeType *getPtrByTimestamp(timestamp_t ts) override {
    // NOTE: Range queries may continuously block updaters from resizing, but
    // this is expected to be common.
    int prev_rqs = rqs_.fetch_add(1);
    int expected;
    // If there is an ongoing RQ, then we do not need to check state.
    while (prev_rqs == 0) {
      while (state_ & RESIZE_STATE)
        ;  // Wait for ongoing resize.
      expected = state_;
      if (!(expected & RESIZE_STATE) &&
          state_.compare_exchange_weak(expected, expected | RQ_STATE)) {
        break;  // Resize will not happen while RQ is active on this bundle.
      }
    }
    int i = curr_;
    int end = base_;  // NOTE: We don't have to worry about the base changing
                      // because we will always find our entry before the base,
                      // or the base will not be changed.
    if (end > i) {
      // Buffer wraps so take into account.
      i = capacity_ + i;
    }

    // Locate first entry that satisfies snapshot, starting from newest.
    NodeType *ptr = nullptr;
    for (; i >= end; --i) {
      if (entries_[i % capacity_].ts_ <= ts) {
        ptr = entries_[i % capacity_].ptr_;
      }
    }

    if (rqs_.fetch_sub(1) == 0) {
      state_.fetch_and(~RQ_STATE);
    }
    return ptr;
  }

  // [UNSAFE]. Returns the number of entries in the bundle.
  inline int getSize() override {
    if (base_ > curr_) {
      return (capacity_ - base_) + curr_;
    } else {
      return curr_ - base_;
    }
  }

  inline void reclaimEntries(timestamp_t ts) {
    int expected;
    while (true) {
      while (state_ & RESIZE_STATE)
        ;  // Wait until resize is done.
      expected = state_;
      // Move state to reclaim only if it is not resizing.
      if (!(expected & RESIZE_STATE) &&
          state_.compare_exchange_weak(expected, expected | RECLAIM_STATE)) {
        break;
      }
    }

    int i = curr_;
    int end = base_;
    if (end > i) {
      i = capacity_ + i;
    }
    for (; i >= end; --i) {
      if (entries_[i % capacity_].ts_ <= ts) {
        // Found first entry to retire at index i - 1, so set base to i.
        if (i >= capacity_) {
          base_ = i % capacity_;
        } else {
          assert(i >= 0);
          base_ = i;
        }
      }
    }
  }

  inline void prepare(NodeType *const ptr) {
    int expected;
    while (true) {
      while (state_ & PENDING_STATE)
        ;  // Wait for ongoing op to finish.
      expected = state_;
      if (!(state_ & PENDING_STATE) &&
          state_.compare_exchange_weak(expected, PENDING_STATE)) {
        // Effectively locks bundle.
        if ((curr_ + 1) % capacity_ == base_) {
          // Resize if we have run out of room.
          grow();
        }
        SOFTWARE_BARRIER;
        entries_[(curr_ + 1) % capacity_].ptr_ = ptr;
      }
    }
  }

  inline void finalize(timestamp_t ts) {
    // Assumes the bundles are in the pending state.
    assert(state_ & PENDING_STATE);
    assert((curr_ + 1) % capacity_ != base_);
    entries_[(curr_ + 1) % capacity_].ts_ = ts;
    curr_ = (curr_ + 1) % capacity_;
    state_.fetch_and(~PENDING_STATE);
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
    *bundle = new Bundle<NodeType>();
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
#define BUNDLE_INIT_CLEANUP(provider) \
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
    // int i = 0;
    Bundle<NodeType> *curr_bundle = bundles[0];
    NodeType *curr_ptr = ptrs[0];
    // BundleEntry<NodeType> *entries[BUNDLE_MAX_BUNDLES_UPDATED + 1] = {
    //     nullptr,
    // };
    while (curr_bundle != nullptr) {
      // entries[i] =
      //     new BundleEntry<NodeType>(BUNDLE_PENDING_TIMESTAMP, ptrs[i],
      //     nullptr, o);
      // curr_bundle->insertAtHead(entries[i]);
      curr_bundle->prepare(curr_ptr);
      curr_bundle++;
      curr_ptr++;
    }
    SOFTWARE_BARRIER;

    // Get update linearization timestamp.
    timestamp_t lin_time = get_update_lin_time(tid);
    SOFTWARE_BARRIER;
    *lin_addr = lin_newval;  // Original linearization point.
    SOFTWARE_BARRIER;

    // Unblock waiting RQs.
    // i = 0;
    // BundleEntry<NodeType> *curr_entry = entries[i];
    // while (curr_entry != nullptr) {
    // curr_entry->set_ts(lin_time);
    // curr_entry->validate();
    // curr_entry = entries[++i];
    // }
    curr_bundle = bundles[0];
    while (curr_bundle != nullptr) {
      curr_bundle->finalize(lin_time);
      curr_bundle++;
    }
  }
};

#endif  // RQ_BUNDLE_H