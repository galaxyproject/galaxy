#!/bin/sh

if [ -d .venv ];
then
    printf "Activating virtualenv at %s/.venv\n" $(pwd)
    . .venv/bin/activate
fi

cd `dirname $0`
python ./scripts/create_db.py $@
