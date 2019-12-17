## Note: as a convenience hack, this file is included in Makefiles,
##       AND in bash scripts, to set some variables.
##       So, don't write anything that isn't valid in both make AND bash.

## Set the desired maximum thread count (maxthreads),
## an upper bound on the maximum thread count that is a power of 2 (maxthreads_powerof2),
## the maximum range query thread count (maxrqthreads) for use in experiments,
## the number of threads to increment by in the graphs produced by experiments (threadincrement),
## and the CPU frequency in GHz (cpu_freq_ghz) used for timing measurements with RDTSC.

maxthreads=7
maxthreads_powerof2=8
maxrqthreads=6
threadincrement=4
cpu_freq_ghz=2.1

## Configure the thread pinning/binding policy (see README.txt)
## Blank means no thread pinning. (Threads can run wherever they want.)
#pinning_policy="-bind 0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47"
pinning_policy="-bind 0,1,2,3,4,5,6,7"

## The policy commented out below is what we used on our 48 thread 2-socket
## Intel machine (where we pinned threads to alternating sockets).
#pinning_policy="-bind 0,24,12,36,1,25,13,37,2,26,14,38,3,27,15,39,4,28,16,40,5,29,17,41,6,30,18,42,7,31,19,43,8,32,20,44,9,33,21,45,10,34,22,46,11,35,23,47"
