#!/bin/sh

cd `dirname $0`

GALAXY_RUN_ALL=1 ./run.sh restart --wait
