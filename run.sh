#!/bin/sh


# Usage: ./run.sh <start|stop|restart>
#
#
# Description: This script can be used to start or stop the galaxy
# web application.

cd "$(dirname "$0")"

. ./scripts/common_startup_functions.sh

# If there is a file that defines a shell environment specific to this
# instance of Galaxy, source the file.
if [ -z "$GALAXY_LOCAL_ENV_FILE" ];
then
    GALAXY_LOCAL_ENV_FILE='./config/local_env.sh'
fi

if [ -f "$GALAXY_LOCAL_ENV_FILE" ];
then
    . "$GALAXY_LOCAL_ENV_FILE"
fi

GALAXY_PID=${GALAXY_PID:-galaxy.pid}
GALAXY_LOG=${GALAXY_LOG:-galaxy.log}
PID_FILE=$GALAXY_PID
LOG_FILE=$GALAXY_LOG

parse_common_args $@

run_common_start_up

setup_python

if [ ! -z "$GALAXY_RUN_WITH_TEST_TOOLS" ];
then
    export GALAXY_CONFIG_OVERRIDE_TOOL_CONFIG_FILE="$(pwd)/test/functional/tools/samples_tool_conf.xml"
    export GALAXY_CONFIG_ENABLE_BETA_WORKFLOW_MODULES="true"
    export GALAXY_CONFIG_OVERRIDE_ENABLE_BETA_TOOL_FORMATS="true"
    export GALAXY_CONFIG_INTERACTIVETOOLS_ENABLE="true"
    export GALAXY_CONFIG_OVERRIDE_WEBHOOKS_DIR="test/functional/webhooks"
fi

set_galaxy_config_file_var

if [ "$INITIALIZE_TOOL_DEPENDENCIES" -eq 1 ]; then
    # Install Conda environment if needed.
    python ./scripts/manage_tool_dependencies.py init_if_needed
fi

find_server "${GALAXY_CONFIG_FILE:-none}" galaxy

echo "Executing: $run_server $server_args"
# args are properly quoted so use eval
eval GALAXY_ROOT_DIR="." $run_server $server_args
