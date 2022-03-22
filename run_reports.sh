#!/bin/sh


# Usage: ./run_reports.sh [--sync-config] <start|stop>
#
#
# Description: This script can be used to start or stop the galaxy
# reports web application. Passing in --sync-config as the first
# argument to this will cause Galaxy's database and path parameters
# from galaxy.ini to be copied over into reports.ini.

cd "$(dirname "$0")"

GALAXY_REPORTS_PID=${GALAXY_REPORTS_PID:-reports_webapp.pid}
GALAXY_REPORTS_LOG=${GALAXY_REPORTS_LOG:-reports_webapp.log}
PID_FILE=$GALAXY_REPORTS_PID
LOG_FILE=$GALAXY_REPORTS_LOG

. ./scripts/common_startup_functions.sh

if [ "$1" = "--sync-config" ];
then
    python ./scripts/sync_reports_config.py
    shift
fi

parse_common_args $@

run_common_start_up

setup_python

if [ -z "$GALAXY_REPORTS_CONFIG" ]; then
    GALAXY_REPORTS_CONFIG=$(PYTHONPATH=lib python -c "from __future__ import print_function; from galaxy.util.properties import find_config_file; print(find_config_file(['reports', 'reports_wsgi']) or '')")
    export GALAXY_REPORTS_CONFIG
fi

find_server ${GALAXY_REPORTS_CONFIG:-none} reports

if [ "$run_server" = "gunicorn" -a -z "$GALAXY_REPORTS_CONFIG" ]; then
    GALAXY_REPORTS_CONFIG="config/reports.yml.sample"
    export GALAXY_REPORTS_CONFIG
    echo 'WARNING: Using default reports config at config/reports.yml.sample, copy to config/reports.yml or set $GALAXY_REPORTS_CONFIG if this is not intentional'
fi

echo "Executing: $run_server $server_args"
eval $run_server $server_args
