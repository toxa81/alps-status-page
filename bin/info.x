#!/bin/bash

running_jobs=$(squeue -o "%i %D" --noheader --states=RUNNING | awk '{print "{\"slurm_job_id\": \""$1"\", \"num_nodes\": "$2"}"}' | jq -s '.')

pending_jobs=$(squeue -o "%i %D" --noheader --states=PENDING | awk '{print "{\"slurm_job_id\": \""$1"\", \"num_nodes\": "$2"}"}' | jq -s '.')

finished_job_times=$(sacct -X --noheader -a --starttime=$(date -d "24 hours ago" '+%Y-%m-%dT%H:%M:%S') --endtime=$(date '+%Y-%m-%dT%H:%M:%S') --state=CD --format=TimelimitRaw,ElapsedRaw | awk '{print "["$1*60", "$2"]"}' | jq -s '.')

num_finished_jobs=$(echo "$finished_job_times" | jq '. | length')

num_nodes_gross=$(sinfo --noheader -O Nodes)

output=$(sinfo -h -o "%T %D" -p normal)

#num_nodes_allocated=$(echo "$output" | awk '$1 == "allocated" {print $2; found=1} END {if (!found) print 0}')
#echo "Number of allocated nodes: $num_nodes_allocated"

num_nodes_total=$(sinfo -h -o "%D" -p normal)

#num_nodes_idle=$(echo "$output" | awk '$1 == "idle" {print $2; found=1} END {if (!found) print 0}')
num_nodes_idle=$(sinfo -h -o "%D" -p normal -t idle)
if [ -z "$num_nodes_idle" ]; then
  num_nodes_idle=0
fi

num_nodes_allocated=$(sinfo -h -o "%D" -p normal -t allocated)
if [ -z "$num_nodes_allocated" ]; then
  num_nodes_allocated=0
fi

json=$(echo '{}' | \
    jq ".num_nodes_gross = $num_nodes_gross" | \
    jq ".num_nodes_total = $num_nodes_total" | \
    jq ".num_nodes_allocated = $num_nodes_allocated" | \
    jq ".num_nodes_idle = $num_nodes_idle" | \
    jq ".running_jobs = $running_jobs" | \
    jq ".pending_jobs = $pending_jobs" | \
    jq ".num_finished_jobs = $num_finished_jobs" | \
    jq ".finished_job_times = $finished_job_times")

curl -X 'PUT' "http://148.187.151.141:8000/status/$CLUSTER_NAME" \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d "$json" \
     --connect-timeout 5 > /dev/null


