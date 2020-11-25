#!/bin/bash
#
# Run script for the macro benchmark (TPC-C benchmarks)
#
# Author: Trevor Brown
#
# Created on Jul 18, 2017, 10:56:28 PM
#

source ../config.mk
source ../microbench/supported.inc

ntrials=5
machine=$(hostname)

outpath=./data/rq_tpcc
fsummary=$outpath/summary.txt

if [[ -e "${outpath}" ]] && [[ ! $(mv "${outpath}" "${outpath}.old") ]]; then
  echo "Would you like to forcefully overwrite the existing version? (Y/n)"
  read answer
  while [[ "$(echo ${answer} | grep "^[yYnN]$")" == "" ]]; do
    echo "(Y/n)"
    read answer
  done

  if [[ "${answer}" == "Y" ]] || [[ "${answer}" == "y" ]]; then
    mv -f $outpath $outpath.old
    rm -rf $outpath
  else
    exit 0
  fi
fi
mkdir -p $outpath

cnt1=10000
cnt2=10000

## fix any \r line endings, which mess up the DBMS schema in TPC-C
dos2unix benchmarks/*.txt

for counting in 1 0; do
  if (($counting == 0)); then
    echo "Total trials: $cnt1 ... $cnt2"
  fi

  for exepath in $(ls ./bin/$machine/rundb*); do
    if [ "${htm_error}" -ne "0" ]; then
      if [[ $exepath == *"HTM"* ]]; then continue; fi
    fi

    nthreads="1"
    for ((x = $threadincrement; x < ${maxthreads}; x += $threadincrement)); do nthreads="$nthreads $x"; done
    nthreads="$nthreads $maxthreads"
    for n in $nthreads; do
      for ((trial = 0; trial < $ntrials; ++trial)); do
        if (($counting == 1)); then
          cnt2=$(expr $cnt2 + 1)
          if ((($cnt2 % 100) == 0)); then echo "Counting trials: $cnt2"; fi
        else
          cnt1=$(expr $cnt1 + 1)
          exeonly=$(echo $exepath | cut -d"/" -f4)
          fname=$outpath/step$cnt1.trial$trial.$exeonly.txt
          workload=$(echo $exeonly | cut -d"_" -f2 | cut -d"." -f1)
          datastructure=$(echo $exeonly | cut -d"_" -f3 | cut -d"." -f1)
          rqalg=$(echo $exeonly | cut -d"_" -f4- | cut -d"." -f1)

          #echo "RUNNING step $cnt1 / $cnt2 : trial $trial of $exeonly > $fname"

          echo -n "step=$cnt1, trial=$trial, workload=$workload, datastructure=$datastructure, rqalg=$rqalg," >>$fsummary

          args="-t$n -n$n"
          cmd="env LD_PRELOAD=../lib/libjemalloc.so TREE_MALLOC=../lib/libjemalloc.so $exepath $args"
          echo $fname >$fname
          echo $cmd >>$fname
          $cmd >>$fname
          cat $fname | grep "summary" | cut -d"]" -f2- >>$fsummary
          tail -1 $fsummary
        fi
      done
    done
  done
done

./makecsv.sh
