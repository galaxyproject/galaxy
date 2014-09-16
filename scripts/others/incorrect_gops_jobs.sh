#!/bin/sh

cd `dirname $0`/../..
python ./scripts/others/incorrect_gops_jobs.py ./config/galaxy.ini >> ./scripts/others/incorrect_gops_jobs.log
