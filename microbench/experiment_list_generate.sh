#!/bin/bash

source ../config.mk
rm -f experiment_list.txt >/dev/null

source ./supported.inc

# Overwrite datastructures and rqtechniques
datastructures="lazylist skiplistlock citrus"
rqtechniques="lockfree rwlock bundle"

ksizes="10000 100000 1000000"

echo "Preparing experiment 0: UPDATE/RQ ONLY WORKLOAD WITH VARYING RQ SIZES"
count=0
rqsizes="1 10 50 100 250 500"
urates="0 1 5 10 25 40 45 49 50"
nrq=0
for rqsize in $rqsizes; do
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
            rq=$((100 - (2 * ${u})))
            echo $u $rq $rqsize $k $nrq $nwork $ds $alg >>experiment_list.txt
            count=$((${count} + 1))
          done
        done
      done
    done
  done
done
echo "Generated ${count} trials for experiment 0."

echo "Preparing experiment 1: MIXED WORKLOAD (1:1 CONTAINS TO UPDATE RATIO) WITH RQ SIZE OF 100"
count=0
rqsize=100
nrq=0
erates="0 2 10 20 50 80 90 98 100"
for e in $erates; do
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
            rq=$((100 - ${e}))
            u=$(echo "scale=4;${e} / 2.0" | bc)
            u=$(echo "scale=4;${u} / 2.0" | bc) # Runscript uses same for inserts and deletes, so divide by two.
            echo $u $rq $rqsize $k $nrq $nwork $ds $alg >>experiment_list.txt
            count=$(( ${count} + 1 ))
          done
      done
    done
  done
done
echo "Generated ${count} trials for experiment 1."

echo "Preparing experiment 2: MIXED WORKLOAD (9:1 CONTAINS TO UPDATE RATIO) WITH RQ SIZE OF 100"
count=0
rqsize=100
nrq=0
erates="0 2 10 20 50 80 90 98 100"
for e in $erates; do
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
            rq=$((100 - ${e}))
            u=$(echo "scale=4;${e} / 10.0" | bc)
            u=$(echo "scale=4;${u} / 2.0" | bc) # Runscript uses same for inserts and deletes, so divide by two.
            echo $u $rq $rqsize $k $nrq $nwork $ds $alg >>experiment_list.txt
            count=$(( ${count} + 1 ))
          done
      done
    done
  done
done
echo "Generated ${count} trials for expeirment 2."

echo "Preparing experiment 3: MIXED WORKLOAD (1:9 CONTAINS TO UPDATE RATIO) WITH RQ SIZE OF 100"
count=0
rqsize=100
nrq=0
erates="0 2 10 20 50 80 90 98 100"
for e in $erates; do
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
            rq=$((100 - ${e}))
            u=$(echo "scale=4;9 * (${e} / 10.0)" | bc)
            u=$(echo "scale=4;${u} / 2.0" | bc) # Runscript uses same for inserts and deletes, so divide by two.
            echo $u $rq $rqsize $k $nrq $nwork $ds $alg >>experiment_list.txt
            count=$(( ${count} + 1 ))
          done
      done
    done
  done
done
echo "Generated ${count} trials for experiment 3."

echo "Preparing experiment 4: CONTAINS ONLY WORKLOAD WITH RQ SIZE OF 100"
count=0
rqsize=100
nrq=0
crates="0 2 10 20 50 80 90 98 100"
for c in $crates; do
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
            rq=$((100 - ${c}))
            echo 0 $rq $rqsize $k $nrq $nwork $ds $alg >>experiment_list.txt
            count=$(( ${count} + 1 ))
          done
      done
    done
  done
done
echo "Generated ${count} trials for experiment 4."

# echo "Preparing experiment 5: UPDATE/RQ ONLY WORKLOAD WITH VARYING RQ SIZES"
# count=0
# rqsizes="1 10 50 100 250 500"
# urates="0 1 5 10 25 40 45 49 50"
# nrq=0
# for rqsize in $rqsizes; do
#   for u in $urates; do
#     for k in $ksizes; do
#       for ds in $datastructures; do
#         for alg in $rqtechniques; do
#           for nrq in $nrqs;
#               do remaining_threads="$(expr $maxthreads - $nrq)"
#             nworks="0"
#             if [ "$threadincrement" -ne "1" ]; then nworks="$nworks 1"; fi
#             for ((x = $threadincrement; x < ${remaining_threads}; x += $threadincrement)); do nworks="$nworks $x"; done
#             if [ "$remaining_threads" -ne "0" ]; then nworks="$nworks $remaining_threads"; fi
#             for nwork in $nworks; do
#               if [ ${nwork} -eq "0" ] && [ ${nrq} -eq "0" ]; then continue; fi
#               check_ds_technique $ds $alg
#               if [ "$?" -ne 0 ]; then continue; fi
#               check_ds_size $ds $k
#               if [ "$?" -ne 0 ]; then continue; fi
#               rq=$((100 - (2 * ${u})))
#               echo $u $rq $rqsize $k $nrq $nwork $ds $alg >>experiment_list.txt
#               count=$(( ${count} + 1 ))
#             done
#           done
#         done
#       done
#     done
#   done
# done
# echo "Generated ${count} trials for experiment 5."

echo "Total experiment lines generated:" $(cat experiment_list.txt | wc -l)
