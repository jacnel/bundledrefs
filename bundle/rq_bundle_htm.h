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

#ifndef BUNDLE_MAX_RQ_THREADS
#define BUNDLE_MAX_RQ_THREADS 8
#endif
#define BUNDLE_DEPTH (BUNDLE_MAX_RQ_THREADS + 2)

#define BUNDLE_STALL_RQS
#define CPU_RELAX

// A collection required by each data structure node to ensure correct range
// query traversals. The RQTracker will only overwrite old reference when
// it can ensure that no range query will require them. This is accomplished
// because we limit the number of active range queries.
template <typename NodeType>
class rq_bundle_t {
 public:
  const unsigned int depth = BUNDLE_DEPTH;
  volatile char pad0[PREFETCH_SIZE_BYTES];
  volatile unsigned int newest = 0;
  volatile timestamp_t ts_bundle[BUNDLE_DEPTH];
  NodeType* volatile ptr_bundle[BUNDLE_DEPTH];

  // Returns a reference to the node that immediately followed at timestamp ts.
  NodeType* volatile getPtrByTimestamp(timestamp_t ts) {
    unsigned int start = newest;
    unsigned int next_idx = start;
    unsigned int temp_idx;
    timestamp_t temp_ts;
    for (int i = 0; i < depth; ++i) {
      temp_idx = (depth + (start - i)) % depth;
#ifdef BUNDLE_STALL_RQS
      while ((temp_ts = this->ts_bundle[temp_idx]) == BUNDLE_BUSY_TIMESTAMP)
        ;
#else
      temp_ts = this->ts_bundle[temp_idx];
#endif
      if (temp_ts > this->ts_bundle[next_idx] && temp_ts <= ts &&
          temp_ts != BUNDLE_NULL_TIMESTAMP) {
        next_idx = temp_idx;
      }
    }
    assert(ptr_bundle[next_idx] != nullptr);
    return ptr_bundle[next_idx];
  }
};

