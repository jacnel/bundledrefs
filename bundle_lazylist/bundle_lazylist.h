#ifndef LAZYLIST_H
#define LAZYLIST_H

#include <unordered_set>
#include <stack>

#ifndef MAX_NODES_INSERTED_OR_DELETED_ATOMICALLY
// define BEFORE including rq_provider.h
#define MAX_NODES_INSERTED_OR_DELETED_ATOMICALLY 4
#endif
#include "bundle_lazylist_impl.h"
#include "rq_bundle.h"

template <typename K, typename V>
class node_t;
#define nodeptr node_t<K, V>*

template <typename K, typename V, class RecManager>
class bundle_lazylist {
 private:
  RecManager* const recordmgr;
  RQProvider<K, V, node_t<K, V>, bundle_lazylist<K, V, RecManager>, RecManager,
             true, false>* const rqProvider;
#ifdef USE_DEBUGCOUNTERS
  debugCounters* const counters;
#endif
  nodeptr head;

  int validateLinks(const int tid, nodeptr pred, nodeptr curr);
  nodeptr new_node(const int tid, const K& key, const V& val, nodeptr next);
  long long debugKeySum(nodeptr head);

  V doInsert(const int tid, const K& key, const V& value, bool onlyIfAbsent);

  int init[MAX_TID_POW2] = {
      0,
  };

 public:
  const K KEY_MIN;
  const K KEY_MAX;
  const V NO_VALUE;
  bundle_lazylist(int numProcesses, const K _KEY_MIN, const K _KEY_MAX,
                  const V NO_VALUE);
  ~bundle_lazylist();
  bool contains(const int tid, const K& key);
  V insert(const int tid, const K& key, const V& value) {
    return doInsert(tid, key, value, false);
  }
  V insertIfAbsent(const int tid, const K& key, const V& value) {
    return doInsert(tid, key, value, true);
  }
  V erase(const int tid, const K& key);
  int rangeQuery(const int tid, const K& lo, const K& hi, K* const resultKeys,
                 V* const resultValues);

  /**
   * This function must be called once by each thread that will
   * invoke any functions on this class.
   *
   * It must be okay that we do this with the main thread and later with another
   * thread!!!
   */
  void initThread(const int tid);
  void deinitThread(const int tid);
#ifdef USE_DEBUGCOUNTERS
  debugCounters* debugGetCounters() { return counters; }
  void clearCounters() { counters->clear(); }
#endif
  long long debugKeySum();
  bool validate(const long long keysum, const bool checkkeysum) { return true; }
  //    void validateRangeQueries(const long long prefillKeyChecksum) {
  //        rqProvider->validateRQs(prefillKeyChecksum);
  //    }
  long long getSizeInNodes() {
    long long size = 0;
    for (nodeptr curr = head->next; curr->key != KEY_MAX; curr = curr->next) {
      ++size;
    }
    return size;
  }
  long long getSize() {
    long long size = 0;
    for (nodeptr curr = head->next; curr->key != KEY_MAX; curr = curr->next) {
      size += (!curr->marked);
    }
    return size;
  }
  string getSizeString() {
    stringstream ss;
    ss << getSizeInNodes() << " nodes in data structure";
    return ss.str();
  }

  RecManager* const debugGetRecMgr() { return recordmgr; }

  inline int getKeys(const int tid, node_t<K, V>* node, K* const outputKeys,
                     V* const outputValues) {
    // ignore marked
    outputKeys[0] = node->key;
    outputValues[0] = node->val;
    return 1;
  }

  bool isInRange(const K& key, const K& lo, const K& hi) {
    return (lo <= key && key <= hi);
  }
  inline bool isLogicallyDeleted(const int tid, node_t<K, V>* node);

  inline bool isLogicallyInserted(const int tid, node_t<K, V>* node) {
    return true;
  }

  node_t<K, V>* debug_getEntryPoint() { return head; }

  string getBundleStatsString() {
    unsigned int max = -1;
    long num_nodes = 0;
    long total = 0;
    stack<nodeptr> s;
    unordered_set<nodeptr> unique;
    nodeptr curr = head;
    s.push(curr);
    while (!s.empty()) {
      // Try to add the current node to set of unique nodes.
      curr = s.top();
      s.pop();
      auto result = unique.insert(curr);
      if (result.second) {
        // If this is an unseen node, update stats.
        ++num_nodes;
        int size = curr->rqbundle->getSize();
        if (size > max) {
          max = size;
        }
        total += size;

        // Add all nodes in the bundle to s, if we haven't seen this
        // node before.
        BundleEntry<node_t<K, V>>* bundle_entry = curr->rqbundle->getHead();
        while (bundle_entry->ts_ != BUNDLE_NULL_TIMESTAMP) {
          if (bundle_entry->ptr_ != nullptr) {
            s.push((nodeptr)bundle_entry->ptr_);
          }
          bundle_entry = bundle_entry->next_;
        }
      }
    }

    stringstream ss;
    ss << "total reachable nodes         : " << num_nodes << endl;
    ss << "average bundle size           : " << (total / (double)num_nodes)
       << endl;
    return ss.str();
  }
};

#endif /* LAZYLIST_H */
