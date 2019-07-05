#!/bin/sh

cd `dirname $0`

. ./scripts/common_startup_functions.sh

setup_python

for file in $1/split_info*.json
do
    # echo processing $file
    python ./scripts/extract_dataset_part.py $file
done
