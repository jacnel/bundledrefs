include ../config.mk
PLAF = -DLOGICAL_PROCESSORS=$(maxthreads_powerof2) -DMAX_TID_POW2=$(maxthreads_powerof2) -DCPU_FREQ_GHZ=$(cpu_freq_ghz) -DCPU_FREQ=$(cpu_freq_ghz)

GPP = g++
FLAGS = -std=c++11 -mcx16 
FLAGS += -O3
# FLAGS += -O0 -fsanitize=address -static-libasan -fsanitize=leak
FLAGS += -g
FLAGS += -DNDEBUG
FLAGS += $(PLAF)
FLAGS += -DUSE_GSTATS
FLAGS += -DNO_FREE
#FLAGS += -DUSE_STL_HASHLIST
FLAGS += -DUSE_SIMPLIFIED_HASHLIST
#FLAGS += -DRAPID_RECLAMATION
#FLAGS += -DRWLOCK_PTHREADS
#FLAGS += -DRWLOCK_FAVOR_WRITERS
FLAGS += -DRWLOCK_FAVOR_READERS
#FLAGS += -DRWLOCK_COHORT_FAVOR_WRITERS
#FLAGS += -DSNAPCOLLECTOR_PRINT_RQS
#FLAGS += -DUSE_RQ_DEBUGGING -DRQ_VALIDATION
#FLAGS += -DRQ_VISITED_IN_BAGS_HISTOGRAM
#FLAGS += -DRQ_HISTOGRAM
#FLAGS += -DADD_DELAY_BEFORE_DTIME
#FLAGS += -DRQ_LOCKFREE_WAITS_FOR_DTIME
#FLAGS += -DUSE_DEBUGCOUNTERS
#FLAGS += -DBLOCKBAG_ITERATOR_COUNT_BLOCKS_TRAVERSED
#FLAGS += -DDEBUG=if\(1\) -DDEBUG1=if\(1\) -DDEBUG2=if\(1\)
#FLAGS += -DDEBUG=if\(1\) -DDEBUG1=if\(0\) -DDEBUG2=if\(0\)
FLAGS += -DDEBUG=if\(0\) -DDEBUG1=if\(0\) -DDEBUG2=if\(0\)
FLAGS += -DMEMORY_STATS=if\(1\) -DMEMORY_STATS2=if\(1\)
#FLAGS += -DMEMORY_STATS=if\(0\) -DMEMORY_STATS2=if\(0\)
FLAGS += -DINSERT_FUNC=insertIfAbsent
#FLAGS += -DUSE_PAPI
# FLAGS += -DUSE_TRACE

# FLAGS += -DDEBRA_DISABLE_READONLY_OPT
#FLAGS += -DEERPRCU_DISABLE_RDTSC_TTAS
# FLAGS += -DSKIPLIST_DEBUGGING_FLATTEN_MAX_LEVEL

# Include bundle configuration macros
include bundle.mk

LDFLAGS = -L../lib
LDFLAGS += -I../
LDFLAGS += -I../bst
LDFLAGS += -I../vcas_bst
LDFLAGS += -I../bslack_reuse
LDFLAGS += -I../citrus
LDFLAGS += -I../common
LDFLAGS += -I../dcss_plus
LDFLAGS += -I../descriptors
LDFLAGS += -I../include
LDFLAGS += -I../lazylist
LDFLAGS += -I../lockfree_list
LDFLAGS += -I../lockfree_skiplist
LDFLAGS += -I../skiplist_lock
LDFLAGS += -I../microbench
LDFLAGS += -I../recordmgr
LDFLAGS += -I../rlu
LDFLAGS += -I../rlu_citrus
LDFLAGS += -I../rlu_linked_list
LDFLAGS += -I../rq
LDFLAGS += -I../rq/snapcollector

# Bundle specific includes.
LDFLAGS += -I../bundle
LDFLAGS += -I../bundle_lazylist
LDFLAGS += -I../bundle_skiplist_lock
LDFLAGS += -I../bundle_citrus
LDFLAGS += -I../bundle_bst
# -------------------------

# Unsafe specific includes.
LDFLAGS += -I../unsafe/lazylist/
LDFLAGS += -I../unsafe/skiplist_lock/
LDFLAGS += -I../unsafe/citrus/
# -------------------------

