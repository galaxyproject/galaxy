#!/bin/bash
#
# Build and/or install packages, for running installed Galaxy from the source
#
# NOTE: Packages are updated and built for release using galaxy-release-util:
#   https://github.com/galaxyproject/galaxy-release-util
#
set -euo pipefail

: "${PACKAGE_LIST_FILE:=packages_by_dep_dag.txt}"
#: ${SETUP_VENV:=true}

INSTALL=true
EDITABLE=false
META=false
WHEELHOUSE=

# Use one environment for package build dependencies and the installed Galaxy.
: "${VENV=../.venv}"
case "$VENV" in
    /*) ;;
    *) VENV="$(pwd)/$VENV" ;;
esac
export VENV

if [ -z "${PIP_EXTRA_ARGS:-}" ]; then
    if command -v uv >/dev/null; then
        PIP_EXTRA_ARGS="--index-strategy unsafe-best-match --extra-index-url https://wheels.galaxyproject.org/simple"
    else
        PIP_EXTRA_ARGS="--extra-index-url https://wheels.galaxyproject.org/simple"
    fi
fi

ensure_venv() {
    if [ ! -d "$VENV" ]; then
        if command -v uv >/dev/null; then
            uv venv "$VENV"
        else
            python3 -m venv "$VENV"
        fi
    fi
}

pip_install() {
    ensure_venv
    if command -v uv >/dev/null; then
        uv pip install --python "$VENV/bin/python" "$@"
    else
        "$VENV/bin/python" -m pip install "$@"
    fi
}

build_release_packages() {
    if command -v galaxy-release-util >/dev/null && galaxy-release-util --help >/dev/null 2>&1; then
        galaxy-release-util build --galaxy-root ..
    elif command -v uvx >/dev/null; then
        local release_util_requirement
        release_util_requirement=$(grep '^galaxy-release-util==' ../lib/galaxy/dependencies/dev-requirements.txt)
        uvx --from "$release_util_requirement" galaxy-release-util build --galaxy-root ..
    else
        echo "ERROR: galaxy-release-util is required to build the Galaxy metapackage." >&2
        exit 1
    fi
}

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

if $META && ! $EDITABLE; then
    build_release_packages
else
    while read -r package; do
        [ -n "$package" ] || continue
        if $INSTALL && [[ $package == meta ]] && ! $META; then continue; fi
        printf "\n========= PACKAGE %s =========\n\n" "$package"
        pushd "$package"
        if $EDITABLE; then
            pip_install -e .
        else
            if [ ! -d "$VENV" ]; then
                ensure_venv
                pip_install -r dev-requirements.txt
            fi
            make dist
            if $INSTALL && ! $META; then
                pip_install dist/*.whl
            fi
        fi
        popd
        [ "$package" != "$up_to" ] || exit
    done < "$PACKAGE_LIST_FILE"
fi

if $INSTALL && $META && ! $EDITABLE; then
    WHEELHOUSE=$(mktemp -d -t gxpkgwheelhouseXXXXXX)
    cp ./*/dist/*.whl "$WHEELHOUSE"
    # shellcheck disable=SC2086
    pip_install ${PIP_EXTRA_ARGS} --find-links "$WHEELHOUSE" meta/dist/*.whl
fi
