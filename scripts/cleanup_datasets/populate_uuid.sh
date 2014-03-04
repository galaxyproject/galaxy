#!/bin/sh

cd `dirname $0`/../..
export PYTHONPATH=./lib/
python ./scripts/cleanup_datasets/populate_uuid.py ./universe_wsgi.ini $@