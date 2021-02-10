## Jacob Nelson
## 
## These are bundle-specific macros to be included in Makefile.

## Helpful flags for debugging.
# ---------------------------
# FLAGS += -DBUNDLE_CLEANUP_NO_FREE
# FLAGS += -DBUNDLE_DEBUG
FLAGS += -DBUNDLE_PRINT_BUNDLE_STATS
# ---------------------------


## Bundle entry cleanup flags. Uncoment CLEANUP_BACKGROUND to 
## enable a background thread cleanup of bundle entries. The 
## CLEANUP_SLEEP macro adjusts how many nanoseconds the background 
## thread sleeps between iterations. It is required if 
## CLENAUP_BACKGROUND is enabled. CLEANUP_UPDATE is an experimental 
## configuration that allows update operations to reclaim stale 
## bundle entries
# ------------------------.
# FLAGS += -DBUNDLE_CLEANUP_UPDATE
FLAGS += -DBUNDLE_CLEANUP_BACKGROUND
FLAGS += -DBUNDLE_CLEANUP_SLEEP=100000  # ns
# --------------------------

# FLAGS += -DBUNDLE_UPDATE_USES_CAS
# FLAGS += -DBUNDLE_RQTS

## Three-phase range query optimzation. Allows range queries to use 
## the regular pointers for the first (pre-traversal) phase. During 
## the second (range-entry) phase, the bundles must be followed to
## ensure that nothing is missed. At this point a range query may 
## restart if there are no longer any bundles to follow. If it enters
## the range then it can perform its collect operation without the
## possibility of restarts.
# ------------------------.
# FLAGS +=  -DBUNDLE_RESTARTS
# ------------------------

## Relaxation optimization. If this is enabled, then threads will 
## only increment the global timestamp after TIMSTAMP_RELAXATION 
## number of update operations
# ------------------------.
# FLAGS += -DBUNDLE_TIMESTAMP_RELAXATION=5
# ------------------------
