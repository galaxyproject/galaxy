#!/bin/bash
set -e
MAX_MAKO_COUNT=330
project_dir=`dirname $0`/..
cd $project_dir
bash -c "[ `find templates -iname '*.mako'  | wc -l | cut -f1 -d' '` -lt $MAX_MAKO_COUNT ]"
