#!/bin/sh

cd "$(dirname "$0")"/../..
python ./scripts/cleanup_datasets/populate_uuid.py ./config/galaxy.ini "$@"
