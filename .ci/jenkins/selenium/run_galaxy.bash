#!/bin/bash

set -e

sleep 30  # TODO: wait on something instead of just sleeping...

echo `df`

echo "Creating postgres database for Galaxy"
createdb -w -U postgres -h postgres galaxy

echo "Starting and waiting for Galaxy daemon(s)"
GALAXY_RUN_ALL=1 bash "$GALAXY_ROOT/run.sh" --daemon --wait

echo "Galaxy daemon ready, monitoring Galaxy logs"
tail -f "$GALAXY_ROOT/main.log"
