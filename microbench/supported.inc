# The following functions help determine the supported configurations. If a warning appears in `plot.py`,
# it is probably because the plotting script is trying to generate plots for an unsupported configuration
# that was never run. This is expected behavior.

# Determines whether a given data structure `ds` supports a given range query algorithm `alg`.
# Returns 1 if the two input arguments are incompatible.
check_ds_technique() {
    ## args: ds alg
    if [ "$2" == "snapcollector" ] && [ "$1" != "lflist" ] && [ "$1" != "skiplistlock" ] ; then return 1 ; fi
    if [ "$2" == "rlu" ] && [ "$1" != "lazylist" ] && [ "$1" != "citrus" ] ; then return 1 ; fi
    if [ "$2" == "bundle" ] && [ "$1" != "lazylist" ] && [ "$1" != "skiplistlock" ] && [ "$1" != "citrus" ]; then return 1 ; fi
    if [ "$2" == "rbundle" ] && [ "$1" != "lazylist" ] && [ "$1" != "skiplistlock" ] && [ "$1" != "citrus" ]; then return 1 ; fi
    if [ "$2" == "vcas" ] && [ "$1" != "bst" ] && [ "$1" != "lazylist" ] && [ "$1" != "skiplistlock" ] && [ "$1" != "citrus" ]; then return 1 ; fi
    return 0
}
export -f check_ds_technique

# Checks if a given data structure `ds` should be run with a given number of keys `k`.
# Returns 1 if the two input arguments are incompatible.
check_ds_size() {
    ## args: ds k
    if [ "$2" == "1000000" ] && [ "$1" != "abtree" ]  && [ "$1" != "citrus" ] && [ "$1" != "skiplistlock" ] ; then return 1 ; fi
    if [ "$2" == "100000" ] && [ "$1" != "bst" ] && [ "$1" != "citrus" ] && [ "$1" != "skiplistlock" ]  ; then return 1 ; fi
    if [ "$2" == "10000" ] && [ "$1" != "lflist" ] && [ "$1" != "lazylist" ] ; then return 1 ; fi
    return 0
}
export -f check_ds_size
