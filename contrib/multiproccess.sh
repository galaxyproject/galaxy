#!/bin/bash

# copy this script to the top level galaxy directory and modify the following
# for your environment

web_server_names=(web{0..2}) # server names: web0 web1 web2
runner_server_names=(runner0) # server name: runner0

web_config='universe_wsgi.webapp.ini'
runner_config='universe_wsgi.runner.ini'

# actually do the requested action

if [ -z "$1" ]; then
    echo "usage: multiprocess.sh <--daemon|--stop-daemon>"
    exit 1
fi

for server_name in ${web_server_names[@]}; do
    echo "[$server_name]"
    python ./scripts/paster.py serve $web_config --server-name=$server_name --pid-file=$server_name.pid --log-file=$server_name.log $@
done
for server_name in ${runner_server_names[@]}; do
    echo "[$server_name]"
    python ./scripts/paster.py serve $runner_config --server-name=$server_name --pid-file=$server_name.pid --log-file=$server_name.log $@
done
