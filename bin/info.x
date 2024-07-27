#!/bin/bash

running_jobs=$(squeue -o "%i %D" --noheader --states=RUNNING | awk '{print "{\"slurm_job_id\": \""$1"\", \"num_nodes\": "$2"}"}' | jq -s '.')

pending_jobs=$(squeue -o "%i %D" --noheader --states=PENDING | awk '{print "{\"slurm_job_id\": \""$1"\", \"num_nodes\": "$2"}"}' | jq -s '.')

num_finished_jobs=$(sacct --noheader -a --starttime=$(date -d "24 hours ago" '+%Y-%m-%dT%H:%M:%S') --endtime=$(date '+%Y-%m-%dT%H:%M:%S') --state=CD | wc -l)

num_nodes_total=$(sinfo -O Nodes | sed -n '2p')

output=$(sinfo -h -o "%T %D")
num_nodes_allocated=$(echo "$output" | awk '$1 == "allocated" {print $2}')
num_nodes_idle=$(echo "$output" | awk '$1 == "idle" {print $2}')

echo '{}' | jq ".num_nodes_total = $num_nodes_total" | jq ".num_nodes_allocated = $num_nodes_allocated" | jq ".num_nodes_idle = $num_nodes_idle" | jq ".running_jobs = $running_jobs" | jq ".pending_jobs = $pending_jobs" | jq ".num_finished_jobs = $num_finished_jobs"

