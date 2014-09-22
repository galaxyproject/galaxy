#!/bin/sh

cd `dirname $0`/../..
python ./scripts/data_libraries/build_whoosh_index.py ./config/galaxy.ini
