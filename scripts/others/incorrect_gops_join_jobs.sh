#!/bin/sh

cd `dirname $0`/../..
python ./scripts/others/incorrect_gops_join_jobs.py ./universe_wsgi.ini >> ./scripts/others/incorrect_gops_join_jobs.log
