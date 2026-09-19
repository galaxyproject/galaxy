#!/bin/sh

cd "$(dirname "$0")"/..

GALAXY_VIRTUAL_ENV="${GALAXY_VIRTUAL_ENV:-.venv}"
if [ -d "$GALAXY_VIRTUAL_ENV" ]; then
    printf "Activating virtualenv at $GALAXY_VIRTUAL_ENV\n"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

PYTHONPATH=lib:$PYTHONPATH
export PYTHONPATH

python -c "import galaxy.tours.validate; galaxy.tours.validate.main()" $*
