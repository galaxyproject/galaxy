#!/usr/bin/env bash
set -euo pipefail

# Necessary for testing the release script
export TEST_MODE=true

: ${ORIGIN:=origin}
: ${STABLE_BRANCH:=master}

REPO_ROOT=
FORK_ROOT=$(mktemp -d -t galaxy_release_test_XXXXXXXX)

TEST_RELEASE_PREV=
TEST_RELEASE_PREV_MINOR=
TEST_RELEASE_CURR='99.01'
TEST_RELEASE_NEXT='99.05'
TEST_RELEASE_NEXT_NEXT='99.09'

: ${VENV:=${FORK_ROOT}/venv}
export VENV


function trap_handler() {
    [ -z "$FORK_ROOT" ] || rm -rf "$FORK_ROOT"
}
trap "trap_handler" EXIT


function log() {
    [ -t 0 ] && echo -e '\033[1;35m#' "$@" '\033[0m' 1>&2 || echo '#' "$@" 1>&2
}


function log_exec() {
    local rc
    set -x
    "$@"
    { rc=$?; set +x; } 2>/dev/null
    return $rc
}


function log_function() {
    local func_name="$1"; shift
    log ">>>> ${func_name}()"
    $func_name "$@"
    log "<<<< ${func_name}()"
}


function get_repo_root() {
    (
        cd "$(dirname "$0")/.."
        pwd
    )
}


function get_stable_version() {
    local part="$1"
    (
        cd_fork work
        local restore_branch="$(git branch --show-current)"
        git checkout -q --no-track -b __stable_version_check "upstream/${STABLE_BRANCH}"
        grep "^VERSION_${part}" lib/galaxy/version.py | sed -E -e "s/^[^'\"]*['\"]([^'\"]*)['\"]$/\1/"
        git checkout -q "$restore_branch"
        git branch -q -D __stable_version_check
    )
}


function cd_fork() {
    log_exec cd "${FORK_ROOT}/${1}"
}


function make_forks() {
    [ -n "$REPO_ROOT" ] || REPO_ROOT=$(get_repo_root)

    # Use a "work" clone to prevent modifications to current clone
    log_exec git clone --no-checkout "${REPO_ROOT}" "${FORK_ROOT}/work"
    (
        cd_fork work
        # A username and email address are needed to commit
        if [ -z "$(git config --get user.name)" ]; then
            log_exec git config user.name "Test User"
        fi
        if [ -z "$(git config --get user.email)" ]; then
            log_exec git config user.email "test@example.org"
        fi
        if [ "$(git rev-parse --abbrev-ref HEAD)" != dev ]; then
            CURRENT_COMMIT=$(git rev-parse HEAD)
            log "Checking out ref '${CURRENT_COMMIT}' as 'dev'"
            log_exec git checkout --no-track -b dev "$CURRENT_COMMIT"
        fi
    )

    # Create bare origin and upstream repos 
    for repo in origin upstream; do
        log_exec git clone --bare "${FORK_ROOT}/work" "${FORK_ROOT}/${repo}"
        (
            cd_fork "$repo"
            log_exec git remote remove origin
        )
    done

    # Set remotes on work repo
    (
        cd_fork work
        log_exec git remote remove origin
        for repo in origin upstream; do
            log_exec git remote add "$repo" "file://${FORK_ROOT}/${repo}"
        done
    )

    # Fetch release branches to upstream repo
    (
        cd_fork upstream
        log_exec git fetch --no-tags "${REPO_ROOT}" refs/remotes/origin/${STABLE_BRANCH}:${STABLE_BRANCH}
    )

    # Set current (previous) stable release from stable branch
    (
        cd_fork work
        log_exec git fetch --no-tags upstream
    )
    TEST_RELEASE_PREV=$(get_stable_version MAJOR)
    TEST_RELEASE_PREV_MINOR=$(get_stable_version MINOR)
}


function create_venv() {
    if [ ! -d "$VENV" ]; then
        log_exec python3 -m venv "$VENV"
        log_exec "${VENV}/bin/pip" install wheel packaging
    fi
    . "${VENV}/bin/activate"
}


