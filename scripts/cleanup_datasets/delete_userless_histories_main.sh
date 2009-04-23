#!/bin/sh

cd `dirname $0`/../..
python ./scripts/cleanup_datasets/cleanup_datasets.py ./universe_wsgi.ini -d 60 -1 $@ >> ./scripts/cleanup_datasets/delete_userless_histories.log
