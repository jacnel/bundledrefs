/*
 * File:   unsafe_skiplist_lock_impl.h
 * Author: Trevor Brown and Maya Arbel-Raviv
 *
 * This is a heavily modified version of the skip-list packaged with StackTrack
 * (by Alistarh et al.)
 *
 * Created on August 6, 2017, 5:25 PM
 */

#ifndef SKIPLIST_LOCK_IMPL_H
#define SKIPLIST_LOCK_IMPL_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "unsafe_skiplist.h"

#define CAS __sync_val_compare_and_swap
#define CPU_RELAX asm volatile("pause\n" ::: "memory")
#define likely
#define unlikely

template <typename K, typename V>
static void sl_node_lock(nodeptr p_node) {
  while (1) {
    long cur_lock = p_node->lock;
    if (likely(cur_lock == 0)) {
      if (likely(CAS(&(p_node->lock), 0, 1) == 0)) {
        return;
      }
    }
    CPU_RELAX;
  }
}

template <typename K, typename V>
static void sl_node_unlock(nodeptr p_node) {
  p_node->lock = 0;
  SOFTWARE_BARRIER;
}

static int sl_randomLevel(const int tid, Random* const threadRNGs) {
  //    int level = 1;
  //    while (((threadRNGs[tid*PREFETCH_SIZE_WORDS].nextNatural() % 100) < 50)
  //    == 0 && level < SKIPLIST_MAX_LEVEL) {
  //        level++;
  //    }
  //    return level - 1;

  // Trevor: let's optimize with a bit hack from:
  // https://graphics.stanford.edu/~seander/bithacks.html#ZerosOnRightLinear
  // idea: new node level is the number of trailing zero bits in a random #.
  unsigned int v =
      threadRNGs[tid * PREFETCH_SIZE_WORDS]
          .nextNatural();  // 32-bit word input to count zero bits on right
  unsigned int c = 32;     // c will be the number of zero bits on the right
  v &= -signed(v);
  if (v) c--;
  if (v & 0x0000FFFF) c -= 16;
  if (v & 0x00FF00FF) c -= 8;
  if (v & 0x0F0F0F0F) c -= 4;
  if (v & 0x33333333) c -= 2;
  if (v & 0x55555555) c -= 1;
  return (c < SKIPLIST_MAX_LEVEL) ? c : SKIPLIST_MAX_LEVEL - 1;
}

template <typename K, typename V, class RecordMgr>
void unsafe_skiplist<K, V, RecordMgr>::initNode(const int tid, nodeptr p_node,
                                                K key, V value, int height) {
  p_node->key = key;
  p_node->val = value;
  p_node->topLevel = height;
  p_node->lock = 0;
  p_node->marked = (long long)0;
  p_node->fullyLinked = (long long)0;
}

template <typename K, typename V, class RecordMgr>
nodeptr unsafe_skiplist<K, V, RecordMgr>::allocateNode(const int tid) {
  nodeptr nnode = new node_t<K, V>;
  if (nnode == NULL) {
    cout << "ERROR: out of memory" << endl;
    exit(-1);
  }
  return nnode;
}

template <typename K, typename V, class RecordMgr>
int unsafe_skiplist<K, V, RecordMgr>::find_impl(const int tid, K key,
                                                nodeptr* p_preds,
                                                nodeptr* p_succs,
                                                nodeptr* p_found) {
  int level;
  int l_found = -1;
  nodeptr p_pred = NULL;
  nodeptr p_curr = NULL;

  p_pred = p_head;

  for (level = SKIPLIST_MAX_LEVEL - 1; level >= 0; level--) {
    p_curr = p_pred->p_next[level];
    while (key > p_curr->key) {
      p_pred = p_curr;
      p_curr = p_pred->p_next[level];
    }
    if (l_found == -1 && key == p_curr->key) {
      l_found = level;
    }
    p_preds[level] = p_pred;
    p_succs[level] = p_curr;
  }
  if (p_found) *p_found = p_curr;
  return l_found;
}