function verify_version() {
    local major="$1"
    local minor="$2"
    local ref="$3"
    local _ref="$3"
    local restore_branch="$(git branch --show-current)"
    [ -n "$(git tag -l $ref)" ]  || _ref="upstream/${ref}"
    log_exec git checkout --no-track -b "__${ref}" "$_ref"
    if grep -q "^VERSION_MAJOR = \"${major}\"$" lib/galaxy/version.py; then
        log "**** Major version '${major}' is correct at ref '${ref}'"
    else
        log "**** Major version '${major}' is incorrect at ref '${ref}':"
        log "$(grep '^VERSION_MAJOR' lib/galaxy/version.py)"
        exit 1
    fi
    if grep -q "^VERSION_MINOR = \"${minor}\"$" lib/galaxy/version.py; then
        log "**** Minor version '${minor}' is correct at ref '${ref}'"
    else
        log "**** Minor version '${minor}' is incorrect at ref '${ref}':"
        log "$(grep '^VERSION_MINOR' lib/galaxy/version.py)"
        exit 1
    fi
    log_exec git checkout "$restore_branch"
    log_exec git branch -D "__${ref}"
}


function verify_makefile_version() {
    local major="$1"
    local ref="$2"
    local _ref="$2"
    local restore_branch="$(git branch --show-current)"
    [ -n "$(git tag -l $ref)" ]  || _ref="upstream/${ref}"
    log_exec git checkout --no-track -b "__${ref}" "$_ref"
    if grep -q "^RELEASE_CURR:=${major}$" Makefile; then
        log "**** RELEASE_CURR '${major}' is correct in Makefile at ref '${ref}'"
    else
        log "**** RELEASE_CURR '${major}' is incorrect in Makefile at ref '${ref}':"
        log "$(grep '^RELEASE_CURR' Makefile)"
        exit 1
    fi
    log_exec git checkout "$restore_branch"
    log_exec git branch -D "__${ref}"
}


function test_rc() {
    log "Test creation of ${TEST_RELEASE_CURR}.rc1..."
    (
        cd_fork work
        log_exec "${REPO_ROOT}/scripts/release.sh" -r "$TEST_RELEASE_CURR"
        # simulate merging RC PRs
        log_exec git push upstream refs/remotes/origin/version-${TEST_RELEASE_CURR}.rc1:refs/heads/release_${TEST_RELEASE_CURR}
        log_exec git push upstream refs/remotes/origin/version-${TEST_RELEASE_NEXT}.dev:refs/heads/dev

        # verify        major                   minor                       ref (branch/tag)
        verify_version  "$TEST_RELEASE_CURR"    'rc1'                       "release_${TEST_RELEASE_CURR}"
        verify_version  "$TEST_RELEASE_NEXT"    'dev0'                      'dev'
        verify_version  "$TEST_RELEASE_PREV"    "$TEST_RELEASE_PREV_MINOR"  "$STABLE_BRANCH"  # should not have changed
        verify_makefile_version "$TEST_RELEASE_NEXT" 'dev'
    )
}


function test_rc_point() {
    log "Test creation of ${TEST_RELEASE_CURR}.rc2..."
    (
        cd_fork work
        log_exec "${REPO_ROOT}/scripts/release.sh" -c -r "$TEST_RELEASE_CURR"
        # verify        major                   minor                       ref (branch/tag)
        verify_version  "$TEST_RELEASE_CURR"    'rc2'                       "release_${TEST_RELEASE_CURR}"
        verify_version  "$TEST_RELEASE_NEXT"    'dev0'                      'dev'
        verify_version  "$TEST_RELEASE_PREV"    "$TEST_RELEASE_PREV_MINOR"  "$STABLE_BRANCH"  # should not have changed
        verify_makefile_version "$TEST_RELEASE_NEXT" 'dev'
    )
}


function test_initial() {
    log "Test creation of ${TEST_RELEASE_CURR} initial (.0)..."
    (
        cd_fork work
        log_exec "${REPO_ROOT}/scripts/release.sh" -r "$TEST_RELEASE_CURR"
        # re-fetch from upstream to ensure tags are correct
        log_exec git tag -d $(git tag -l)
        log_exec git fetch upstream

        # verify        major                   minor       ref (branch/tag)
        verify_version  "$TEST_RELEASE_CURR"    ''          "v${TEST_RELEASE_CURR}"
        verify_version  "$TEST_RELEASE_CURR"    '1.dev0'    "release_${TEST_RELEASE_CURR}"
        verify_version  "$TEST_RELEASE_NEXT"    'dev0'      'dev'
        verify_version  "$TEST_RELEASE_CURR"    ''          "$STABLE_BRANCH"
        verify_makefile_version "$TEST_RELEASE_NEXT" 'dev'
    )
}


