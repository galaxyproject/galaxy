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

# Install uv for fast operation
if ! command -v uv >/dev/null; then
    echo "Installing uv..."
    if command -v curl >/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh || python3 -m pip install uv
    elif command -v wget >/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh || python3 -m pip install uv
    else
        python3 -m pip install uv
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi

# Run uv (this may update pyproject.toml and uv.lock).
if [ -n "$pkg" ]; then
    uv lock --upgrade-package "$pkg"
else
    uv lock --upgrade
fi

# Update pinned requirements files.
UV_EXPORT_OPTIONS='--frozen --no-annotate --no-hashes'
uv export ${UV_EXPORT_OPTIONS} --no-dev > "$this_directory/pinned-requirements.txt"
uv export ${UV_EXPORT_OPTIONS} --only-group=test > "$this_directory/pinned-test-requirements.txt"
uv export ${UV_EXPORT_OPTIONS} --only-group=dev > "$this_directory/dev-requirements.txt"
uv export ${UV_EXPORT_OPTIONS} --only-group=typecheck > "$this_directory/pinned-typecheck-requirements.txt"
