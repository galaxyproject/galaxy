#!/bin/sh

cd `dirname $0`/../..
python ./scripts/cleanup_datasets/cleanup_datasets.py ./config/galaxy.ini -d 10 -4 -r $@ >> ./scripts/cleanup_datasets/purge_libraries.log