LDFLAGS += -lpthread
LDFLAGS += -ldl
LDFLAGS += -lnuma
LDFLAGS += -lpapi

machine=$(shell hostname)

all: abtree bslack bst lazylist lflist citrus rlu skiplistlock bundle ubundle

.PHONY: bundle rbundle
bundle: citrus.rq_bundle skiplistlock.rq_bundle lazylist.rq_bundle
rbundle: citrus.rq_rbundle skiplistlock.rq_rbundle lazylist.rq_rbundle
tsbundle: citrus.rq_tsbundle skiplistlock.rq_tsbundle lazylist.rq_tsbundle

BUNDLE_FLAGS = -DRQ_BUNDLE -DBUNDLE_LINKED_BUNDLE 
BUNDLE_FLAGS_RESTARTS = -DRQ_BUNDLE -DBUNDLE_LINKED_BUNDLE -DBUNDLE_RESTARTS
BUNDLE_FLAGS_RQ_TIMESTAMP = -DRQ_BUNDLE -DBUNDLE_LINKED_BUNDLE -DBUNDLE_RQTS -DBUNDLE_RESTARTS

thispath=

# .PHONY: abtree abtree.rq_lockfree abtree.rq_rwlock abtree.rq_htm_rwlock abtree.rq_unsafe
# abtree: abtree.rq_lockfree abtree.rq_rwlock abtree.rq_htm_rwlock abtree.rq_unsafe
# abtree.rq_lockfree:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DABTREE -DRQ_LOCKFREE $(pinning) $(thispath)main.cpp $(LDFLAGS)
# abtree.rq_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DABTREE -DRQ_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# abtree.rq_htm_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DABTREE -DRQ_HTM_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# abtree.rq_unsafe:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DABTREE -DRQ_UNSAFE $(pinning) $(thispath)main.cpp $(LDFLAGS)

# .PHONY: bslack bslack.rq_lockfree bslack.rq_rwlock bslack.rq_htm_rwlock bslack.rq_unsafe
# bslack: bslack.rq_lockfree bslack.rq_rwlock bslack.rq_htm_rwlock bslack.rq_unsafe
# bslack.rq_lockfree:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBSLACK -DRQ_LOCKFREE $(pinning) $(thispath)main.cpp $(LDFLAGS)
# bslack.rq_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBSLACK -DRQ_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# bslack.rq_htm_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBSLACK -DRQ_HTM_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# bslack.rq_unsafe:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBSLACK -DRQ_UNSAFE $(pinning) $(thispath)main.cpp $(LDFLAGS)

.PHONY: lazylist lazylist.rq_lockfree lazylist.rq_rwlock lazylist.rq_htm_rwlock lazylist.rq_unsafe lazylist.rq_bundle lazylist.rq_rbundle lazylist.rq_tsbundle
lazylist: lazylist.rq_lockfree lazylist.rq_rwlock lazylist.rq_htm_rwlock lazylist.rq_unsafe lazylist.rq_bundle lazylist.rq_rbundle lazylist.rq_tsbundle
lazylist.rq_lockfree:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLAZYLIST -DRQ_LOCKFREE $(pinning) $(thispath)main.cpp $(LDFLAGS)
lazylist.rq_rwlock:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLAZYLIST -DRQ_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# lazylist.rq_htm_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLAZYLIST -DRQ_HTM_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# lazylist.rq_unsafe:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLAZYLIST -DRQ_UNSAFE $(pinning) $(thispath)main.cpp $(LDFLAGS)
lazylist.rq_bundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_LIST ${BUNDLE_FLAGS} $(pinning) $(thispath)main.cpp $(LDFLAGS)
lazylist.rq_rbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_LIST ${BUNDLE_FLAGS_RESTARTS} $(pinning) $(thispath)main.cpp $(LDFLAGS)
lazylist.rq_tsbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_LIST ${BUNDLE_FLAGS_RQ_TIMESTAMP} $(pinning) $(thispath)main.cpp $(LDFLAGS)


