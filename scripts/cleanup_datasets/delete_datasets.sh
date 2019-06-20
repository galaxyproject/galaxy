#!/bin/sh

cd "$(dirname "$0")"/../..
python ./scripts/cleanup_datasets/cleanup_datasets.py -d 10 -6 -r "$@" >> ./scripts/cleanup_datasets/delete_datasets.log
