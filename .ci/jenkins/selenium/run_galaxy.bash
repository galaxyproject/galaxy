#!/bin/bash

set -e

sleep 10  # TODO: wait on something instead of just sleeping...

echo `df`

createdb -w -U postgres -h postgres galaxy
GALAXY_RUN_ALL=1 bash "$GALAXY_ROOT/run.sh" --daemon --wait

tail -f "$GALAXY_ROOT/main.log"
