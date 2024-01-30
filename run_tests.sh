#!/bin/bash

timestamp=$(date +'%Y%m%d%H%M%S')
log_dir="logs/testing/${timestamp}"
cases_file="dev-network/test/cases.json"
mkdir -p "${log_dir}"
sudo python3 dev-network/utils/run_test_sender.py -t dev-network/topology.json -j build/main.json -b simple_switch_grpc --quiet --test --log-dir "${log_dir}" > "${log_dir}/runtime_configurations.log"  --testcases ${cases_file} &
watch -n 1 "grep -r -E 'TEST (FAILED|PASSED|RUN)' "${log_dir}" | awk -F 'log:' '{print \$2}' | sort"
