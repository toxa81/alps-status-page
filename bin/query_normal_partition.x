#!/bin/bash

states=(
  unknown down idle allocated '?' mixed future drain drained draining no_respond reserved perfctrs cloud completing powering_down powered_down power_down powering_up fail maint reboot reboot^ unknown
)
for state in "${states[@]}"; do
  value=$(sinfo -h -o "%D" -p normal -t "$state")
  if [ -z "$value" ]; then
    value=0
  fi
  echo "Number of nodes in state $state: $value"
done

num_nodes_total=$(sinfo -h -o "%D" -p normal)
if [ -z "$num_nodes_total" ]; then
  num_nodes_total=0
fi
echo "Total number of nodes: $num_nodes_total"
