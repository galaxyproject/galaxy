#!/bin/sh

# This script installs poetry if it's not already installed in the user account.
# It then runs poetry inside Galaxy's root directory, potentially updating 
# pyproject.toml and poetry.lock, and the pinned and dev requirements files.

set -e

this_directory="$(cd "$(dirname "$0")" > /dev/null && pwd)"

usage() {
    printf "Usage: %s: [-a] [pkg_spec...]\n" ${0##*/} >&2
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
    printf "When adding (-a), you must provide at least one package specification.\n" >&2
    usage
    exit 2
fi

# Install the latest version of poetry into the user account
curl -sSL https://install.python-poetry.org | python3 -

# Run poetry (this may update pyproject.toml and poetry.lock).
if [ -z "$add" ]; then
    poetry update -vv --lock "$@"
else
    poetry add -vv --lock "$@"
fi

# Update pinned requirements.
poetry export -f requirements.txt --without-hashes --output "$this_directory/pinned-requirements.txt"
poetry export --dev -f requirements.txt --without-hashes --output "$this_directory/dev-requirements.txt"
