#ifndef RQ_BUNDLE_H
#define RQ_BUNDLE_H

#include <pthread.h>
#include <atomic>
#include <mutex>
#include "common_bundle.h"
#include "plaf.h"
#include "rq_debugging.h"

#define CPU_RELAX asm volatile("pause\n" ::: "memory")

template <typename NodeType>
class BundleEntry {
 public:
  volatile timestamp_t ts_;
  NodeType *volatile ptr_;
  BundleEntry *volatile next_;

  explicit BundleEntry(timestamp_t ts, NodeType *ptr, BundleEntry *next)
      : ts_(ts), ptr_(ptr), next_(next) {}

  void set_ts(const timestamp_t ts) { ts_ = ts; }
  void set_ptr(NodeType *const ptr) { ptr_ = ptr; }
  void set_next(BundleEntry *const next) { next_ = next; }
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
  BundleEntry<NodeType> *tail_;
  volatile int updates = 0;
  volatile int last_recycled = 0;
  volatile int oldest_edge = 0;

 public:
  explicit Bundle() {
    head_ = new BundleEntry<NodeType>(BUNDLE_NULL_TIMESTAMP, nullptr, nullptr);
    tail_ = head_;
  }

  inline BundleEntry<NodeType> *getHead() { return head_; }

  // Returns a reference to the node that immediately followed at timestamp ts.
  inline NodeType *volatile getPtrByTimestamp(timestamp_t ts) {
    // Start at head and work backwards until edge is found.
    BundleEntry<NodeType> *curr = head_;
    // bool once = false;
    while (curr->ts_ == BUNDLE_BUSY_TIMESTAMP) {
      CPU_RELAX;
    }
    while (curr->ts_ != BUNDLE_NULL_TIMESTAMP && curr->ts_ > ts) {
      curr = curr->next_;
    }
    return curr->ptr_;
  }

  // Inserts a new rq_bundle_node at the head of the bundle.
  inline void insertAtHead(BundleEntry<NodeType> *new_entry) {
    BundleEntry<NodeType> *expected = head_;
    while (true) {
      new_entry->set_next(expected);
      while (expected->ts_ == BUNDLE_BUSY_TIMESTAMP) {
        CPU_RELAX;
      }
      if (head_.compare_exchange_weak(expected, new_entry)) {
        ++updates;
        return;
      }
      expected = head_;
    }
  }

  // [UNSAFE] Returns the number of bundle entries.
  inline int getSize() {
    int size = 0;
    BundleEntry<NodeType> *curr = head_;
    while (curr->ts_ != BUNDLE_NULL_TIMESTAMP) {
      ++size;
      curr = curr->next_;
    }
    return size;
  }

  // Recycles any edges that are older than ts. At the moment this should be
  // ordered before adding a new entry to the bundle.
  inline void recycleEdges(timestamp_t ts) {
    //   // And it should not be called on a newly initialized bundle node.
    //   if (head_ == tail_) {
    //     dump(ts);
    //     exit(1);
    //   }
    //   // Read the head and wait for a concurrent update.
    //   BundleEntry<NodeType> *const start = head_;
    //   while (start->ts_ == BUNDLE_BUSY_TIMESTAMP)
    //     ;
    //   if (ts == BUNDLE_NULL_TIMESTAMP) {
    //     // If there are no active RQs then we can recycle all edges, but the
    //     // newest (i.e., head).
    //     last_recycled = start->next_->ts_;
    //     oldest_edge = start->ts_;
    //     std::atomic::atomic_compare_exchange_weak(
    //         (std::atomic<BundleEntry<NodeType> *> *)(&(start->next_)),
    //         start->next_, tail_);
    //   } else {
    //     // Traverse from head and remove nodes that are lower than ts.
    //     BundleEntry<NodeType> *curr = start;
    //     while (curr->ts_ != BUNDLE_NULL_TIMESTAMP && curr->ts_ > ts) {
    //       curr = curr->next_;
    //     }
    //     // curr points to the oldest edge required by any active RQs.
    //     if (curr->ts_ != BUNDLE_NULL_TIMESTAMP) {
    //       last_recycled = curr->next_->ts_;
    //       oldest_edge = curr->ts_;
    //       curr->next_ = tail_;
    //     }
    //   }
  }

