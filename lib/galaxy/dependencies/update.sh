#!/bin/sh
set -e

# You can pass one or more package specifications to this script to add only
# them without updating all the rest of the requirements.

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Please run this script inside a virtual environment!"
    exit 1
fi

THIS_DIRECTORY="$(cd "$(dirname "$0")" > /dev/null && pwd)"

pip install --upgrade pip setuptools poetry
if [ $# -gt 0 ]; then
    poetry add --lock "$@"
else
    poetry update -v --lock
fi
poetry export -f requirements.txt --without-hashes --output "$THIS_DIRECTORY/pinned-requirements.txt"
poetry export --dev -f requirements.txt --without-hashes --output "$THIS_DIRECTORY/dev-requirements.txt"
