#!/bin/sh

# This script installs poetry if it's not already installed in the user account.
# It then runs poetry inside Galaxy's root directory, potentially updating 
# pyproject.toml and poetry.lock, and the pinned and dev requirements files.

set -e

SUPPORTED_PYTHON_VERSIONS="3.7 3.8 3.9 3.10 3.11"
NOT_SUPPORTED_NEXT_PYTHON_VERSION="3.12"

this_directory="$(cd "$(dirname "$0")" > /dev/null && pwd)"

usage() {
    printf "Usage: %s: [-a] [pkg_spec...]\n" "${0##*/}" >&2
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
shift $((OPTIND - 1))

if [ -n "$add" ] && [ $# -eq 0 ]; then
    printf "When adding (-a), you must provide at least one package specification.\n" >&2
    usage
    exit 2
fi

# Install the latest version of poetry into the user account
curl -sSL https://install.python-poetry.org | python3 -
poetry self add poetry-plugin-export

# Run poetry (this may update pyproject.toml and poetry.lock).
if [ -z "$add" ]; then
    poetry update -vv --lock "$@"
else
    poetry add -vv --lock "$@"
fi

# Update pinned requirements files.
PINNED_REQUIREMENTS_FILE=$this_directory/pinned-requirements.txt
PINNED_DEV_REQUIREMENTS_FILE=$this_directory/dev-requirements.txt
poetry export -f requirements.txt --without-hashes --output "$PINNED_REQUIREMENTS_FILE"
poetry export --only dev -f requirements.txt --without-hashes --output "$PINNED_DEV_REQUIREMENTS_FILE"

# Fix requirements

latest_package_version_for_python_version () {
    PIP_INDEX_OUT=$(pip index versions --python-version "$2" "$1")
    echo "$PIP_INDEX_OUT" | head -n 1 | sed -e 's/.* (\(.*\)).*/\1/'
}

split_requirement () {
    PACKAGE_NAME=$1

    if ! pip index version --help >/dev/null; then
        echo "pip >= 21.2.1 required for the 'index' command"
        exit 1
    fi

    NEW_REQUIREMENTS=
    PREVIOUS_LATEST_PACKAGE_VERSION=
    for PYTHON_VERSION in $SUPPORTED_PYTHON_VERSIONS; do
        LATEST_PACKAGE_VERSION=$(latest_package_version_for_python_version "$PACKAGE_NAME" "$PYTHON_VERSION")
        if [ -z "$NEW_REQUIREMENTS" ]; then
            NEW_REQUIREMENTS="$PACKAGE_NAME==$LATEST_PACKAGE_VERSION ; python_version >= \"$PYTHON_VERSION\""
        elif [ "$LATEST_PACKAGE_VERSION" != "$PREVIOUS_LATEST_PACKAGE_VERSION" ]; then
            NEW_REQUIREMENTS="$NEW_REQUIREMENTS and python_version < \"$PYTHON_VERSION\"\n$PACKAGE_NAME==$LATEST_PACKAGE_VERSION ; python_version >= \"$PYTHON_VERSION\""
        fi
        PREVIOUS_LATEST_PACKAGE_VERSION=$LATEST_PACKAGE_VERSION
    done
    if [ -n "$NOT_SUPPORTED_NEXT_PYTHON_VERSION" ]; then
        NEW_REQUIREMENTS="$NEW_REQUIREMENTS and python_version < \"$NOT_SUPPORTED_NEXT_PYTHON_VERSION\""
    fi

    sed -i.orig -e "s/^$PACKAGE_NAME==.*/$NEW_REQUIREMENTS/" "$PINNED_REQUIREMENTS_FILE" "$PINNED_DEV_REQUIREMENTS_FILE"
}

# For some packages there is no recent version that works on all Python versions
# supported by Galaxy, so Poetry resorts to an old version that didn't have a
# maximum Python version pin. Here we replace any such requirement with multiple
# Python-version-specific requirements.
split_requirement numpy
split_requirement scipy
