#!/bin/sh

cd "$(dirname "$0")"


export GALAXY_SKIP_CLIENT_BUILD=1
TOOL_SHED_PID=${TOOL_SHED_PID:-tool_shed_webapp.pid}
TOOL_SHED_LOG=${TOOL_SHED_LOG:-tool_shed_webapp.log}
PID_FILE=$TOOL_SHED_PID
LOG_FILE=$TOOL_SHED_LOG

. ./scripts/common_startup_functions.sh

parse_common_args $@

# Conditional dependencies come from tool_shed.yml here, not galaxy.yml
export GALAXY_CONDITIONAL_DEPENDENCIES_APP=tool_shed

run_common_start_up

setup_python

set_tool_shed_config_file_var

find_server ${TOOL_SHED_CONFIG_FILE:-none} tool_shed
echo "Executing: $run_server $server_args"
eval $run_server $server_args
