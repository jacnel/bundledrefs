## Jacob Nelson
## 
## These are bundle-specific macros to be included in Makefile.

## Helpful flags for debugging.
# ---------------------------
# FLAGS += -DBUNDLE_CLEANUP_NO_FREE
# FLAGS += -DBUNDLE_DEBU
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
# FLAGS += -DBUNDLE_CLEANUP_BACKGROUND
# FLAGS += -DBUNDLE_CLEANUP_SLEEP=100000  # ns
# --------------------------

## Relaxation optimization. If this is enabled, then threads will 
## only increment the global timestamp after TIMSTAMP_RELAXATION 
## number of update operations
# ------------------------.
# FLAGS += -DBUNDLE_TIMESTAMP_RELAXATION=5
# ------------------------
