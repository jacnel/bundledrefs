#!/bin/bash

source ../config.mk
rm -f experiment_list.txt >/dev/null

source ./supported.inc

## Overwrite datastructures and rqtechniques from 'supported.inc'
## Full experimental configurations.
rqtechniques="unsafe vcas rlu bundle tsbundle lockfree"
datastructures="lazylist skiplistlock citrus"
ksizes="10000 1000000"

prepare_exp() {
  echo 0 0 0 0 0 0 $1 prepare
}

run_workloads() {
  echo "Preparing workloads: THROUGHPUT WHILE VARYING WORKLOAD DISTRIBUTION"
  count=0
  rqsize=50
  # rqrates="0 2 10 50"
  rqrates="10"
  urates="0 1 5 25 45 50" # 2 * rate = total update %
  nrq=0
  prepare_exp "workloads" >>experiment_list.txt
  for rq in $rqrates; do
    for u in $urates; do
      for k in $ksizes; do
        for ds in $datastructures; do
          for alg in $rqtechniques; do
            nworks="0"
            if [ "$threadincrement" -ne "1" ]; then nworks="$nworks 1"; fi
            for ((x = $threadincrement; x < ${maxthreads}; x += $threadincrement)); do nworks="$nworks $x"; done
            if [ "$((${x} - ${threadincrement}))" -ne "${maxthreads}" ]; then nworks="$nworks $maxthreads"; fi
            for nwork in $nworks; do
              if [ ${nwork} -eq "0" ] && [ ${nrq} -eq "0" ]; then continue; fi
              check_ds_technique $ds $alg
              if [ "$?" -ne 0 ]; then continue; fi
              check_ds_size $ds $k
              if [ "$?" -ne 0 ]; then continue; fi
              if [ "$((u * 2 + rq))" -gt 100 ]; then continue; fi
              echo $u $rq $rqsize $k $nrq $nwork $ds $alg >>experiment_list.txt
              count=$((${count} + 1))
            done
          done
        done
      done
    done
  done
  echo "Generated ${count} trials."
}

run_rq_sizes() {
  echo "Preparing rq_sizes: THROUGHPUT WHILE VARYING RANGE QUERY SIZE"
  rqsizes="8 64 256 1024 8092 16184"
  urate=50
  count=0
  prepare_exp "rq_sizes" >>experiment_list.txt
  for rqsize in $rqsizes; do
    for k in $ksizes; do
      for ds in $datastructures; do
        for alg in $rqtechniques; do
          check_ds_technique $ds $alg
          if [ "$?" -ne 0 ]; then continue; fi
          check_ds_size $ds $k
          if [ "$?" -ne 0 ]; then continue; fi
          echo $urate 0 $rqsize $k 24 24 $ds $alg >>experiment_list.txt
          count=$(($count + 1))
        done
      done
    done
  done
  echo "Generated ${count} trials."

}

#< Indicates the plotting script should detect this line as an experiment to plot
run_workloads #<
run_rq_sizes #<

echo "Total experiment lines generated:" $(cat experiment_list.txt | wc -l)
