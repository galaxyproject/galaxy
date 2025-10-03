#!/bin/sh

set -e

# This script updates the pinned requirements for linting.
# The lint requirements are split from the other ones since they often have
# incompatible dependencies.

THIS_DIRECTORY="$(cd "$(dirname "$0")" > /dev/null && pwd)"

update_pinned_reqs() {
    VENV=$(mktemp -d "${TMPDIR:-/tmp}/$1_venv.XXXXXXXXXX")
    
    # Install uv for fast package installation
    if ! command -v uv >/dev/null; then
        echo "Installing uv..."
        if command -v curl >/dev/null; then
            curl -LsSf https://astral.sh/uv/install.sh | sh || python3.9 -m pip install uv
        elif command -v wget >/dev/null; then
            wget -qO- https://astral.sh/uv/install.sh | sh || python3.9 -m pip install uv
        else
            python3.9 -m pip install uv
        fi
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    # Use uv venv for fast virtual environment creation
    uv venv "${VENV}" --python python3.9
    . "${VENV}/bin/activate"
    
    # No need to upgrade pip/setuptools - uv handles everything
    uv pip install -r "${THIS_DIRECTORY}/$1-requirements.txt"
    # The grep below is needed to workaround https://github.com/pypa/pip/issues/8331
    uv pip freeze | grep -v 'pkg_resources==0.0.0' > "${THIS_DIRECTORY}/pinned-$1-requirements.txt"
    rm -rf "${VENV}"
}

update_pinned_reqs lint
