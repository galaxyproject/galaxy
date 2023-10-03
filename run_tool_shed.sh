#!/bin/sh

cd "$(dirname "$0")"


export GALAXY_SKIP_CLIENT_BUILD=1
TOOL_SHED_PID=${TOOL_SHED_PID:-tool_shed_webapp.pid}
TOOL_SHED_LOG=${TOOL_SHED_LOG:-tool_shed_webapp.log}
PID_FILE=$TOOL_SHED_PID
LOG_FILE=$TOOL_SHED_LOG

. ./scripts/common_startup_functions.sh

parse_common_args $@

run_common_start_up

setup_python

if [ -z "$TOOL_SHED_CONFIG_FILE" ]; then
    TOOL_SHED_CONFIG_FILE=$(PYTHONPATH=lib python -c "from __future__ import print_function; from galaxy.util.properties import find_config_file; print(find_config_file(['tool_shed', 'tool_shed_wsgi'], include_samples=True) or '')")
    export TOOL_SHED_CONFIG_FILE
fi

find_server ${TOOL_SHED_CONFIG_FILE:-none} tool_shed
echo "Executing: $run_server $server_args"
eval $run_server $server_args
