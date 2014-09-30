#!/bin/sh

cd `dirname $0`/../..
python ./scripts/others/incorrect_gops_join_jobs.py ./config/galaxy.ini >> ./scripts/others/incorrect_gops_join_jobs.log
