#!/bin/bash
set -e
MAX_LINE_COUNT=19900
project_dir=`dirname $0`/..
cd $project_dir
bash -c "[ `find lib/galaxy/webapps/galaxy/controllers/ -name '*.py' | xargs wc -l | tail -n 1 | awk '{ printf \$1; }'` -lt $MAX_LINE_COUNT ]"
