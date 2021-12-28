#! /bin/bash

if [[ $# -ne 3 ]]; then
  echo "Incorrect number of arguments (expected=3, actual=$#)."
  echo "Usage: $0 <datadir> <num_trials> <listname>."
  exit
fi

datadir=$1
ntrials=$2
listname=$3
# Each algorithm should be isolated in its own directory.
algos=$(ls ${datadir})
# echo $algos

cd ${datadir}
outfile=${listname}.csv

currfile=""
rqthrupt=0
uthrupt=0
totthrupt=0
ulat=0
clat=0
rqlat=0
rqthrupt=0
uthrupt=0
totthrupt=0
avgrqlen=0
avgannounce=0
avgbag=0
reachable=0
avgbundle=0
trialcount=0
samplecount=0
nobundlestats=0
restarts=0
avgretries=0
avgtraversals=0
echo "list,max_key,u_rate,rq_rate,wrk_threads,rq_threads,rq_size,u_latency,c_latency,rq_latency,tot_thruput,u_thruput,c_thruput,rq_thruput,rq_len,avg_in_announce,avg_in_bags,reachable_nodes,avg_bundle_size,tot_restarts,avg_retries,avg_traversals" >${outfile}
for algo in ${algos}; do
  files=$(ls ${algo} | grep ${listname})
  # echo $files
  for f in ${files}; do
    filename=${algo}/${f}
    # echo $filename
    # Only parse lines for given listname.
    if [[ "${listname}" != "" ]] && [[ "$(echo ${filename} | grep ${listname})" == "" ]]; then
      exit
    elif [[ "$(echo ${filename} | sed 's/.*[.]csv/.csv/')" == ".csv" ]]; then
      # Skip any generated .csv files.
      continue
    fi

    # Assumes trials are consecutive.
    rootname=$(echo ${filename} | sed -E 's/step[0-9]+[.]//' | sed -e 's/[.]trial.*//')
    if [[ ! "${rootname}" == "${currfile}" ]]; then
      trialcount=0
      samplecount=0
      currfile=${rootname}

      config=$(cat ${filename} | grep -B 10000 'BEGIN RUNNING')

      # Get name of list.
      list=$(echo ${filename} | sed -e "s/.*[.]${listname}[.]/${listname}-/" | sed -e 's/[.].*//')
      rqstrategy=$(echo "${list}" | sed -e "s/.*-//")

      # Get maximum key.
      maxkey=$(echo "${config}" | grep 'MAXKEY=' | sed -e 's/.*=//')

      nwrkthrds=$(echo "${config}" | grep 'WORK_THREADS=' | sed -e 's/.*=//')
      irate=$(echo "${config}" | grep 'INS=' | sed -e 's/.*=//')
      rrate=$(echo "${config}" | grep 'DEL=' | sed -e 's/.*=//')
      urate=$(echo "${irate} + ${rrate}" | bc)
      rqsize=$(echo "${config}" | grep 'RQSIZE=' | sed -e 's/.*=//')
      rqrate=$(echo "${config}" | grep 'RQ=' | sed -e 's/.*=//')
      rqthrds=$(echo "${config}" | grep 'RQ_THREADS=' | sed -e 's/.*=//')
    fi

    trialcount=$((trialcount + 1))
    filecontents=$(cat ${filename} | grep -A 10000 'END RUNNING')
    if [[ $(echo "${filecontents}" | grep -c 'end delete ds') != 1 ]]; then
      # Skip if not a completed run.
      continue
    fi

    # Latency statistics.
    ulat=$(($(echo "${filecontents}" | grep 'average latency_updates' | sed -e 's/.*=//') + ${ulat}))
    clat=$(($(echo "${filecontents}" | grep 'average latency_searches' | sed -e 's/.*=//') + ${clat}))
    rqlat=$(($(echo "${filecontents}" | grep 'average latency_rqs' | sed -e 's/.*=//') + ${rqlat}))

    # Throughput statistics.
    rqthrupt=$(($(echo "${filecontents}" | grep 'rq throughput' | sed -e 's/.*: //') + ${rqthrupt}))
    uthrupt=$(($(echo "${filecontents}" | grep 'update throughput' | sed -e 's/.*: //') + ${uthrupt}))
    totthrupt=$(($(echo "${filecontents}" | grep 'total throughput' | sed -e 's/.*: //') + ${totthrupt}))

    # Average range query length.
    avgrqlen=$(($(echo "${filecontents}" | grep 'average length_rqs' | sed -e 's/.*=//') + ${avgrqlen}))

    # EBR specific statistics.
    # if [[ "${nobundlestats}" == 0 ]] && ([[ "${rqstrategy}" == "lbundle" ]] || [[ "${rqstrategy}" == "cbundle" ]]); then
    # Bundle specific statistics.
    # reachable=$(($(echo "${filecontents}" | grep 'total reachable_nodes' | sed -e 's/.*: //') + ${reachable}))
    # if [[ ${reachable} != 0 ]]; then
    # avgbundle=$(echo "$(echo "${filecontents}" | grep 'average bundle_size' | sed -e 's/.*: //') + ${avgbundle}" | bc)
    # fi
    # else
    # if [[ "${avgbundle}" != "0" ]]; then
    #   exit 1
    # fi
    avgannounce=$(($(echo "${filecontents}" | grep 'average visited_in_announcements' | sed -e 's/.*=//') + ${avgannounce}))
    avgbag=$(($(echo "${filecontents}" | grep 'average visited_in_bags' | sed -e 's/.*=//') + ${avgbag}))
    # fi

    restarts=$(($(echo "${filecontents}" | grep 'sum bundle_restarts' | sed -e 's/.*=//') + ${restarts}))
    avgretries=$(($(echo "${filecontents}" | grep 'average bundle_retries' | sed -e 's/.*=//') + ${avgretries}))
    avgtraversals=$(($(echo "${filecontents}" | grep 'average bundle_traversals' | sed -e 's/.*=//') + ${avgtraversals}))

    samplecount=$((${samplecount} + 1))

    # Output previous averages.
    if [[ ${trialcount} == ${ntrials} ]]; then
      if [[ ${samplecount} != ${ntrials} ]]; then
        echo "Warning: unexpected number of samples (${samplecount}). Computing averages anyway: ${rootname}"
      elif [[ ${samplecount} == 0 ]]; then
        echo "Error: No samples collected: ${rootname}"
      else 
        printf "%s,%d,%.2f,%.2f,%d,%d,%d" ${list} ${maxkey} ${urate} ${rqrate} ${nwrkthrds} ${rqthrds} ${rqsize} >>${outfile}
        printf ",%d" $((${ulat} / ${samplecount})) >>${outfile}
        printf ",%d" $((${clat} / ${samplecount})) >>${outfile}
        printf ",%d" $((${rqlat} / ${samplecount})) >>${outfile}
        printf ",%d" $((${totthrupt} / ${samplecount})) >>${outfile}
        printf ",%d" $((${uthrupt} / ${samplecount})) >>${outfile}
        printf ",%d" $((${totthrupt} - (${uthrupt} + ${rqthrupt}))) >>${outfile}
        printf ",%d" $((${rqthrupt} / ${samplecount})) >>${outfile}
        printf ",%d" $((${avgrqlen} / ${samplecount})) >>${outfile}
        printf ",%d" $((${avgannounce} / ${samplecount})) >>${outfile}
        printf ",%d" $((${avgbag} / ${samplecount})) >>${outfile}
        printf ",%d" $((${reachable} / ${samplecount})) >>${outfile}
        printf ",%.2f" $(echo "scale=4;$(echo ${avgbundle}) / ${samplecount}.0" | bc) >>${outfile}
        printf ",%d" $((${restarts} / ${samplecount})) >>${outfile}
        printf ",%d" $((${avgretries} / ${samplecount})) >>${outfile}
        printf ",%d" $((${avgtraversals} / ${samplecount})) >>${outfile}
        printf "\n" >>${outfile}
      fi

      ulat=0
      clat=0
      rqlat=0
      rqthrupt=0
      uthrupt=0
      totthrupt=0
      avgrqlen=0
      avgannounce=0
      avgbag=0
      reachable=0
      avgbundle=0
      restarts=0
      avgretries=0
      avgtraversals=0
    fi
  done
done
