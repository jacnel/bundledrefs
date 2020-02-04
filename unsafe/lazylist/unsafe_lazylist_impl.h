/**
 *   This algorithm is based on:
 *   A Lazy Concurrent List-Based Set Algorithm,
 *   S. Heller, M. Herlihy, V. Luchangco, M. Moir, W.N. Scherer III, N. Shavit
 *   OPODIS 2005
 *
 *   The implementation is based on implementations by:
 *   Vincent Gramoli https://sites.google.com/site/synchrobench/
 *   Vasileios Trigonakis http://lpd.epfl.ch/site/ascylib -
 * http://lpd.epfl.ch/site/optik
 */

#ifndef LAZYLIST_IMPL_H
#define LAZYLIST_IMPL_H

#include <cassert>
#include <csignal>
#include "locks_impl.h"
#include "unsafe_lazylist.h"

#ifndef casword_t
#define casword_t uintptr_t
#endif

template <typename K, typename V>
class node_t {
 public:
  K key;
  volatile V val;
  node_t* volatile next;
  volatile int lock;
  volatile long long
      marked;  // is stored as a long long simply so it is large enough to be
               // used with the lock-free RQProvider (which requires all fields
               // that are modified at linearization points of operations to be
               // at least as large as a machine word)

  bool isMarked(const int tid) { return marked; }
};

template <typename K, typename V, class RecManager>
unsafe_lazylist<K, V, RecManager>::unsafe_lazylist(const int numProcesses,
                                                   const K _KEY_MIN,
                                                   const K _KEY_MAX,
                                                   const V _NO_VALUE)
    // Plus 1 for the background thread.
    : recordmgr(new RecManager(numProcesses, SIGQUIT))
#ifdef USE_DEBUGCOUNTERS
      ,
      counters(new debugCounters(numProcesses))
#endif
      ,
      KEY_MIN(_KEY_MIN),
      KEY_MAX(_KEY_MAX),
      NO_VALUE(_NO_VALUE) {
  const int tid = 0;
  initThread(tid);
  nodeptr max = new_node(tid, KEY_MAX, 0, NULL);
  head = new_node(tid, KEY_MIN, 0, NULL);

  head->next = max;
}

template <typename K, typename V, class RecManager>
unsafe_lazylist<K, V, RecManager>::~unsafe_lazylist() {
  const int dummyTid = 0;
  nodeptr curr = head;
  while (curr->key < KEY_MAX) {
    nodeptr next = curr->next;
    delete curr;
    // recordmgr->deallocate(dummyTid, curr);
    curr = next;
  }
  // recordmgr->deallocate(dummyTid, curr);
  delete curr;
  recordmgr->printStatus();
  delete recordmgr;
#ifdef USE_DEBUGCOUNTERS
  delete counters;
#endif
}

template <typename K, typename V, class RecManager>
void unsafe_lazylist<K, V, RecManager>::initThread(const int tid) {
  if (init[tid])
    return;
  else
    init[tid] = !init[tid];

  recordmgr->initThread(tid);
}

template <typename K, typename V, class RecManager>
void unsafe_lazylist<K, V, RecManager>::deinitThread(const int tid) {
  if (!init[tid])
    return;
  else
    init[tid] = !init[tid];

  recordmgr->deinitThread(tid);
}

template <typename K, typename V, class RecManager>
nodeptr unsafe_lazylist<K, V, RecManager>::new_node(const int tid, const K& key,
                                                    const V& val,
                                                    nodeptr next) {
  // nodeptr nnode = recordmgr->template allocate<node_t<K, V>>(tid);
  nodeptr nnode = new node_t<K,V>();
  if (nnode == NULL) {
    cout << "out of memory" << endl;
    exit(1);
  }
  nnode->key = key;
  nnode->val = val;
  nnode->next = next;
  nnode->marked = 0LL;
  nnode->lock = false;
#ifdef __HANDLE_STATS
  GSTATS_APPEND(tid, node_allocated_addresses, ((long long)nnode) % (1 << 12));
#endif
  return nnode;
}

template <typename K, typename V, class RecManager>
inline int unsafe_lazylist<K, V, RecManager>::validateLinks(const int tid,
                                                            nodeptr pred,
                                                            nodeptr curr) {
  return (!pred->marked && !curr->marked && (pred->next == curr));
}

