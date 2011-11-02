#!/bin/sh

cd `dirname $0`
for file in $1/split_info*.json
do
    # echo processing $file
    python ./scripts/extract_dataset_part.py $file
done