function test_point() {
    log "Test creation of ${TEST_RELEASE_CURR}.1..."
    (
        cd_fork work
        log_exec "${REPO_ROOT}/scripts/release.sh" -r "$TEST_RELEASE_CURR"
        log_exec git tag -d $(git tag -l)
        log_exec git fetch upstream

        # verify        major                   minor       ref (branch/tag)
        verify_version  "$TEST_RELEASE_CURR"    '1'         "$STABLE_BRANCH"
        verify_version  "$TEST_RELEASE_CURR"    '1'         "v${TEST_RELEASE_CURR}.1"
        verify_version  "$TEST_RELEASE_CURR"    '2.dev0'    "release_${TEST_RELEASE_CURR}"
        verify_version  "$TEST_RELEASE_NEXT"    'dev0'      'dev'
        verify_makefile_version "$TEST_RELEASE_NEXT" 'dev'
    )
}


function test_next() {
    log "Test creation of ${TEST_RELEASE_NEXT} rc1 -> initial (.0)..."
    (
        cd_fork work
        # create RC
        log_exec "${REPO_ROOT}/scripts/release.sh" -r "$TEST_RELEASE_NEXT"
        # simulate merging RC PRs
        log_exec git push upstream refs/remotes/origin/version-${TEST_RELEASE_NEXT}.rc1:refs/heads/release_${TEST_RELEASE_NEXT}
        log_exec git push upstream refs/remotes/origin/version-${TEST_RELEASE_NEXT_NEXT}.dev:refs/heads/dev
        # create initial
        log_exec "${REPO_ROOT}/scripts/release.sh" -r "$TEST_RELEASE_NEXT"
        log_exec git tag -d $(git tag -l)
        log_exec git fetch upstream

        # verify        major                       minor       ref (branch/tag)
        verify_version  "$TEST_RELEASE_NEXT"        ''          "$STABLE_BRANCH"
        verify_version  "$TEST_RELEASE_NEXT"        ''          "v${TEST_RELEASE_NEXT}"
        verify_version  "$TEST_RELEASE_NEXT"        '1.dev0'    "release_${TEST_RELEASE_NEXT}"
        verify_version  "$TEST_RELEASE_NEXT_NEXT"   'dev0'      'dev'
        verify_makefile_version "$TEST_RELEASE_NEXT" "release_${TEST_RELEASE_NEXT}"
        verify_makefile_version "$TEST_RELEASE_NEXT_NEXT" 'dev'
    )
}


function test_prev() {
    log "Test creation of ${TEST_RELEASE_CURR}.2..."
    (
        cd_fork work
        log_exec "${REPO_ROOT}/scripts/release.sh" -r "$TEST_RELEASE_CURR"
        log_exec git tag -d $(git tag -l)
        log_exec git fetch upstream

        # verify        major                       minor       ref (branch/tag)
        verify_version  "$TEST_RELEASE_NEXT"        ''          "$STABLE_BRANCH"
        verify_version  "$TEST_RELEASE_CURR"        '2'         "v${TEST_RELEASE_CURR}.2"
        verify_version  "$TEST_RELEASE_CURR"        '3.dev0'    "release_${TEST_RELEASE_CURR}"
        verify_version  "$TEST_RELEASE_NEXT"        '1.dev0'    "release_${TEST_RELEASE_NEXT}"
        verify_version  "$TEST_RELEASE_NEXT_NEXT"   'dev0'      'dev'
        verify_makefile_version "$TEST_RELEASE_NEXT" "release_${TEST_RELEASE_NEXT}"
        verify_makefile_version "$TEST_RELEASE_NEXT_NEXT" 'dev'
    )
}


function main() {
    log "TIP: test output is magenta, release script output is green/red"
    log_function make_forks
    log_function create_venv
    log_function test_rc
    log_function test_rc_point
    log_function test_initial
    log_function test_point
    log_function test_next
    log_function test_prev
    log "OK"
}


main