  void __attribute__((noinline)) dump(timestamp_t ts) {
    BundleEntry<NodeType> *curr = head_;
    std::cout << "(ts=" << ts << ") : ";
    while (curr != tail_) {
      std::cout << "<" << curr->ts_ << "," << curr->ptr_ << "," << curr->next_
                << ">";
      curr = curr->next_;
    }
    std::cout << "(tail)<" << curr->ts_ << "," << curr->ptr_ << ","
              << curr->next_ << ">";
    std::cout << " [updates=" << updates << ", last_recycled=" << last_recycled
              << ", oldest_edge=" << oldest_edge << "]" << std::endl;
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

 public:
  RQProvider(const int num_processes, DataStructure *ds, RecordManager *recmgr)
      : num_processes_(num_processes), ds_(ds), recmgr_(recmgr) {
    rq_thread_data_ = new __rq_thread_data[num_processes];
    for (int i = 0; i < num_processes; ++i) {
      rq_thread_data_[i].data.rq_lin_time = BUNDLE_NULL_TIMESTAMP;
      rq_thread_data_[i].data.rq_flag = false;
    }
    curr_timestamp_ = BUNDLE_NULL_TIMESTAMP;
    // TODO: Implement cleanup thread.
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

  // For each address addr that is modified by rq_linearize_update_at_write
  // or rq_linearize_update_at_cas, you must replace any initialization of
  // addr with invocations of rq_write_addr.
  template <typename T>
  inline void write_addr(const int tid, T volatile *const addr, const T val) {
    *addr = val;
  }

  // For each address addr that is modified by rq_linearize_update_at_write
  // or rq_linearize_update_at_cas, you must replace any reads of addr with
  // invocations of rq_read_addr
  template <typename T>
  inline T read_addr(const int tid, T volatile *const addr) {
    return *addr;
  }

  inline void physical_deletion_succeeded(const int tid,
                                          NodeType *const *const deletedNodes) {
    int i;
    for (i = 0; deletedNodes[i]; ++i) {
      recmgr_->retire(tid, deletedNodes[i]);
    }
  }

 private:
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

  inline timestamp_t get_update_lin_time(int tid) {
#ifdef BUNDLE_TIMESTAMP_RELAXATION
    if ((rq_thread_data_[tid].data.local_timestamp %
         BUNDLE_TIMESTAMP_RELAXATION - 1) == 0) {
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
    rq_thread_data_[tid].data.rq_lin_time = -1;
  }

  // Find and update the newest reference in the predecesor's bundle. If this
  // operation is an insert, then the new nodes bundle must also be
  // initialized. Any node whose bundle is passed here must be locked.
  template <typename T>
  inline T linearize_update_at_write(const int tid, T volatile *const lin_addr,
                                     const T &lin_newval,
                                     Bundle<NodeType> *const *const bundles,
                                     NodeType *const *const ptrs) {
    // BUSY_TIMESTAMP blocks all RQs that might see the update, ensuring that
    // the update is visible (i.e., get and RQ have the same linearization
    // point).
    int i = 0;
    Bundle<NodeType> *curr_bundle = bundles[i];
    BundleEntry<NodeType> *entries[BUNDLE_MAX_BUNDLES_UPDATED + 1] = {
        nullptr,
    };
    while (curr_bundle != nullptr) {
      entries[i] =
          new BundleEntry<NodeType>(BUNDLE_BUSY_TIMESTAMP, ptrs[i], nullptr);
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
      curr_entry = entries[++i];
    }
  }
};

#endif  // RQ_BUNDLE_H