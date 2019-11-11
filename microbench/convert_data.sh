#! /bin/bash

if [[ $# -ne 2 ]]; then
  echo "Incorrect number of arguments (expected=1, actual=$#)."
  echo "Usage: $0 <datadir> <num_trials>."
  exit
fi

datadir=$1
files=$(ls ${datadir})
cd ${datadir}

ntrials=$2
currfile=""

rqthrupt=0
uthrupt=0
totthrupt=0
for filename in ${files}; do

  rootname=$(echo ${filename} | sed -E 's/step[0-9]+[.]//' | sed -e 's/[.]trial.*//')
  if [[ ! "${rootname}" == "${currfile}" ]]; then

    # Output previous averages.
    if [[ ! -z "${currfile}" ]]; then
      rqthrupt=$((${rqthrupt} / ${ntrials}))
      uthrupt=$((${uthrupt} / ${ntrials}))
      totthrupt=$((${totthrupt} / ${ntrials}))
      echo "${list},${size},${urate},${maxrqs},${rqthrds},${rqrate},${nwrkthrds},${rqthrupt},${uthrupt},${totthrupt}"
      rqthrupt=0
      uthrupt=0
      totthrupt=0
    else
      echo "list,size,update_rate,max_rqs,rq_threads,rq_rate,num_wrk_threads,#rq txs,#update txs,#txs"
    fi
    
    if [[ ${filename} == "summary.txt" ]]; then
      continue
    fi

    currfile=${rootname}

    # Extract the values to organize for consumption by plotting script.
    list=$(echo ${filename} | sed -e 's/.*[.]lazylist[.]//' | sed -e 's/[.].*//')

    size=$(cat ${filename} | grep 'MAXKEY=' | sed -e 's/.*=//')
    size=$((${size} / 2))

    irate=$(cat ${filename} | grep 'INS=' | sed -e 's/.*=//')
    rrate=$(cat ${filename} | grep 'DEL=' | sed -e 's/.*=//')
    urate=$((${irate} + ${rrate}))

    maxrqs=-1 # The maximum allowable RQs does not apply.

    rqthrds=$(cat ${filename} | grep 'RQ_THREADS=' | sed -e 's/.*=//')

    rqrate=$(cat ${filename} | grep 'RQ=' | sed -e 's/.*=//')
    if [[ ${rqrate} == '0' ]] && [[ ${rqthrds} -gt 0 ]]; then
      rqrate=100
    fi

    nwrkthrds=$(cat ${filename} | grep 'WORK_THREADS=' | sed -e 's/.*=//')
  fi
  # Accumulate throughputs.
  rqthrupt=$(($(cat ${filename} | grep 'rq throughput' | sed -e 's/.*: //') + ${rqthrupt}))
  uthrupt=$(($(cat ${filename} | grep 'update throughput' | sed -e 's/.*: //') + ${uthrupt}))
  totthrupt=$(($(cat ${filename} | grep 'total throughput' | sed -e 's/.*: //') + ${totthrupt}))
done
