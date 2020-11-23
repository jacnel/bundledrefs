# These are bundle-specific macros to be included in Makefile.

# Helpful flags for debugging.
# FLAGS += -DBUNDLE_CLEANUP_NO_FREE
# FLAGS += -DBUNDLE_DEBUG
FLAGS += -DBUNDLE_PRINT_BUNDLE_STATS
# ---------------------------

# Bundle entry cleanup flags.
# FLAGS += -DBUNDLE_CLEANUP_UPDATE
FLAGS += -DBUNDLE_CLEANUP_BACKGROUND
FLAGS += -DBUNDLE_CLEANUP_SLEEP=100000  # ns
# --------------------------

# Relaxation optimization.
# FLAGS += -DBUNDLE_TIMESTAMP_RELAXATION=1000000
# ------------------------
