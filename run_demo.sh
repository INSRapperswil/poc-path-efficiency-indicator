#!/bin/bash

timestamp=$(date +'%Y%m%d%H%M%S')
log_dir="logs/demo/${timestamp}"
cases_file="dev-network/demo/cases.json"
mkdir -p "${log_dir}"
sudo python3 dev-network/utils/run_test_sender.py -t dev-network/topology.json -j build/main.json -b simple_switch_grpc --quiet --demo --log-dir "${log_dir}" --testcases "${cases_file}"
