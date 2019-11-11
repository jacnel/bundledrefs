#ifndef RQ_BUNDLE_H
#define RQ_BUNDLE_H

#include <pthread.h>
#include <atomic>
#include "plaf.h"
#include "rq_debugging.h"

typedef long long timestamp_t;
#define BUNDLE_NULL_TIMESTAMP 0
#define BUNDLE_MIN_TIMESTAMP 1
#define BUNDLE_MAX_TIMESTAMP (LLONG_MAX - 1)
#define BUNDLE_BUSY_TIMESTAMP LLONG_MAX

#define CPU_RELAX

// A collection required by each data structure node to ensure correct range
// query traversals. The RQTracker will only overwrite old reference when
// it can ensure that no range query will require them. This is accomplished
// because we limit the number of active range queries.
template <typename NodeType>
class rq_bundle_node_t {
 public:
  volatile timestamp_t ts_;
  NodeType *volatile ptr_;
  struct rq_bundle_node *volatile next_;

  explicit rq_bundle_node_t(timestamp_t ts, NodeType *ptr,
                            rq_bundle_node_t *next)
      : ts_(ts), ptr_(ptr), next_(next) {}

  void set_next(rq_bundle_node_t *const next) { next_ = next; }
};

template <typename NodeType>
class rq_bundle_t {
 private:
  rq_bundle_node_t *volatile head;
  rq_bundle_node_t *tail;

 public:
  rq_bundle_t() {
    // A sentinal node to help recycling.
    head = new rq_bundle_node_t(BUNDLE_NULL_TIMESTAMP, nullptr, nullptr);
    tail = head;
  }

  // Returns a reference to the node that immediately followed at timestamp ts.
  inline NodeType *volatile getPtrByTimestamp(timestamp_t ts) {
    // Start at head and work backwards until edge is found.
    rq_bundle_node_t *curr = head;
    // Wait if update is in progress.
    while (curr->ts == BUNDLE_BUSY_TIMESTAMP)
      ;
    while (curr->ts > ts) {
      // TODO: Maybe, prefetch the next pointer.
      curr = curr->next;
      assert(curr != tail);
    }
    return curr->ptr;
  }

  // Inserts a new rq_bundle_node at the head of the bundle.
  void insertAtHead(rq_bundle_node_t *const new_bundle_node) {
    new_bundle_node.set_next(head);
    head = new_bundle_node;
  }

  // Recycles any edges that are older than ts. At the moment this must be
  // ordered before adding a new bundle node.
  inline void recycleEdges(timestamp_t ts) {
    // This should not be called while the bundle is being updated.
    assert(head->ts_ != BUNDLE_BUSY_TIMESTAMP);
    // And it should not be called on a newly initialized bundle node.
    assert(head != tail);
    // If there are no active RQs then we can recycle all edges, but the newest
    // (i.e., head).
    if (ts == BUNDLE_NULL_TIMESTAMP) {
      head->next_ = tail;
    } else {
      // Traverse from head and remove nodes that are lower than ts.
      rq_bundle_node_t *pred = nullptr;
      rq_bundle_node_t *curr = head;
      while (curr->ts_ != BUNDLE_NULL_TIMESTAMP && curr->ts_ >= ts) {
        pred = curr;
        curr = curr->next_;
      }
      // curr points to the first node that may be recylced given ts, so swing
      // pred's next to the tail. Currently, assumed that external
      // synchronization protects the bundle.
      if (pred != nullptr) {
        pred->next_ = tail;
        // TODO: Handle memory leaks.
      }
    }
  }
};