# .PHONY: lflist lflist.rq_lockfree lflist.rq_rwlock lflist.rq_htm_rwlock lflist.rq_unsafe lflist.rq_snapcollector
# lflist: lflist.rq_lockfree lflist.rq_rwlock lflist.rq_htm_rwlock lflist.rq_unsafe lflist.rq_snapcollector
# lflist.rq_lockfree:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLFLIST -DRQ_LOCKFREE $(pinning) $(thispath)main.cpp $(LDFLAGS)
# lflist.rq_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLFLIST -DRQ_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# lflist.rq_htm_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLFLIST -DRQ_HTM_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# lflist.rq_unsafe:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLFLIST -DRQ_UNSAFE $(pinning) $(thispath)main.cpp $(LDFLAGS)
# lflist.rq_snapcollector:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DLFLIST -DRQ_SNAPCOLLECTOR $(pinning) $(thispath)main.cpp $(LDFLAGS)

.PHONY: skiplistlock skiplistlock.rq_lockfree skiplistlock.rq_rwlock skiplistlock.rq_htm_rwlock skiplistlock.rq_unsafe skiplistlock.rq_snapcollector skiplistlock.rq_bundle skiplistlock.rq_rbundle skiplistlock.rq_tsbundle
skiplistlock: skiplistlock.rq_lockfree skiplistlock.rq_rwlock skiplistlock.rq_htm_rwlock skiplistlock.rq_unsafe skiplistlock.rq_snapcollector skiplistlock.rq_bundle skiplistlock.rq_rbundle skiplistlock.rq_tsbundle
skiplistlock.rq_lockfree:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DSKIPLISTLOCK -DRQ_LOCKFREE $(pinning) $(thispath)main.cpp $(LDFLAGS)
skiplistlock.rq_rwlock:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DSKIPLISTLOCK -DRQ_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# skiplistlock.rq_htm_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DSKIPLISTLOCK -DRQ_HTM_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# skiplistlock.rq_unsafe:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DSKIPLISTLOCK -DRQ_UNSAFE $(pinning) $(thispath)main.cpp $(LDFLAGS)
skiplistlock.rq_snapcollector:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DSKIPLISTLOCK -DRQ_SNAPCOLLECTOR $(pinning) $(thispath)main.cpp $(LDFLAGS)
skiplistlock.rq_bundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_SKIPLIST ${BUNDLE_FLAGS} $(pinning) $(thispath)main.cpp $(LDFLAGS)
skiplistlock.rq_rbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_SKIPLIST ${BUNDLE_FLAGS_RESTARTS} $(pinning) $(thispath)main.cpp $(LDFLAGS)
skiplistlock.rq_tsbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_SKIPLIST ${BUNDLE_FLAGS_RESTARTS} $(pinning) $(thispath)main.cpp $(LDFLAGS)

.PHONY: bst bst.rq_lockfree bst.rq_rwlock bst.rq_htm_rwlock bst.rq_unsafe bst.rq_vcas bst.rq_bundle
bst: bst.rq_lockfree bst.rq_rwlock bst.rq_htm_rwlock bst.rq_unsafe bst.rq_vcas bst.rq_bundle
bst.rq_lockfree:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBST -DRQ_LOCKFREE $(pinning) $(thispath)main.cpp $(LDFLAGS)
bst.rq_rwlock:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(;ilesuffix).out $(xargs) -DBST -DRQ_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# bst.rq_htm_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBST -DRQ_HTM_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
bst.rq_unsafe:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBST -DRQ_UNSAFE $(pinning) $(thispath)main.cpp $(LDFLAGS)
bst.rq_vcas:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DVCASBST -DRQ_VCAS $(pinning) $(thispath)main.cpp $(LDFLAGS)
# bst.rq_bundle:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRQ_BUNDLE -DBUNDLE_LINKED_BUNDLE -DBUNDLE_BST $(pinning) $(thispath)main.cpp $(LDFLAGS)

