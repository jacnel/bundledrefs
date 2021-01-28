// Jacob Nelson
//
// This file implements a bundle as a linked list of bundle entries. A bundle is
// prepared by CASing the head of the bundle to a pending entry.

#ifndef BUNDLE_LINKED_BUNDLE_H
#define BUNDLE_LINKED_BUNDLE_H

#include <pthread.h>
#include <sys/types.h>

#include <atomic>
#include <mutex>

#include "common_bundle.h"
#include "plaf.h"
#include "rq_debugging.h"

#define CPU_RELAX asm volatile("pause\n" ::: "memory")
#define likely(x) __builtin_expect((x), 1)
#define unlikely(x) __builtin_expect((x), 0)

#define DEBUG_PRINT_INIT() unsigned long i = 0
#define DEBUG_PRINT(str)                         \
  if ((i + 1) % 10000 == 0) {                    \
    std::cout << str << std::endl << std::flush; \
  }                                              \
  ++i;

enum op { NOP, INSERT, REMOVE };

template <typename NodeType>
class BundleEntry {
 public:
  // volatile timestamp_t ts_;  // Redefinition of ts_ to make it volitile.
  std::atomic<timestamp_t> ts_;
  NodeType *ptr_;

  // Additional members.
  // BundleEntry *volatile next_;
  std::atomic<BundleEntry *> next_;
  volatile timestamp_t deleted_ts_;

  explicit BundleEntry(timestamp_t ts, NodeType *ptr, BundleEntry *next)
      : ts_(ts), next_(next) {
    this->ptr_ = ptr;
    deleted_ts_ = BUNDLE_NULL_TIMESTAMP;
  }

  void set_ts(const timestamp_t ts) { ts_ = ts; }
  void set_ptr(NodeType *const ptr) { this->ptr_ = ptr; }
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

template <typename NodeType>
class LinkedBundle {
 private:
  std::atomic<BundleEntry<NodeType> *> head_;
  BundleEntry<NodeType> *volatile tail_;

#ifdef BUNDLE_DEBUG
  volatile int updates = 0;
  BundleEntry<NodeType> *volatile last_recycled = nullptr;
  volatile int oldest_edge = 0;
#endif

 public:
  // LinkedBundle()
  //     : tail_(
  //           new BundleEntry<NodeType>(BUNDLE_NULL_TIMESTAMP, nullptr, nullptr)),
  //       head_(tail_) {}
  LinkedBundle() = delete;

  ~LinkedBundle() {
    BundleEntry<NodeType> *curr = head_;
    BundleEntry<NodeType> *next;
    while (curr != tail_) {
      assert(curr != nullptr);
      next = curr->next_;
      delete curr;
      curr = next;
    }
    delete tail_;
  }

  void init() {
    // static_assert(std::is_default_constructible<LinkedBundle<NodeType>>::value);
    tail_ = new BundleEntry<NodeType>(BUNDLE_NULL_TIMESTAMP, nullptr, nullptr);
    head_ = tail_;
  }

  // Inserts a new rq_bundle_node at the head of the bundle.
  inline void prepare(NodeType *const ptr) {
    BundleEntry<NodeType> *new_entry =
        new BundleEntry<NodeType>(BUNDLE_PENDING_TIMESTAMP, ptr, nullptr);
    BundleEntry<NodeType> *expected = head_;
    new_entry->next_ = expected;
    while (true) {
      if (likely(expected->ts_.load() != BUNDLE_PENDING_TIMESTAMP &&
                 head_.compare_exchange_weak(expected, new_entry))) {
#ifdef BUNDLE_DEBUG
        ++updates;
#endif
        return;
      }
      // long i = 0;
      while (expected->ts_ == BUNDLE_PENDING_TIMESTAMP) {
        // DEBUG_PRINT("insertAtHead");
        CPU_RELAX;
      }
    }
  }

