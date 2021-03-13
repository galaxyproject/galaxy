#!/bin/sh

# This script creates a temporary venv and installs poetry into that venv.
# The temporary venv should NOT be activated.
# It then runs poetry inside Galaxy's root directory, potentially updating 
# pyproject.toml and poetry.lock, and the pinned and dev requirements files.

set -e

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Please run this script inside a virtual environment!"
    exit 1
fi

this_directory="$(cd "$(dirname "$0")" > /dev/null && pwd)"

usage() {
    printf "Usage: %s: [-a] [pkg1] [... pkgN]\n" ${0##*/} >&2
}

add=
while getopts 'a' OPTION
do
    case $OPTION in
        a) add=1
           ;;
        ?) usage
           exit 2
           ;;
    esac
done
shift $(($OPTIND - 1))

if [ -n "$add" ] && [ $# -eq 0 ]; then
    printf "When adding (-a), you must provide at least one package name.\n" >&2
    usage
    exit 2
fi

# Create poetry-venv in a tmp directory; install poetry and make shortcut to executable.
poetry_venv=$(mktemp -d "${TMPDIR:-/tmp}/poetry_venv.XXXXXXXXXX")
python3 -m venv "${poetry_venv}"
${poetry_venv}/bin/pip install --upgrade pip poetry
poetry="${poetry_venv}/bin/poetry"

# Run poetry (this may update pyproject.toml and poetry.lock).
if [ -z "$add" ]; then
    "$poetry" update --lock "$@"
else
    "$poetry" add --lock "$@"
fi

# Update pinned requirements.
$poetry export -f requirements.txt --without-hashes --output "$this_directory/pinned-requirements.txt"
$poetry export --dev -f requirements.txt --without-hashes --output "$this_directory/dev-requirements.txt"
