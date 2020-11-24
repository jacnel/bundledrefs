###### MICROBENCHMARK PLOT CONFIG ######

## Points to location of microbenchmark data (should not change)
microbench_dir = './microbench/data'

### "workloads" experiment configuration ###

## Must correspond to one of the rqrates in run_workloads() in ./microbench/experiment_list_generate.sh
workloads_rqrate = 10
## Only change if you know what you are doing. Must correspong to urates in run_workloads() in ./microbench/experiment_list_generate.sh
workloads_urates = [0, 2, 10, 50, 90, 100]

### "rqsize" experiment configuration ###

## Must correspond to one of the ksizes in ./microbench/experiment_list_generate.sh
rqsize_max_key = 100000

#########################################

###### MACROBENCHMARK PLOT CONFIG ######

# Points to location of macrobenchmark data (should not change)
macrobench_dir = './macrobench/data'

#########################################