.PHONY: citrus citrus.rq_lockfree citrus.rq_rwlock citrus.rq_htm_rwlock citrus.rq_unsafe citrus.rq_bundle citrus.rq_rbundle citrus.rq_tsbundle
citrus: citrus.rq_lockfree citrus.rq_rwlock citrus.rq_htm_rwlock citrus.rq_unsafe citrus.rq_bundle citrus.rq_rbundle citrus.rq_tsbundle
citrus.rq_lockfree:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DCITRUS -DRQ_LOCKFREE $(pinning) $(thispath)main.cpp $(LDFLAGS)
citrus.rq_rwlock:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DCITRUS -DRQ_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# citrus.rq_htm_rwlock:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DCITRUS -DRQ_HTM_RWLOCK $(pinning) $(thispath)main.cpp $(LDFLAGS)
# citrus.rq_unsafe:
# 	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DCITRUS -DRQ_UNSAFE $(pinning) $(thispath)main.cpp $(LDFLAGS)
citrus.rq_bundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_CITRUS ${BUNDLE_FLAGS} $(pinning) $(thispath)main.cpp $(LDFLAGS)
citrus.rq_rbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_CITRUS ${BUNDLE_FLAGS_RESTARTS} $(pinning) $(thispath)main.cpp $(LDFLAGS)
citrus.rq_tsbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DBUNDLE_CITRUS ${BUNDLE_FLAGS_RESTARTS} $(pinning) $(thispath)main.cpp $(LDFLAGS)

.PHONY: rlu lazylist.rq_rlu citrus.rq_rlu
rlu: lazylist.rq_rlu citrus.rq_rlu
lazylist.rq_rlu:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRLU_LIST $(pinning) $(thispath)main.cpp $(thispath)../rlu/rlu.cpp $(LDFLAGS)
citrus.rq_rlu:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRLU_CITRUS $(pinning) $(thispath)main.cpp $(thispath)../rlu/rlu.cpp $(LDFLAGS)

.PHONY: ubundle lazylist.rq_ubundle skiplistlock.rq_ubundle citrus.rq_ubundle 
ubundle: lazylist.rq_ubundle skiplistlock.rq_ubundle citrus.rq_ubundle 
lazylist.rq_ubundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRQ_BUNDLE -DBUNDLE_UNSAFE_BUNDLE -DBUNDLE_LIST $(pinning) $(thispath)main.cpp $(LDFLAGS)
skiplistlock.rq_ubundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRQ_BUNDLE -DBUNDLE_UNSAFE_BUNDLE -DBUNDLE_SKIPLIST $(pinning) $(thispath)main.cpp $(LDFLAGS)
citrus.rq_ubundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRQ_BUNDLE -DBUNDLE_UNSAFE_BUNDLE -DBUNDLE_CITRUS $(pinning) $(thispath)main.cpp $(LDFLAGS)

## The following is an experimental bundle implementation that uses a circular buffer instead of a linked list.
.PHONY: cbundle lazylist.rq_cbundle skiplistlock.rq_cbundle citrus.rq_cbundle
cbundle: lazylist.rq_cbundle skiplistlock.rq_cbundle citrus.rq_cbundle
lazylist.rq_cbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRQ_BUNDLE -DBUNDLE_CIRCULAR_BUNDLE -DBUNDLE_LIST $(pinning) $(thispath)main.cpp $(LDFLAGS)
skiplistlock.rq_cbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRQ_BUNDLE -DBUNDLE_CIRCULAR_BUNDLE -DBUNDLE_SKIPLIST $(pinning) $(thispath)main.cpp $(LDFLAGS)
citrus.rq_cbundle:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DRQ_BUNDLE -DBUNDLE_CIRCULAR_BUNDLE -DBUNDLE_CITRUS $(pinning) $(thispath)main.cpp $(LDFLAGS)

.PHONY: unsafe lazylist.rq_unsafe skiplistlock.rq_unsafe citrus.rq_unsafe
unsafe: lazylist.rq_unsafe skiplistlock.rq_unsafe citrus.rq_unsafe
lazylist.rq_unsafe:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DUNSAFE_LIST $(pinning) $(thispath)main.cpp $(LDFLAGS)
skiplistlock.rq_unsafe:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DUNSAFE_SKIPLIST $(pinning) $(thispath)main.cpp $(LDFLAGS)
citrus.rq_unsafe:
	$(GPP) $(FLAGS) -o $(thispath)$(machine).$@$(filesuffix).out $(xargs) -DUNSAFE_CITRUS $(pinning) $(thispath)main.cpp $(LDFLAGS)

.PHONY: clean
clean:
	rm *.out
