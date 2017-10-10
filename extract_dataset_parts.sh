#!/bin/sh

cd `dirname $0`
: ${GALAXY_VIRTUAL_ENV:=.venv}

if [ -d "$GALAXY_VIRTUAL_ENV" ];
then
    printf "Activating virtualenv at $GALAXY_VIRTUAL_ENV\n"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

for file in $1/split_info*.json
do
    # echo processing $file
    python ./scripts/extract_dataset_part.py $file
done