// NOTES ON IMPLEMENTATION DETAILS.
// --------------------------------
// The active RQ array is now the number of processes allowed to accomodate any
// number of range query threads. Snapshots are still taken by iterating over
// the list. For now, we iterate over the entire list but there is room for
// optimizations here (i.e., maintin number of active RQs and map the tid to the
// next slot in array).

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
      // TODO: Provide debug statistics.
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

  // Initializes a new node's bundle.
  inline void init_node(const int tid, NodeType *const node,
                        NodeType *const next) {
    node->rqbundle = new rq_bundle_t<NodeType>();
  }

  // For each address addr that is modified by rq_linearize_update_at_write
  // or rq_linearize_update_at_cas, you must replace any initialization of addr
  // with invocations of rq_write_addr.
  //
  // TODO: This was kept around to make porting RQProvider easier.
  template <typename T>
  inline void write_addr(const int tid, T volatile *const addr, const T val) {
    *addr = val;
  }

  // For each address addr that is modified by rq_linearize_update_at_write
  // or rq_linearize_update_at_cas, you must replace any reads of addr with
  // invocations of rq_read_addr
  //
  // TODO: This was kept around to make porting RQProvider easier.
  template <typename T>
  inline T read_addr(const int tid, T volatile *const addr) {
    return *addr;
  }

  // TODO: These were also kept around to make life easier.
  inline void announce_physical_deletion(const int tid,
                                         NodeType *const *const deletedNodes) {}
  inline void physical_deletion_failed(const int tid,
                                       NodeType *const *const deletedNodes) {}
  inline void physical_deletion_succeeded(const int tid,
                                          NodeType *const *const deletedNodes) {
  }

 private:
  // Creates a snapshot of the current state of active RQs.
  inline timestamp_t *get_oldest_active_rq(const int tid) {
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

  inline timestamp_t get_update_lin_time() {
    assert(curr_timestamp_ != BUNDLE_MAX_TIMESTAMP);
    return curr_timestamp_.fetch_add(1);
  }

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

 public:
  // Find and update the newest reference in the predecesor's bundle. If this
  // operation is an insert, then the new nodes bundle must also be initialized.
  template <typename T>
  inline T linearize_update_at_write(const int tid, T volatile *const lin_addr,
                                     const T &lin_newval,
                                     rq_bundle_t<NodeType> *const pred_bundle,
                                     rq_bundle_t<NodeType> *const curr_bundle,
                                     NodeType *const pred_bundle_ptr,
                                     NodeType *const curr_bundle_ptr,
                                     bool is_insert) {
    // TODO: If we want to implement a lock free version this may have to
    // change.
    // TODO: Remove edge recylcing from the critical path of an update.
    pred_bundle->recycleEdges(get_oldest_active_rq(tid));
    SOFTWARE_BARRIER;
    // BUSY_TIMESTAMP blocks all RQs that might see the update, ensuring that
    // the update is visible (i.e., get and RQ have the same linearization
    // point).
    rq_bundle_node_t *pred_bundle_node =
        new rq_bundle_node_t{BUNDLE_BUSY_TIMESTAMP, pred_bundle_ptr, nullptr};

    pred_bundle->insertAtHead(pred_bundle_node);

    if (is_insert) {
      rq_bundle_node_t *curr_bundle_node =
          new rq_bundle_node_t{BUNDLE_BUSY_TIMESTAMP, curr_bundle_ptr, nullptr};
      curr_bundle->insertAtHead(curr_bundle_node);
    }
    SOFTWARE_BARRIER;

    // Get update linearization timestamp.
    timestamp_t lin_time = get_update_lin_time();
    SOFTWARE_BARRIER;

    *lin_addr = lin_newval;  // Original linearization point.
    SOFTWARE_BARRIER;

    // Unblock waiting RQs.
    if (is_insert) {
      curr_bundle->head.ts = lin_time;
    }
    pred_bundle->head.ts = lin_time;
  }

  // Add keys to the result set. When bundles are used, range query traversal
  // becomes much simpler. The primary advantage is that any node touched will
  // be in our snapshot.
  inline int traverse(const int tid, NodeType *curr, const K &high,
                      K *const resultKeys, V *resultValues) {
    const timestamp_t ts = start_traversal(tid);
    int cnt = 0;
    assert(curr != nullptr);
    while (curr->key <= high && curr->key != KEY_MAX) {
      cnt += ds_->getKeys(tid, curr, resultKeys, resultValues);
      curr = curr->rqbundle->getPtrByTimestamp(ts);
    }
    end_traversal(tid);
    return cnt;
  }
};

#endif  // RQ_BUNDLE_H