#!/usr/bin/env bash

# This file is sourced in the maintenance.sh script and could be sourced in ./run.sh or ./run_reports.sh
SCRIPTLOCATION="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# If there is a file that defines a shell environment specific to this
# instance of Galaxy, source the file.
if [ -z $GALAXY_LOCAL_ENV_FILE ];
then
  GALAXY_LOCAL_ENV_FILE="$SCRIPTLOCATION/../config/local_env.sh"
fi

if [ -f $GALAXY_LOCAL_ENV_FILE ];
then
  echo "Activating local env file: $GALAXY_LOCAL_ENV_FILE"
  . $GALAXY_LOCAL_ENV_FILE
fi

# If there is a .venv/ directory, assume it contains a virtualenv that we
# should run this instance in.
GALAXY_VIRTUAL_ENV="${GALAXY_VIRTUAL_ENV:-$SCRIPTLOCATION/../.venv}"
if [ -d "$GALAXY_VIRTUAL_ENV" -a -z "$skip_venv" ];
then
  [ -n "$PYTHONPATH" ] && { echo 'Unsetting $PYTHONPATH'; unset PYTHONPATH; }
  echo "Activating virtualenv at $GALAXY_VIRTUAL_ENV"
  . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi
if [ -z "$GALAXY_CONFIG_FILE" ]; then
  if [ -f "$SCRIPTLOCATION/../universe_wsgi.ini" ]; then
    GALAXY_CONFIG_FILE=universe_wsgi.ini
  elif [ -f "$SCRIPTLOCATION/../config/galaxy.ini" ]; then
    GALAXY_CONFIG_FILE=config/galaxy.ini
  else
    GALAXY_CONFIG_FILE=config/galaxy.ini.sample
  fi
  export GALAXY_CONFIG_FILE
fi

echo "GALAXY_CONFIG_FILE: ${GALAXY_CONFIG_FILE}"
