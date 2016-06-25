#!/bin/sh

#######
# NOTE: To downgrade to a specific version, use something like:
# sh manage_db.sh downgrade --version=3 <tool_shed if using that webapp - galaxy is the default>
#######

: ${GALAXY_VIRTUAL_ENV:=.venv}

if [ -d "$GALAXY_VIRTUAL_ENV" ];
then
    printf "Activating virtualenv at $GALAXY_VIRTUAL_ENV\n"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

cd `dirname $0`
python ./scripts/manage_db.py $@