template <typename K, typename V, class RecManager>
unsafe_skiplist<K, V, RecManager>::unsafe_skiplist(const int numProcesses,
                                                   const K _KEY_MIN,
                                                   const K _KEY_MAX,
                                                   const V NO_VALUE,
                                                   Random* const threadRNGs)
    : NUM_PROCESSES(numProcesses),
      recmgr(new RecManager(numProcesses, 0)),
      threadRNGs(threadRNGs)
#ifdef USE_DEBUGCOUNTERS
      ,
      counters(new debugCounters(numProcesses))
#endif
      ,
      KEY_MIN(_KEY_MIN),
      KEY_MAX(_KEY_MAX),
      NO_VALUE(NO_VALUE) {

  // note: initThread calls rqProvider->initThread

  int i;
  const int dummyTid = 0;
  recmgr->initThread(dummyTid);

  p_tail = new node_t<K, V>();
  initNode(dummyTid, p_tail, KEY_MAX, NO_VALUE, SKIPLIST_MAX_LEVEL - 1);
  p_tail->fullyLinked = 1;

  p_head = new node_t<K, V>();
  initNode(dummyTid, p_head, KEY_MIN, NO_VALUE, SKIPLIST_MAX_LEVEL - 1);
  p_head->fullyLinked = 1;

  for (i = 0; i < SKIPLIST_MAX_LEVEL; i++) {
    p_head->p_next[i] = p_tail;
  }
}

template <typename K, typename V, class RecManager>
unsafe_skiplist<K, V, RecManager>::~unsafe_skiplist() {
  const int dummyTid = 0;
  nodeptr curr = p_head;
  while (curr->key < KEY_MAX) {
    auto tmp = curr;
    curr = curr->p_next[0];
  }
  recmgr->printStatus();
  delete recmgr;
#ifdef USE_DEBUGCOUNTERS
  delete counters;
#endif
}

template <typename K, typename V, class RecManager>
void unsafe_skiplist<K, V, RecManager>::initThread(const int tid) {
  if (init[tid])
    return;
  else
    init[tid] = !init[tid];

  recmgr->initThread(tid);
}

template <typename K, typename V, class RecManager>
void unsafe_skiplist<K, V, RecManager>::deinitThread(const int tid) {
  if (!init[tid])
    return;
  else
    init[tid] = !init[tid];

  recmgr->deinitThread(tid);
}