// Stores information about the active range queries. Used by updates to ensure
// that no edges required by an active range query are recycled.
typedef struct rq_snapshot {
  int num_active;
  timestamp_t oldest_active;
  timestamp_t newest_active;
  timestamp_t active_rqs[BUNDLE_MAX_RQ_THREADS];

  rq_snapshot* init() {
    num_active = 0;
    oldest_active = BUNDLE_MAX_TIMESTAMP;
    newest_active = BUNDLE_NULL_TIMESTAMP;
    for (int i = 0; i < BUNDLE_MAX_RQ_THREADS; ++i) {
      active_rqs[i] = BUNDLE_NULL_TIMESTAMP;
    }
    return this;
  }
} rq_snapshot_t;

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

  union __update_thread_data {
    struct {
      rq_snapshot_t snapshot;
    };
    volatile char bytes[__THREAD_DATA_SIZE];
  } __attribute__((aligned(__THREAD_DATA_SIZE)));

  // Number of processes concurrently operating on the data structure.
  const int num_processes_;
  // Maximum number of threads performing range queries.
  const int max_num_rq_threads_ = BUNDLE_MAX_RQ_THREADS;
  // Mapping from thread ids to RQ ids.
  int rq_tids[MAX_TID_POW2];
  volatile char pad0[PREFETCH_SIZE_BYTES];
  // Timestamp used by range queries to linearize accesses.
  std::atomic<timestamp_t> curr_timestamp_;
  volatile char pad1[PREFETCH_SIZE_BYTES];
  // Timestamp used by updates to mark changes.
  std::atomic<timestamp_t> next_timestamp_;
  volatile char pad2[PREFETCH_SIZE_BYTES];
  // Number of threads initialized to perform range queries.
  std::atomic<int> num_init_rq_threads_;
  volatile char pad3[PREFETCH_SIZE_BYTES];
  // Array of RQ announcements. One per RQ thread.
  __rq_thread_data* rq_thread_data_;
  // Array of snapshots for updates.
  __update_thread_data* update_thread_data_;

  DataStructure* ds_;
  RecordManager* const recmgr_;

  int init_[MAX_TID_POW2] = {
      0,
  };

 public:
  RQProvider(const int num_processes, DataStructure* ds, RecordManager* recmgr)
      : num_processes_(num_processes), ds_(ds), recmgr_(recmgr) {
    rq_thread_data_ = new __rq_thread_data[max_num_rq_threads_];
    update_thread_data_ = new __update_thread_data[num_processes];
    for (int i = 0; i < max_num_rq_threads_; ++i) {
      rq_thread_data_[i].data.rq_lin_time = BUNDLE_NULL_TIMESTAMP;
      rq_thread_data_[i].data.rq_flag = false;
    }
    for (int i = 0; i < MAX_TID_POW2; ++i) {
      rq_tids[i] = -1;
    }
    curr_timestamp_ = BUNDLE_NULL_TIMESTAMP;
    next_timestamp_ = BUNDLE_MIN_TIMESTAMP;
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

  bool registerRQThread(const int tid) {
    if (rq_tids[tid] != -1) {
      return true;
    } else if (num_init_rq_threads_ >= BUNDLE_MAX_RQ_THREADS) {
      // Cannot admit any new range query threads.
      assert(num_init_rq_threads_ == BUNDLE_MAX_RQ_THREADS);
      return false;
    } else {
      const int rq_tid = num_init_rq_threads_.fetch_add(1);
      assert(rq_thread_data_[rq_tid].data.rq_lin_time ==
                 BUNDLE_NULL_TIMESTAMP &&
             rq_thread_data_[rq_tid].data.rq_flag == false);
      rq_tids[tid] = rq_tid;
      return true;
    }
  }

  void unregisterRQThread(const int tid) {
    if (rq_tids[tid] == -1) {
      return;
    } else {
      rq_tids[tid] = -1;
      num_init_rq_threads_.fetch_sub(1, std::memory_order_acquire);
      assert(num_init_rq_threads_ >= 0);
    }
  }

  // Initializes a new node's bundle.
  inline void init_node(const int tid, NodeType* const node,
                        NodeType* const next) {
    node->rqbundle = new rq_bundle_t<NodeType>();
    int newest = node->rqbundle->newest;
    for (int i = 0; i < node->rqbundle->depth; ++i) {
      node->rqbundle->ptr_bundle[i] = (i == newest ? next : nullptr);
      // The timestamp of newest must be set later.
      node->rqbundle->ts_bundle[i] =
          (i == newest ? BUNDLE_BUSY_TIMESTAMP : BUNDLE_NULL_TIMESTAMP);
    }
  }

  // For each address addr that is modified by rq_linearize_update_at_write
  // or rq_linearize_update_at_cas, you must replace any initialization of addr
  // with invocations of rq_write_addr.
  //
  // TODO: This was kept around to make porting RQProvider easier.
  template <typename T>
  inline void write_addr(const int tid, T volatile* const addr, const T val) {
    *addr = val;
  }

  // For each address addr that is modified by rq_linearize_update_at_write
  // or rq_linearize_update_at_cas, you must replace any reads of addr with
  // invocations of rq_read_addr
  //
  // TODO: This was kept around to make porting RQProvider easier.
  template <typename T>
  inline T read_addr(const int tid, T volatile* const addr) {
    return *addr;
  }

  // TODO: These were also kept around to make life easier.
  inline void announce_physical_deletion(const int tid,
                                         NodeType* const* const deletedNodes) {}
  inline void physical_deletion_failed(const int tid,
                                       NodeType* const* const deletedNodes) {}
  inline void physical_deletion_succeeded(const int tid,
                                          NodeType* const* const deletedNodes) {
  }

 private:
  // Creates a snapshot of the current state of active RQs.
  inline void snapshot_active_rqs(const int tid) {
    rq_snapshot_t* snapshot = update_thread_data_[tid].snapshot.init();
    timestamp_t curr_rq;
    for (int i = 0; i < max_num_rq_threads_; ++i) {
      while (rq_thread_data_[i].data.rq_flag == true)
        ;  // Wait until RQ linearizes itself.
      curr_rq = rq_thread_data_[i].data.rq_lin_time;
      if (curr_rq != BUNDLE_NULL_TIMESTAMP) {
        snapshot->active_rqs[snapshot->num_active++] = curr_rq;
        if (curr_rq < snapshot->oldest_active) {
          snapshot->oldest_active = curr_rq;  // Update oldest.
        }
        if (curr_rq > snapshot->newest_active) {
          snapshot->newest_active = curr_rq;  // Update newest.
        }
      }
    }
    assert(snapshot->num_active <= num_init_rq_threads_);
  }

  // It is assumed that no concurrent operation will alter a bundle.
  inline int find_edge_to_recycle(const int tid,
                                  rq_bundle_t<NodeType>* rqbundle) {
    timestamp_t curr_ts, next_ts, rq_ts, temp_ts;
    int curr_idx;
    unsigned int depth = rqbundle->depth;
    unsigned int newest = rqbundle->newest;
    volatile timestamp_t* ts_bundle = rqbundle->ts_bundle;
    rq_snapshot_t* snapshot = &update_thread_data_[tid].snapshot;

    if (snapshot->num_active == 0 ||  // Optimization.
        snapshot->oldest_active >= ts_bundle[newest]) {
      return (newest + 1) % depth;
    }

    for (int i = 0; i < depth - 1; ++i) {
      curr_idx = (newest + i) % depth;
      curr_ts = ts_bundle[curr_idx];

      if (curr_ts == BUNDLE_NULL_TIMESTAMP ||
          curr_ts > snapshot->newest_active) {
        return curr_idx;  // Trivially able to recycle.
      } else {
        next_ts = BUNDLE_MAX_TIMESTAMP;
        for (int j = 0; j < depth; ++j) {
          temp_ts = ts_bundle[(curr_idx + j) % depth];
          if (temp_ts > curr_idx && temp_ts < next_ts) {
            next_ts = temp_ts;
          }
        }
        // All edges but the newest should have a newer edge.
        assert(next_ts != BUNDLE_MAX_TIMESTAMP);

        for (int a = 0; a < snapshot->num_active; ++a) {
          rq_ts = snapshot->active_rqs[a];
          if (curr_ts < rq_ts && next_ts <= rq_ts) {
            return curr_idx;
          }
        }
      }
    }
    assert(0);  // The design ensures that some edge is recyclable.
    return -1;
  }

  inline timestamp_t start_update() { return next_timestamp_.fetch_add(1); }

  inline void end_update(timestamp_t ts) {
    while (curr_timestamp_ != ts - 1) {
      CPU_RELAX;
    }
    curr_timestamp_++;
  }

  inline timestamp_t get_update_lin_time() {
    assert(curr_timestamp_ != BUNDLE_MAX_TIMESTAMP);
    return curr_timestamp_.fetch_add(1);
  }

  // Write the range query linearization time so updates do not recycle any
  // edges needed by this range query.
  inline timestamp_t start_traversal(int tid) {
    int rq_tid = rq_tids[tid];
    assert(rq_tid != -1);
    // Atomic loads on rq_flag have acquire semantics.
    rq_thread_data_[rq_tid].data.rq_flag = true;
    rq_thread_data_[rq_tid].data.rq_lin_time = curr_timestamp_;
    rq_thread_data_[rq_tid].data.rq_flag = false;
    return rq_thread_data_[rq_tid].data.rq_lin_time;
  }

  // Reset the range query linearization time so that updates may recycle an
  // edge we needed.
  inline void end_traversal(int tid) {
    int rq_tid = rq_tids[tid];
    assert(rq_tid != -1);
    rq_thread_data_[rq_tid].data.rq_lin_time = -1;
  }

 public:
  // Find and update the newest reference in the predecesor's bundle. If this
  // operation is an insert, then the new nodes bundle must also be initialized.
  template <typename T>
  inline T linearize_update_at_write(const int tid, T volatile* const lin_addr,
                                     const T& lin_newval,
                                     rq_bundle_t<NodeType>* const pred_bundle,
                                     rq_bundle_t<NodeType>* const curr_bundle,
                                     NodeType* ptr_bundle_val, bool is_insert) {
    // First, determine which edge in the bundle can be recycled. We delay this
    // until after the linearization point because only range queries will
    // require this information.
    //
    // TODO: If we want to implement a lock free version this may have to
    // change.
    snapshot_active_rqs(tid);
    int idx = find_edge_to_recycle(tid, pred_bundle);

    // Blocks all RQs that may see the updated timestamp, ensuring that the
    // update is visible (i.e., get and RQ have the same linearization point).
    pred_bundle->ts_bundle[idx] = BUNDLE_BUSY_TIMESTAMP;
    SOFTWARE_BARRIER;
    timestamp_t lin_time = get_update_lin_time();

    *lin_addr = lin_newval;  // Original linearization point.

    // Now, update the predecesor's bundle. The pointer must be set first so
    // that an active RQ does not see an inconsistent value.
    pred_bundle->newest = idx;
    pred_bundle->ptr_bundle[idx] = ptr_bundle_val;
    SOFTWARE_BARRIER;
    pred_bundle->ts_bundle[idx] = lin_time;
    if (is_insert) {
      curr_bundle->ts_bundle[curr_bundle->newest] = lin_time;
    }
  }

  // Add keys to the result set. When bundles are used, range query traversal
  // becomes much simpler. The primary advantage is that any node touched will
  // be in our snapshot.
  inline int traverse(const int tid, NodeType* curr, const K& high,
                      K* const resultKeys, V* resultValues) {
    const timestamp_t ts = start_traversal(tid);
    int cnt = 0;
    assert(curr != nullptr);
    while (curr->key <= high && curr->key < KEY_MAX) {
      cnt += ds_->getKeys(tid, curr, resultKeys, resultValues);
      curr = curr->rqbundle->getPtrByTimestamp(ts);
    }
    end_traversal(tid);
    return cnt;
  }
};

#endif  // RQ_BUNDLE_H