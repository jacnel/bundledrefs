###### MICROBENCHMARK PLOT CONFIG ######

## Points to location of microbenchmark data (should not change)
microbench_dir = './microbench/data'

### "workloads" experiment configuration ###

## Must correspond to one of the rqrates in run_workloads() in ./microbench/experiment_list_generate.sh
workloads_rqrate = 50
## Only change if you know what you are doing. Must correspong to urates in run_workloads() in ./microbench/experiment_list_generate.sh
workloads_urates = [0, 2, 10, 50, 90, 100]

### "rq_size" experiment configuration ###

## Must correspond to one of the ksizes in ./microbench/experiment_list_generate.sh
rqsize_max_key = 100000


### "rq_threads" experiment configuration ###
n_rq_threads = 36

#########################################

###### MACROBENCHMARK PLOT CONFIG ######

# Points to location of macrobenchmark data (should not change)
macrobench_dir = './macrobench/data'

#########################################
