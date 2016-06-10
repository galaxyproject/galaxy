#!/bin/sh

: ${GALAXY_VIRTUAL_ENV:=.venv}

if [ -d "$GALAXY_VIRTUAL_ENV" ];
then
    printf "Activating virtualenv at $GALAXY_VIRTUAL_ENV\n"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

cd `dirname $0`
python ./lib/tool_shed/galaxy_install/migrate/scripts/manage_tools.py $@
