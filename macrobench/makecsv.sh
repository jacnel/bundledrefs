#!/bin/bash

colStr=$(cat data/rq_tpcc/summary.txt | tail -1 | tr "," "\n" | tr -d " " | cut -d"=" -f1 | tr "\n" ",")
remove="step trial time_wait time_ts_alloc time_man time_index time_abort time_cleanup latency deadlock_cnt cycle_detect dl_detect_time dl_wait_time time_query debug1 debug2 debug3 debug4 debug5 throughput node_size descriptor_size"
for r in $remove; do
  colStr=$(echo $colStr | sed "s/$r,//")
done

ntrials=5
n=0
outfile="data.csv"
echo $colStr | sed 's/,$//' >${outfile}

file="data/rq_tpcc/summary.txt"
if [[ $# == 1 ]]; then
  file=$1
fi

cat $file | grep "datastructure" | while read line; do
  if [[ $n == $(($ntrials + 1)) ]] || [[ $n == 0 ]]; then
    # Initialize values.
    txn_cnt=0
    abort_cnt=0
    run_time=0
    ixNumContains=0
    ixTimeContains=0
    ixNumInsert=0
    ixTimeInsert=0
    ixNumRemove=0
    ixTimeRemove=0
    ixNumRangeQuery=0
    ixTimeRangeQuery=0
    ixLenRangeQuery=0
    ixTotalOps=0
    ixTotalTime=0
    ixThroughput=0
    n=1

    # Print common values.
    workload=$(echo $line | sed 's/.*workload=//' | sed 's/,.*//')
    datastructure=$(echo $line | sed 's/.*datastructure=//' | sed 's/,.*//')
    rqalg=$(echo $line | sed 's/.*rqalg=//' | sed 's/,.*//')
    echo -n "$workload,$datastructure,$rqalg," >>${outfile}
  fi

  txn_cnt=$(echo "$(echo $line | sed 's/.*txn_cnt=//' | sed 's/,.*//') + $txn_cnt" | bc)
  abort_cnt=$(echo "$(echo $line | sed 's/.*abort_cnt=//' | sed 's/,.*//') + $abort_cnt" | bc)
  run_time=$(echo "$(echo $line | sed 's/.*run_time=//' | sed 's/,.*//') + $run_time" | bc)
  ixNumContains=$(echo "$(echo $line | sed 's/.*ixNumContains=//' | sed 's/,.*//') + $ixNumContains" | bc)
  ixTimeContains=$(echo "$(echo $line | sed 's/.*ixTimeContains=//' | sed 's/,.*//') + $ixTimeContains" | bc)
  ixNumInsert=$(echo "$(echo $line | sed 's/.*ixNumInsert=//' | sed 's/,.*//') + $ixNumInsert" | bc)
  ixTimeInsert=$(echo "$(echo $line | sed 's/.*ixTimeInsert=//' | sed 's/,.*//') + $ixTimeInsert" | bc)
  ixNumRemove=$(echo "$(echo $line | sed 's/.*ixNumRemove=//' | sed 's/,.*//') + $ixNumRemove" | bc)
  ixTimeRemove=$(echo "$(echo $line | sed 's/.*ixTimeRemove=//' | sed 's/,.*//') + $ixTimeRemove" | bc)
  ixNumRangeQuery=$(echo "$(echo $line | sed 's/.*ixNumRangeQuery=//' | sed 's/,.*//') + $ixNumRangeQuery" | bc)
  ixTimeRangeQuery=$(echo "$(echo $line | sed 's/.*ixTimeRangeQuery=//' | sed 's/,.*//') + $ixTimeRangeQuery" | bc)
  ixLenRangeQuery=$(echo "$(echo $line | sed 's/.*ixLenRangeQuery=//' | sed 's/,.*//') + $ixLenRangeQuery" | bc)
  ixTotalOps=$(echo "$(echo $line | sed 's/.*ixTotalOps=//' | sed 's/,.*//') + $ixTotalOps" | bc)
  ixTotalTime=$(echo "$(echo $line | sed 's/.*ixTotalTime=//' | sed 's/,.*//') + $ixTotalTime" | bc)
  ixThroughput=$(echo "$(echo $line | sed 's/.*ixThroughput=//' | sed 's/,.*//') + $ixThroughput" | bc)

  if [[ $n == $ntrials ]]; then
    txn_cnt=$(echo "scale=4;$txn_cnt / $ntrials" | bc)
    abort_cnt=$(echo "scale=4;$abort_cnt / $ntrials" | bc)
    run_time=$(echo "scale=4;$run_time / $ntrials" | bc)
    ixNumContains=$(echo "scale=4;$ixNumContains / $ntrials" | bc)
    ixTimeContains=$(echo "scale=4;$ixTimeContains / $ntrials" | bc)
    ixNumInsert=$(echo "scale=4;$ixNumInsert / $ntrials" | bc)
    ixTimeInsert=$(echo "scale=4;$ixTimeInsert / $ntrials" | bc)
    ixNumRemove=$(echo "scale=4;$ixNumRemove / $ntrials" | bc)
    ixTimeRemove=$(echo "scale=4;$ixTimeRemove / $ntrials" | bc)
    ixNumRangeQuery=$(echo "scale=4;$ixNumRangeQuery / $ntrials" | bc)
    ixTimeRangeQuery=$(echo "scale=4;$ixTimeRangeQuery / $ntrials" | bc)
    ixLenRangeQuery=$(echo "scale=4;$ixLenRangeQuery / $ntrials" | bc)
    ixTotalOps=$(echo "scale=4;$ixTotalOps / $ntrials" | bc)
    ixTotalTime=$(echo "scale=4;$ixTotalTime / $ntrials" | bc)
    ixThroughput=$(echo "scale=4;$ixThroughput / $ntrials" | bc)

    # More common values.
    nthreads=$(echo $line | sed 's/.*nthreads=//' | sed 's/,.*//')

    echo "$txn_cnt,$abort_cnt,$run_time,$ixNumContains,$ixTimeContains,$ixNumInsert,$ixTimeInsert,$ixNumRemove,$ixTimeRemove,$ixNumRangeQuery,$ixTimeRangeQuery,$ixLenRangeQuery,$ixTotalOps,$ixTotalTime,$ixThroughput,$nthreads" >>${outfile}
  fi
  n=$(($n + 1))

done