  // Labels the pending entry to make it visible to range queries.
  inline void finalize(timestamp_t ts) {
    // BundleEntry<NodeType> *entry = head_;
    // assert(entry->ts_ == BUNDLE_PENDING_TIMESTAMP);
    // entry->ts_ = ts;
    assert(head_.load()->ts_ == BUNDLE_PENDING_TIMESTAMP);
    head_.load(memory_order_release)->ts_ = ts;
  }

  // Returns a reference to the node that immediately followed at timestamp ts.
  inline NodeType *getPtrByTimestamp(timestamp_t ts) {
    // Start at head and work backwards until edge is found.
    BundleEntry<NodeType> *curr = head_;
    long i = 0;
    while (unlikely(curr->ts_ == BUNDLE_PENDING_TIMESTAMP)) {
      // DEBUG_PRINT("getPtrByTimestamp");
      CPU_RELAX;
    }
    while (unlikely(curr != tail_ && curr->ts_ > ts)) {
      assert(curr->ts_ != BUNDLE_NULL_TIMESTAMP);
      curr = curr->next_;
    }
#ifdef BUNDLE_DEBUG
    if (curr->marked()) {
      std::cout << dump(0) << std::flush;
      exit(1);
    }
#endif
    return curr->ptr_;
  }

  // Reclaims any edges that are older than ts. At the moment this should be
  // ordered before adding a new entry to the bundle.
  inline void reclaimEntries(timestamp_t ts) {
    // Obtain a reference to the pred non-reclaimable entry and first
    // reclaimable one.
    BundleEntry<NodeType> *pred = head_;
    long i = 0;
    if (pred->ts_ == BUNDLE_PENDING_TIMESTAMP) {
      // DEBUG_PRINT("reclaimEntries");
      pred = pred->next_;
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
#ifdef BUNDLE_DEBUG
    last_recycled = curr;
    oldest_edge = pred->ts_;
#endif

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
#ifdef BUNDLE_DEBUG
    if (curr != tail_) {
      std::cout << curr << std::endl;
      std::cout << dump(ts) << std::flush;
      exit(1);
    }
#endif
  }

  // [UNSAFE] Returns the number of bundle entries.
  int size() {
    int size = 0;
    BundleEntry<NodeType> *curr = head_;
    while (curr != tail_) {
#ifdef BUNDLE_DEBUG
      if (curr->marked()) {
        std::cout << dump(0) << std::flush;
        exit(1);
      }
#endif
      ++size;
      curr = curr->next_;
#ifdef BUNDLE_DEBUG
      if (curr == nullptr) {
        std::cout << dump(0) << std::flush;
        exit(1);
      }
#endif
    }
    return size;
  }

  inline NodeType *first(timestamp_t &ts) {
    BundleEntry<NodeType> *entry = head_;
    ts = entry->ts_;
    return entry->ptr_;
  }

  std::pair<NodeType *, timestamp_t> *get(int &length) {
    // Find the number of entries in the list.
    BundleEntry<NodeType> *curr_entry = head_;
    int size = 0;
    while (curr_entry != tail_) {
      ++size;
      curr_entry = curr_entry->next_;
    }

    // Build the return array.
    std::pair<NodeType *, timestamp_t> *retarr =
        new std::pair<NodeType *, timestamp_t>[size];
    int pos = 0;
    NodeType *ptr;
    timestamp_t ts;
    curr_entry = head_;
    while (curr_entry != tail_) {
      ptr = curr_entry->ptr_;
      ts = curr_entry->ts_;
      retarr[pos++] = std::pair<NodeType *, timestamp_t>(ptr, ts);
      curr_entry = curr_entry->next_;
    }
    length = size;
    return retarr;
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
         << reinterpret_cast<long>(curr->next_.load(std::memory_order_relaxed))
         << ">";
    } else {
      ss << "(unexpected end)";
    }
#ifdef BUNDLE_DEBUG
    ss << " [updates=" << updates << ", last_recycled=" << last_recycled
       << ", oldest_edge=" << oldest_edge << "]" << std::endl;
#else
    ss << std::endl;
#endif
    return ss.str();
  }
};

#endif  // BUNDLE_LINKED_BUNDLE_H