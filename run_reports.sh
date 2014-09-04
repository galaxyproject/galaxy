#!/bin/sh


# Usage: ./run_reports.sh [--sync-config] <start|stop>
#
#
# Description: This script can be used to start or stop the galaxy
# reports web application. Passing in --sync-config as the first
# argument to this will cause Galaxy's database and path parameters
# from universe_wsgi.ini to be copied over into reports_wsgi.ini.

cd `dirname $0`

# If there is a .venv/ directory, assume it contains a virtualenv that we
# should run this instance in.
if [ -d .venv ];
then
    . .venv/bin/activate
fi

./scripts/common_startup.sh --skip-samples

GALAXY_REPORTS_CONFIG=${GALAXY_REPORTS_CONFIG:-reports_wsgi.ini}
GALAXY_REPORTS_PID=${GALAXY_REPORTS_PID:-reports_webapp.pid}
GALAXY_REPORTS_LOG=${GALAXY_REPORTS_LOG:-reports_webapp.log}

if [ -n "$GALAXY_REPORTS_CONFIG_DIR" ]; then
    python ./scripts/build_universe_config.py "$GALAXY_REPORTS_CONFIG_DIR" "$GALAXY_REPORTS_CONFIG"
fi


if [ "$1" = "--sync-config" ];
then
    python ./scripts/sync_reports_config.py
    shift
fi

python ./scripts/paster.py serve "$GALAXY_REPORTS_CONFIG" --pid-file="$GALAXY_REPORTS_PID" --log-file="$GALAXY_REPORTS_LOG" $@
