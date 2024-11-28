#!/bin/sh

# This script installs uv if it's not already installed in the user account.
# It then runs uv inside Galaxy's root directory, potentially updating
# pyproject.toml and uv.lock, and the pinned requirements files.

set -e

this_directory="$(cd "$(dirname "$0")" > /dev/null && pwd)"

usage() {
    printf "Usage: %s: [-p pkg]\n" "${0##*/}" >&2
}

pkg=
while getopts 'p:h' OPTION
do
    case $OPTION in
        p) pkg="$OPTARG"
           ;;
        h) usage
           exit 0
           ;;
        ?) usage
           exit 2
           ;;
    esac
done
shift $((OPTIND - 1))

# Create a virtual environment in a tmp directory and install uv into it
uv_venv=$(mktemp -d "${TMPDIR:-/tmp}/uv_venv.XXXXXXXXXX")
python3 -m venv "${uv_venv}"
"${uv_venv}/bin/python" -m pip install uv
uv="${uv_venv}/bin/uv"

# Run uv (this may update pyproject.toml and uv.lock).
if [ -n "$pkg" ]; then
    ${uv} lock --upgrade-package "$pkg"
else
    ${uv} lock --upgrade
fi

# Update pinned requirements files.
${uv} export --frozen --no-hashes --no-dev > "$this_directory/pinned-requirements.txt"
${uv} export --frozen --no-hashes --only-group=dev > "$this_directory/dev-requirements.txt"
${uv} export --frozen --no-hashes --only-group=typecheck > "$this_directory/pinned-typecheck-requirements.txt"
