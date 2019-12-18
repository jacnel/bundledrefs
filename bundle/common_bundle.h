#ifndef BUNDLE_COMMON_BUNDLE_H
#define BUNDLE_COMMON_BUNDLE_H

typedef long long timestamp_t;
#define BUNDLE_NULL_TIMESTAMP 0
#define BUNDLE_MIN_TIMESTAMP 1
#define BUNDLE_MAX_TIMESTAMP (LLONG_MAX - 1)
#define BUNDLE_PENDING_TIMESTAMP LLONG_MAX

template <typename NodeType>
class BundleInterface {
 public:
  virtual NodeType *getPtrByTimestamp(timestamp_t ts) = 0;
  virtual int getSize() = 0;
  virtual void reclaimEntries(timestamp_t ts) = 0;
  virtual void prepare(NodeType *ptr) = 0;
  virtual void finalize(timestamp_t ts) = 0;
};

#endif // BUNDLE_COMMON_BUNDLE_H