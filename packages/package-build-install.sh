#!/bin/bash
#
# Build and/or install packages, for running installed Galaxy from the source
#
# NOTE: Packages are updated and built for release using galaxy-release-util:
#   https://github.com/galaxyproject/galaxy-release-util
#
set -euo pipefail

: "${PACKAGE_LIST_FILE:=packages_by_dep_dag.txt}"
: "${PIP_EXTRA_ARGS:=--extra-index-url https://wheels.galaxyproject.org}"
#: ${SETUP_VENV:=true}

INSTALL=true
EDITABLE=false
META=false
WHEELHOUSE=

if command -v uv >/dev/null; then
    VENV_CMD="$(command -v uv) venv"
    PIP_CMD="$(command -v uv) pip"
else
    VENV_CMD='python3 -m venv'
    PIP_CMD='pip'
fi

# Prevent making a venv for build deps for each package, Used inside the package dir, so refers to
# <source_root>/packages/.venv
: "${VENV=../.venv}"
export VENV

trap_handler() {
    if [ -n "$WHEELHOUSE" ]; then
        rm -rf "$WHEELHOUSE"
    fi
}
trap trap_handler EXIT

usage() {
    echo "usage: $0 [-bem] [up_to_package]"
    echo "  -b  build only, no install"
    echo "  -e  install packages in \"editable\" mode (pip install -e)"
    echo "  -m  install galaxy metapackage, installing pinned deps in meta/requirements.txt"
}

while getopts ':bhem' OPTION
do
    case $OPTION in
        b) INSTALL=false
           ;;
        h) usage
           exit 0
           ;;
        e) EDITABLE=true
           INSTALL=true
           ;;
        m) META=true
           ;;
        ?) usage
           exit 2
           ;;
    esac
done
shift $((OPTIND - 1))

up_to="${1:-}"

if [ -n "$up_to" ] && [ ! -d "$up_to" ]; then
    echo "ERROR: package does not exist: $up_to"
    exit 1
fi

while read -r package; do
    [ -n "$package" ] || continue
    if $INSTALL && [[ $package == meta ]] && ! $META; then continue; fi
    printf "\n========= PACKAGE %s =========\n\n" "$package"
    pushd "$package"
    if $EDITABLE; then
        ${PIP_CMD} install -e .
    else
        if [ ! -d "$VENV" ]; then
            ${VENV_CMD} "$VENV"
            VIRTUAL_ENV="${VENV}" ${PIP_CMD} install -r dev-requirements.txt
        fi
        make dist
        if $INSTALL && ! $META; then
            ${PIP_CMD} install dist/*.whl
        fi
    fi
    popd
    [ "$package" != "$up_to" ] || exit
done < "$PACKAGE_LIST_FILE"

if $INSTALL && $META && ! $EDITABLE; then
    WHEELHOUSE=$(mktemp -d -t gxpkgwheelhouseXXXXXX)
    cp ./*/dist/*.whl "$WHEELHOUSE"
    # shellcheck disable=SC2086
    ${PIP_CMD} install ${PIP_EXTRA_ARGS} --find-links "$WHEELHOUSE" meta/dist/*.whl
fi
