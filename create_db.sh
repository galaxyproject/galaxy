#!/bin/sh

: ${GALAXY_VIRTUAL_ENV:=.venv}

if [ -d "$GALAXY_VIRTUAL_ENV" ];
then
    printf "Activating virtualenv at $GALAXY_VIRTUAL_ENV\n"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

cd `dirname $0`
python ./scripts/create_db.py $@
