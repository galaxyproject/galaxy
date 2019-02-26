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
    export GALAXY_CONFIG_OVERRIDE_TOOL_CONFIG_FILE="test/functional/tools/samples_tool_conf.xml"
    export GALAXY_CONFIG_ENABLE_BETA_WORKFLOW_MODULES="true"
    export GALAXY_CONFIG_ENABLE_BETA_WORKFLOW_FORMAT="true"
    export GALAXY_CONFIG_OVERRIDE_ENABLE_BETA_TOOL_FORMATS="true"
    export GALAXY_CONFIG_OVERRIDE_WEBHOOKS_DIR="test/functional/webhooks"
fi

if [ -n "$GALAXY_UNIVERSE_CONFIG_DIR" ]; then
    python ./scripts/build_universe_config.py "$GALAXY_UNIVERSE_CONFIG_DIR"
fi

set_galaxy_config_file_var

if [ "$INITIALIZE_TOOL_DEPENDENCIES" -eq 1 ]; then
    # Install Conda environment if needed.
    python ./scripts/manage_tool_dependencies.py init_if_needed
fi

[ -n "$GALAXY_UWSGI" ] && APP_WEBSERVER='uwsgi'
find_server "${GALAXY_CONFIG_FILE:-none}" galaxy

if [ "$run_server" = "python" -a -n "$GALAXY_RUN_ALL" ]; then
    servers=$(sed -n 's/^\[server:\(.*\)\]/\1/  p' "$GALAXY_CONFIG_FILE" | xargs echo)
    if [ -z "$stop_daemon_arg_set" -a -z "$daemon_or_restart_arg_set" ]; then
        echo "ERROR: \$GALAXY_RUN_ALL cannot be used without the '--daemon', '--stop-daemon', 'restart', 'start' or 'stop' arguments to run.sh"
        exit 1
    fi
    for server in $servers; do
        echo "Executing: python $server_args --server-name=\"$server\" --pid-file=\"$server.pid\" --log-file=\"$server.log\""
        eval python $server_args --server-name="$server" --pid-file="$server.pid" --log-file="$server.log"
        if [ -n "$wait_arg_set" -a -n "$daemon_or_restart_arg_set" ]; then
            while true; do
                sleep 1
                # Grab the current pid from the pid file and remove any trailing space
                if ! current_pid_in_file=$(sed -e 's/[[:space:]]*$//' "$server.pid"); then
                    echo "A Galaxy process died, interrupting" >&2
                    exit 1
                fi
                if [ -n "$current_pid_in_file" ]; then
                    echo "Found PID $current_pid_in_file in '$server.pid', monitoring '$server.log'"
                else
                    echo "No PID found in '$server.pid' yet"
                    continue
                fi
                # Search for all pids in the logs and tail for the last one
                latest_pid=$(grep '^Starting server in PID [0-9]\+\.$' "$server.log" | sed 's/^Starting server in PID \([0-9]\+\).$/\1/' | tail -n 1)
                # If they're equivalent, then the current pid file agrees with our logs
                # and we've succesfully started
                [ -n "$latest_pid" ] && [ "$latest_pid" -eq "$current_pid_in_file" ] && break
            done
            echo
        fi
    done
else
    echo "Executing: $run_server $server_args"
    # args are properly quoted so use eval
    eval $run_server $server_args
fi