template <typename K, typename V, class RecManager>
bool unsafe_skiplist<K, V, RecManager>::contains(const int tid, K key) {
  nodeptr p_preds[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_succs[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_found = NULL;
  int lFound;
  bool res;
  lFound = find_impl(tid, key, p_preds, p_succs, &p_found);
  res = (lFound != -1) && p_succs[lFound]->fullyLinked &&
        !p_succs[lFound]->marked;
#ifdef RQ_SNAPCOLLECTOR
  if (lFound != -1) rqProvider->search_report_target_key(tid, key, p_found);
#endif
  return res;
}

template <typename K, typename V, class RecManager>
const pair<V, bool> unsafe_skiplist<K, V, RecManager>::find(const int tid,
                                                            const K& key) {
  nodeptr p_preds[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_succs[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_found = NULL;
  int lFound;
  bool res;
  lFound = find_impl(tid, key, p_preds, p_succs, &p_found);
  res = (lFound != -1) && p_succs[lFound]->fullyLinked &&
        !p_succs[lFound]->marked;
#ifdef RQ_SNAPCOLLECTOR
  if (lFound != -1) rqProvider->search_report_target_key(tid, key, p_found);
#endif
  if (res) {
    return pair<V, bool>(p_found->val, true);
  } else {
    return pair<V, bool>(NO_VALUE, false);
  }
}

template <typename K, typename V, class RecManager>
V unsafe_skiplist<K, V, RecManager>::doInsert(const int tid, const K& key,
                                              const V& value,
                                              bool onlyIfAbsent) {
  nodeptr p_preds[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_succs[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_node_found = NULL;
  nodeptr p_pred = NULL;
  nodeptr p_succ = NULL;
  nodeptr p_new_node = NULL;
  V ret = NO_VALUE;
  int level;
  int topLevel = -1;
  int lFound = -1;
  int done = 0;

  topLevel = sl_randomLevel(tid, threadRNGs);
  while (!done) {
    lFound = find_impl(tid, key, p_preds, p_succs, NULL);
    if (lFound != -1) {
      p_node_found = p_succs[lFound];
      if (!p_node_found->marked) {
        while (!p_node_found->fullyLinked) {
          CPU_RELAX;
        }  // keep spinning

        // node is found and fully linked!
        if (onlyIfAbsent) {
          ret = p_node_found->val;
#ifdef RQ_SNAPCOLLECTOR
          rqProvider->insert_readonly_report_target_key(tid, p_node_found);
#endif
          return ret;
        } else {
          cout << "ERROR: insert-replace functionality not implemented for "
                  "unsafe_skiplist_impl"
               << endl;
          exit(-1);
        }
      }
      continue;  // try again
    }

    int highestLocked = -1;
    int valid = 1;
    for (level = 0; valid && (level <= topLevel); level++) {
      p_pred = p_preds[level];
      p_succ = p_succs[level];
      if (level == 0 || p_preds[level] != p_preds[level - 1]) {
        // don't try to lock same node twice
        sl_node_lock(p_pred);
      }
      highestLocked = level;
      // make sure nothing has changed in between
      valid = (!p_pred->marked && !p_succ->marked &&
               (p_pred->p_next[level] == p_succ));
    }

    if (valid) {
      p_new_node = new node_t<K, V>();  // shmem_none->allocateNode(tid);
#ifdef __HANDLE_STATS
      GSTATS_APPEND(tid, node_allocated_addresses,
                    ((long long)p_new_node) % (1 << 12));
#endif
      initNode(tid, p_new_node, key, value, topLevel);
      sl_node_lock(p_new_node);

      // Initialize bundle with the lowest level pointer.
      p_new_node->topLevel = topLevel;
      for (level = 0; level <= topLevel; level++) {
        p_new_node->p_next[level] = p_succs[level];
      }
      SOFTWARE_BARRIER;
      for (level = 0; level <= topLevel; level++) {
        p_preds[level]->p_next[level] = p_new_node;
      }
      // Bundle<node_t<K, V>>* bundles[] = {p_preds[0]->rqbundle,
      //                                    p_new_node->rqbundle, nullptr};
      // nodeptr ptrs[] = {p_new_node, p_succs[0], nullptr};
      // rqProvider->linearize_update_at_write(
      //     tid, &p_new_node->fullyLinked, (long long)1, bundles, ptrs,
      //     INSERT);
      p_new_node->fullyLinked = 1LL;
      // if (!p_preds[0]->validate()) {
        // std::cout << "Pointer mismatch! [key=" << p_preds[0]->p_next[0]->key
        //           << ",marked=" << p_preds[0]->p_next[0]->marked << "] "
        //           << p_preds[0]->p_next[0]
        //           << " vs. [key=" <<
        //           p_preds[0]->rqbundle->getHead()->ptr_->key
        //           << ",marked=" <<
        //           p_preds[0]->rqbundle->getHead()->ptr_->marked
        //           << "] " << p_preds[0]->rqbundle->dump(0) << std::flush;
        // exit(1);
      // }
#ifdef __HANDLE_STATS
      GSTATS_ADD_IX(tid, skiplist_inserted_on_level, 1, topLevel);
#endif
      // p_new_node->fullyLinked = 1;
      sl_node_unlock(p_new_node);
      done = 1;
    }

    // unlock everything here
    for (level = 0; level <= highestLocked; level++) {
      if (level == 0 || p_preds[level] != p_preds[level - 1]) {
        // don't try to unlock the same node twice
        sl_node_unlock(p_preds[level]);
      }
    }
  }
  return ret;
}

template <typename K, typename V, class RecManager>
V unsafe_skiplist<K, V, RecManager>::erase(const int tid, const K& key) {
  nodeptr p_preds[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_succs[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_victim = NULL;
  nodeptr p_pred = NULL;
  int i;
  int level;
  int lFound;
  int highestLocked;
  int valid;
  int isMarked = 0;
  int topLevel = -1;
  V ret = NO_VALUE;

  while (1) {
    lFound = find_impl(tid, key, p_preds, p_succs, NULL);
    if (lFound == -1) {
      break;
    }
    p_victim = p_succs[lFound];

    if ((!isMarked) || (p_victim->fullyLinked &&
                        (p_victim->topLevel == lFound) && !p_victim->marked)) {
      if (!isMarked) {
        topLevel = p_victim->topLevel;
        sl_node_lock(p_victim);
        if (p_victim->marked) {
          sl_node_unlock(p_victim);
          // ret = 0; ret is already NO_VALUE = fail
          break;
        }
      }

      highestLocked = -1;
      valid = 1;

      for (level = 0; valid && (level <= topLevel); level++) {
        p_pred = p_preds[level];
        if (level == 0 ||
            p_preds[level] != p_preds[level - 1]) {  // don't do twice
          sl_node_lock(p_pred);
        }
        highestLocked = level;
        valid = (!p_pred->marked && (p_pred->p_next[level] == p_victim));
      }

      if (valid) {
        // Bundle<node_t<K, V>>* bundles[] = {p_preds[0]->rqbundle, nullptr};
        // nodeptr ptrs[] = {p_victim->p_next[0], nullptr};
        // rqProvider->linearize_update_at_write(
        //     tid, &p_victim->marked, (long long)1, bundles, ptrs, REMOVE);
        p_victim->marked = 1LL;
        for (level = topLevel; level >= 0; level--) {
          p_preds[level]->p_next[level] = p_victim->p_next[level];
        }
        // nodeptr deletedNodes[] = {p_victim, nullptr};
        // rqProvider->physical_deletion_succeeded(tid, deletedNodes);
        // if (!p_preds[0]->validate()) {
          // std::cout << "Pointer mismatch! [key=" <<
          // p_preds[0]->p_next[0]->key
          //           << ",marked=" << p_preds[0]->p_next[0]->marked << "] "
          //           << p_preds[0]->p_next[0] << " vs. [key="
          //           << p_preds[0]->rqbundle->getHead()->ptr_->key <<
          //           ",marked="
          //           << p_preds[0]->rqbundle->getHead()->ptr_->marked << "] "
          //           << p_preds[0]->rqbundle->getHead()->ptr_ << " "
          //           << p_preds[0]->rqbundle->dump(0) << std::flush;
          // exit(1);
        // }
        ret = p_victim->val;
        sl_node_unlock(p_victim);
      } else {
        sl_node_unlock(p_victim);
      }

      // unlock mutexes
      for (i = 0; i <= highestLocked; i++) {
        if (i == 0 || p_preds[i] != p_preds[i - 1]) {
          sl_node_unlock(p_preds[i]);
        }
      }

      if (valid) {
        break;
      }
    }
  }
  //    if (ret != NO_VALUE) {
  //        recmgr->retire(tid, (nodeptr) p_victim);
  //    }
  return ret;
}

template <typename K, typename V, class RecManager>
int unsafe_skiplist<K, V, RecManager>::rangeQuery(const int tid, const K& lo,
                                                  const K& hi,
                                                  K* const resultKeys,
                                                  V* const resultValues) {
  //    cout<<"rangeQuery(lo="<<lo<<" hi="<<hi<<")"<<endl;
  int cnt = 0;
  nodeptr p_preds[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  nodeptr p_succs[SKIPLIST_MAX_LEVEL] = {
      0,
  };
  int lFound = find_impl(tid, lo, p_preds, p_succs, NULL);
  nodeptr curr = p_succs[0];
  while (curr->key < hi) {
    cnt += getKeys(tid, curr, resultKeys + cnt, resultValues + cnt);
    curr = curr->p_next[0];
  }
  return cnt;
}

#endif /* SKIPLIST_LOCK_IMPL_H */
