#!/bin/bash
#
# Build and/or install packages, for running installed Galaxy from the source
#
# NOTE: Packages are updated and built for release using galaxy-release-util:
#   https://github.com/galaxyproject/galaxy-release-util
#
set -euo pipefail

: ${PACKAGE_LIST_FILE:=packages_by_dep_dag.txt}
: ${PIP_EXTRA_ARGS:=--extra-index-url https://wheels.galaxyproject.org}
#: ${SETUP_VENV:=true}

# Ensure uv is installed
ensure_uv() {
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
}

INSTALL=true
EDITABLE=false
META=false
WHEELHOUSE=

# Prevent making a venv for build deps for each package, Used inside the package dir, so refers to
# <source_root>/packages/.venv
: ${VENV=../.venv}
export VENV

trap_handler() {
    if [ -n "$WHEELHOUSE" ]; then
        rm -rf "$WHEELHOUSE"
    fi
}
trap trap_handler EXIT

while getopts ':bhem' OPTION
do
    case $OPTION in
        b)
            INSTALL=false
            ;;
        h)
            echo "usage: $0 [-bem] [up_to_package]"
            echo "  -b  build only, no install"
            echo "  -e  install packages in \"editable\" mode (uv pip install -e)"
            echo "  -m  install galaxy metapackage, installing pinned deps in meta/requirements.txt"
            exit 0
            ;;
        e)
            EDITABLE=true
            INSTALL=true
            ;;
        m)
            META=true
            ;;
    esac
done
shift $((OPTIND - 1))

up_to="${1:-}"

if [ -n "$up_to" -a ! -d "$up_to" ]; then
    echo "ERROR: package does not exist: $up_to"
    exit 1
fi

while read package; do
    [ -n "$package" ] || continue
    if $INSTALL && [[ $package == meta ]] && ! $META; then continue; fi
    printf "\n========= PACKAGE %s =========\n\n" "$package"
    pushd $package
    if $EDITABLE; then
        # Install package in editable mode using uv (much faster than pip)
        ensure_uv
        uv pip install -e .
    else
        if [ ! -d "$VENV" ]; then
            # Install uv for fast venv creation and package management
            ensure_uv
            
            # Use uv venv for fast virtual environment creation
            uv venv "$VENV" --python python3
            "${VENV}/bin/uv" pip install -r <(grep -v test-requirements.txt dev-requirements.txt)
        fi
        make dist
        if $INSTALL && ! $META; then
            uv pip install dist/*.whl
        fi
    fi
    popd
    [ "$package" != "$up_to" ] || exit
done < "$PACKAGE_LIST_FILE"

if $INSTALL && $META && ! $EDITABLE; then
    WHEELHOUSE=$(mktemp -d -t gxpkgwheelhouseXXXXXX)
    cp */dist/*.whl "$WHEELHOUSE"
    uv pip install $PIP_EXTRA_ARGS --find-links "$WHEELHOUSE" meta/dist/*.whl
fi
