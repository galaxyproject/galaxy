#!/bin/sh

cd `dirname $0`/../..
python ./scripts/cleanup_datasets/cleanup_datasets.py ./config/galaxy.ini -d 10 -1 $@ >> ./scripts/cleanup_datasets/delete_userless_histories.log
