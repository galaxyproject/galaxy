#!/bin/sh

#######
# NOTE: To downgrade to a specific version, use something like:
# sh manage_db.sh downgrade --version=3 <tool_shed if using that webapp - galaxy is the default>
#######

if [ -d .venv ];
then
    printf "Activating virtualenv at %s/.venv\n" $(pwd)
    . .venv/bin/activate
fi

cd `dirname $0`
python ./scripts/manage_db.py $@