template <typename K, typename V, class RecManager>
bool unsafe_lazylist<K, V, RecManager>::contains(const int tid, const K& key) {
  nodeptr curr = head;
  while (curr->key < key) {
    curr = curr->next;
  }

  V res = NO_VALUE;
  if ((curr->key == key) && !curr->marked) {
    res = curr->val;
  }
  return (res != NO_VALUE);
}

template <typename K, typename V, class RecManager>
V unsafe_lazylist<K, V, RecManager>::doInsert(const int tid, const K& key,
                                              const V& val, bool onlyIfAbsent) {
  nodeptr curr;
  nodeptr pred;
  nodeptr newnode;
  V result;
  while (true) {
    pred = head;
    curr = pred->next;
    while (curr->key < key) {
      pred = curr;
      curr = curr->next;
    }
    acquireLock(&(pred->lock));
    if (validateLinks(tid, pred, curr)) {
      if (curr->key == key) {
        if (curr->marked) {  // this is an optimization
          releaseLock(&(pred->lock));
          continue;
        }
        // node containing key is not marked
        if (onlyIfAbsent) {
          V result = curr->val;
          releaseLock(&(pred->lock));
          return result;
        }
        acquireLock(&(curr->lock));
        result = curr->val;
        // nodeptr insertedNodes[] = {NULL};
        // nodeptr deletedNodes[] = {NULL};
        // rqProvider->linearize_update_at_write(tid, &curr->val, val,
        // insertedNodes, deletedNodes); // shifting KEY_MAX, and not using
        // read_addr to access keys, makes this a problem. no need to run this
        // through the rqProvider, since we just need a write, and we never
        // access keys using the rqProvider.
        curr->val = val;  // original linearization point
        releaseLock(&(curr->lock));
        releaseLock(&(pred->lock));
        return result;
      }
      // key is not in list
      assert(curr->key != key);
      result = NO_VALUE;
      newnode = new_node(tid, key, val, curr);

      pred->next = newnode;

      releaseLock(&(pred->lock));
      return result;
    }
    releaseLock(&(pred->lock));
  }
}

/*
 * Logically remove an element by setting a mark bit to 1
 * before removing it physically.
 */
template <typename K, typename V, class RecManager>
V unsafe_lazylist<K, V, RecManager>::erase(const int tid, const K& key) {
  nodeptr pred;
  nodeptr curr;
  V result;
  while (true) {
    pred = head;
    curr = pred->next;
    while (curr->key < key) {
      pred = curr;
      curr = curr->next;
    }

    if (curr->key != key) {
      result = NO_VALUE;
      return result;
    }
    acquireLock(&(curr->lock));
    acquireLock(&(pred->lock));
    if (validateLinks(tid, pred, curr)) {
      // TODO: maybe implement version with atomic removal of consecutive marked
      // nodes
      assert(curr->key == key);
      result = curr->val;
      nodeptr c_nxt = curr->next;

      curr->marked = 1LL;
      pred->next = c_nxt;

      releaseLock(&(curr->lock));
      releaseLock(&(pred->lock));
      return result;
    }
    releaseLock(&(curr->lock));
    releaseLock(&(pred->lock));
  }
}

template <typename K, typename V, class RecManager>
int unsafe_lazylist<K, V, RecManager>::rangeQuery(const int tid, const K& lo,
                                                  const K& hi,
                                                  K* const resultKeys,
                                                  V* const resultValues) {
  int cnt = 0;
  nodeptr pred = head;
  nodeptr curr = pred->next;
  while (curr->key < lo) {
    curr = curr->next;
  }
  while (curr->key <= hi) {
    cnt += getKeys(tid, curr, resultKeys + cnt, resultValues + cnt);
    curr = curr->next;
  }

  return cnt;
}

template <typename K, typename V, class RecManager>
long long unsafe_lazylist<K, V, RecManager>::debugKeySum(nodeptr head) {
  long long result = 0;
  nodeptr curr = head->next;
  while (curr->key < KEY_MAX) {
    result += curr->key;
    curr = curr->next;
  }
  return result;
}

template <typename K, typename V, class RecManager>
long long unsafe_lazylist<K, V, RecManager>::debugKeySum() {
  return debugKeySum(head);
}

template <typename K, typename V, class RecManager>
inline bool unsafe_lazylist<K, V, RecManager>::isLogicallyDeleted(
    const int tid, node_t<K, V>* node) {
  return node->isMarked(tid);
}
#endif /* LAZYLIST_IMPL_H */
