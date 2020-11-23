# Foreward

We would first like to acknowledge that this project is built on top of a benchmark suite developed by Maya Arbel-Raviv and Trevor Brown. We thank them for making the source code available, it was invaluable to the success of our own work.

# Overview

The following is a document intended to support an artifact evaluation for the paper "Bundled References: An Abstraction for Highly-Concurrent Linearizable Range Queries" by Jacob Nelson, Ahmed Hasan and Roberto Palmieri. The core contributions with respect to implementation are contained in the directorys prefixed with "bundle".

'bundle' implements the bundling interface as a linked list of bundle entries. In addition to the linked list bundle, there is a cirular buffer bundle (not included in the paper) as well as an unsafe version that eliminates the overhead of ensuring bundle consistency.
'bundle_lazylist', 'bundle_skiplistlock' and 'bundle_citrus' each implement a data structure to which we apply bundling. We do not apply our technique to any data structures that are lock-free because our current bundling implementation would impose blocking.

The experiments that we report in the paper are located in the 'microbench' and 'macrobench' directories.

'microbench' tests each data structure in isolation.
'macrobench' ports DBx1000 to include the implemented data structures.

# Requirements

C++ Libraries:
libnuma

Python 3.x
plotly 
plotly-orca
psutils
requests
pandas

# Getting Started Guide

The following commands will build the necessary binaries, run the microbenchmark, and generate the plots included in the paper. From the root directory, run the following:

```
cd microbench
make -j lazylist skiplistlock citrus rlu lbundle unsafe
./runscript.sh
cd ..
python plot.py --save_plots --microbench
```

The first three arguments to the `make` command (i.e., lazylist, skiplistlock, citrus) build the EBR-based approach from Arbel-Raviv and Brown. The next argument (i.e., rlu) builds the RLU-based lazy-list and Citrus tree. The fifth argument (i.e., lbundle) builds the linked bundle lazy-list, optimistic skip-list and Citrus tree. Finally, the last argument (i.e., unsafe) builds the three data structures of interest with no instrumentation for range queries. Unlike the unsafe implementation provided by Arbel-Raviv and Brown, our implementation does not reclaim memory. We chose to do this because the RLU-based data structures do not utilize epoch-based memory reclamation. As such, our unsafe versions are an upper bound on all range query techniques and provides a more general reference.

`./runscript.sh` will run expeirments based on 'experiment_list_generate.sh', which will write a list of experiments to be run to a file. 'runscript.sh' also defines the number of trials and the length of each run, which for the sake of time we have limited to 1 trial and .5 seconds per run. 'experiment_list_generate.sh' defines the data structures, key ranges and range query techniques to test. Again, for the sake of simplicity we configure it out of the box to only run tests for the optimistic skip-list. The experiment generation file includes two experiments. One for throughput as a function of range queries and another for throughput for various workloads.

