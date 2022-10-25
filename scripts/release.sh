#!/usr/bin/env bash
set -euo pipefail
shopt -s extglob

# TODO: upload packages
# TODO: set dev version in 21.01 (+ 20.09?) branches

: ${VENV:=.venv}
: ${FORK_REMOTE:=origin}
: ${UPSTREAM_REMOTE:=upstream}
: ${UPSTREAM_REMOTE_URL:=git@github.com:galaxyproject/galaxy.git}
: ${DEV_BRANCH:=dev}
: ${STABLE_BRANCH:=master}

# Vars for local releases
: ${RELEASE_LOCAL_TAG:=local}
: ${RELEASE_LOCAL_COMMIT:=$(git rev-parse --short HEAD)}
: ${RELEASE_LOCAL_VERSION:=${RELEASE_LOCAL_TAG}$(date -u +%Y%m%dT%H%M%SZ).${RELEASE_LOCAL_COMMIT}}

# Only use this for dev/testing/CI to ignore forward merge conflicts, skip confirmation and package builds, etc.
: ${TEST_MODE:=false}
$TEST_MODE && MERGE_STRATEGY_OPTIONS='-X ours' || MERGE_STRATEGY_OPTIONS=

VERIFY_PACKAGES=(wheel packaging)

BRANCH_CURR=$(git branch --show-current)

: ${RELEASE_CURR:=$(grep '^VERSION_MAJOR' lib/galaxy/version.py | sed -E -e "s/^[^'\"]*['\"]([^'\"]*)['\"]$/\1/")}
RELEASE_NEXT=
RELEASE_CURR_MINOR=
RELEASE_CURR_MINOR_NEXT=
RELEASE_CURR_MINOR_NEXT_DEV=
RELEASE_TYPE=
PACKAGE_VERSION=

declare -a CLEAN_BRANCHES
declare -a CLEAN_TAGS
CLEAN_BRANCHES=()
CLEAN_TAGS=()

declare -a PUSH_BRANCHES
PUSH_BRANCHES=()

WORKING_DIR_CLEAN=false
ERROR=false

NEXT_RELEASE_TEMPLATE="import datetime; print((datetime.datetime.strptime('RELEASE_CURR', '%y.%m').date() + datetime.timedelta(days=(31 * 4))).strftime('%y.%m'))"
PACKAGE_VERSION_TEMPLATE="import packaging.version; print('.'.join(map(str, packaging.version.parse('VERSION').release)))"
PACKAGE_DEV_VERSION_TEMPLATE="import packaging.version; print(packaging.version.parse('VERSION'))"


while getopts ":clr:" opt; do
    case "$opt" in
        c)
            RELEASE_TYPE='rc'
            ;;
        r)
            RELEASE_CURR="$OPTARG"
            ;;
        l)
            RELEASE_TYPE='local'
            ;;
        *)
            echo "usage: $(basename "$0") [-c (force rc)] [-l (local release)] [-r release version]"
            exit 1
            ;;
    esac
done


function trap_handler() {
    { set +x; } 2>/dev/null
    local file
    $ERROR && log_func=log_error || log_func=log
    $log_func "Cleaning up..."
    if $WORKING_DIR_CLEAN; then
        log_exec git reset -- .
        log_exec git checkout -- .
    fi
    [ "$(git branch --show-current)" == "$BRANCH_CURR" ] || log_exec git checkout "$BRANCH_CURR"
    [ "${#CLEAN_BRANCHES[@]}" -eq 0 ] || git branch -D "${CLEAN_BRANCHES[@]}"
    $ERROR && exit 1 || exit 0
}


function trap_handler_err() {
    ERROR=true
    for tag in "${CLEAN_TAGS[@]}"; do
        log_exec git tag -d "$tag"
    done
    trap_handler
}


function trap_handler_ok() {
    # if $ERROR is true then the trap handler already ran
    $ERROR || trap_handler
}


trap "trap_handler_err" SIGTERM SIGINT ERR
trap "trap_handler_ok" EXIT


function log() {
    [ -t 0 ] && echo -e '\033[1;32m#' "$@" '\033[0m' 1>&2 || echo '#' "$@" 1>&2
}


function log_warning() {
    [ -t 0 ] && echo -e '\033[1;33mWARNING:' "$@" '\033[0m' 1>&2 || echo 'WARNING:' "$@" 1>&2
}


function log_error() {
    [ -t 0 ] && echo -e '\033[1;31mERROR:' "$@" '\033[0m' 1>&2 || echo 'ERROR:' "$@" 1>&2
}


function log_debug() {
    echo "####" "$@" 1>&2
}


function log_exec() {
    local rc
    set -x
    "$@"
    { rc=$?; set +x; } 2>/dev/null
    return $rc
}


function sed_inplace() {
    [ $# -gt 2 ] || { log_error "sed_inplace called with less than 3 args: " "$@"; exit 1; }
    log_exec sed -i.bak-release "$@"
    # filename should always be the final arg
    rm "${!#}.bak-release"
}


function fork_owner() {
    local url=$(git remote get-url "$FORK_REMOTE")
    case "$url" in
        https://github.com/*)
            echo "$url" | awk -F/ '{print $4}'
            ;;
        git@github.com:*)
            echo "$url" | awk -F: '{print $2}' | awk -F/ '{print $1}'
            ;;
        file:///*)
            echo '__DEV_TEST_USER__'
            ;;
        *)
            log_error "Cannot parse remote '$FORK_REMOTE' url for owner username: $url"
            exit 1
            ;;
    esac
}


function ensure_upstream() {
    if ! git remote -v | grep -E "^${UPSTREAM_REMOTE}\s+" >/dev/null; then
        log_warning "Remote ${UPSTREAM_REMOTE} does not exist, will be added with URL: ${UPSTREAM_REMOTE_URL}"
        log_exec git remote add "$UPSTREAM_REMOTE" "$UPSTREAM_REMOTE_URL"
    fi
}


function ensure_prereqs() {
    local pip_list
    log "Checking for uncommitted local modifications..."
    log_exec git diff --stat --exit-code || { log_error "Some files have changes"; exit 1; }
    WORKING_DIR_CLEAN=true
    log "Checking for required packages..."
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        [ -d "$VENV" ] || { log_error "Missing venv, please create: ${VENV}"; exit 1; }
        . "${VENV}/bin/activate"
    fi
    pip_list=$(log_exec "${VENV}/bin/pip" list)
    for package in ${VERIFY_PACKAGES[@]}; do
        echo "$pip_list" | grep -E "^${package}\s+" || { log_error "Package '${package}' missing from venv: ${VENV}" ; exit 1; }
    done
}


function user_verify_release() {
    log "Release Details"
    local future
    case "${RELEASE_NEXT:-}" in
        '')
            future="${RELEASE_CURR}.${RELEASE_CURR_MINOR_NEXT_DEV}"
            ;;
        *)
            future="${RELEASE_NEXT}.dev0"
            ;;
    esac
    cat <<EOF
Release Type:		${RELEASE_TYPE}
Major Version:		${RELEASE_CURR}
Minor Version:		${RELEASE_CURR_MINOR_NEXT}
Package Version:	${PACKAGE_VERSION}
Future Version:		${future}
EOF
    if $TEST_MODE; then
        log "Confirmation not requested, proceeding..."
    else
        log "Press any key to confirm or ^C to exit"
        read -n 1 -s
    fi
}


function release_next() {
    local curr="$1"
    python3 -c "${NEXT_RELEASE_TEMPLATE/RELEASE_CURR/$curr}"
}


function packaging_version() {
    local version="$1"
    local dev_release="$2"
    if $dev_release; then
        python3 -c "${PACKAGE_DEV_VERSION_TEMPLATE/VERSION/$version}"
    else
        python3 -c "${PACKAGE_VERSION_TEMPLATE/VERSION/$version}"
    fi
}


function git_checkout_temp() {
    local name="$1"
    local ref="$2"
    log_exec git checkout --no-track -b "$name" "$ref"
    CLEAN_BRANCHES+=("$name")
}


function branch_exists() {
    local branch="$1"
    local ref_base
    case "$branch" in
        */*)
            ref_base='refs/remotes'
            ;;
        *)
            ref_base='refs/heads'
            ;;
    esac
    git for-each-ref --format='%(refname:short)' "${ref_base}/${branch}" | grep -q "^${branch}\$"
}


function _test_forward_merge() {
    local curr="$1"
    local next="$(release_next "$curr")"
    local curr_branch="${UPSTREAM_REMOTE}/release_${curr}"
    local next_branch="${UPSTREAM_REMOTE}/release_${next}"
    local curr_local_branch="__release_merge_test_${curr}"
    local next_local_branch="__release_merge_test_${next}"
    local recurse=true
    log "Testing forward merge of ${curr} to ${next}"
    if ! branch_exists "$curr_local_branch"; then
        branch_exists "$curr_branch" || { log_error "No existing branch for merge test: ${curr_branch}"; exit 1; }
        git_checkout_temp "$curr_local_branch" "$curr_branch"
    fi
    if ! branch_exists "$next_branch"; then
        next_branch="${UPSTREAM_REMOTE}/${DEV_BRANCH}"
        recurse=false
    fi
    git_checkout_temp "$next_local_branch" "$next_branch"
    # Test the merge even if ignoring just to test the code path
    log_exec git merge $MERGE_STRATEGY_OPTIONS -m 'test merge; please ignore' "$curr_local_branch" || { 
        log_error "Merging unmodified ${curr} to ${next} failed, resolve upstream first!"; exit 1; }
    if $recurse; then
        _test_forward_merge "$next"
    fi
}


function test_forward_merge() {
    local branch_curr=$(git branch --show-current)
    _test_forward_merge "$@"
    git checkout "$branch_curr"
}


function perform_stable_merge() {
    [ "$RELEASE_TYPE" == 'initial' -o "$RELEASE_TYPE" == 'point' ] || return 0
    local branch_curr=$(git branch --show-current)
    git_checkout_temp '__stable' "${UPSTREAM_REMOTE}/${STABLE_BRANCH}"
    local stable=$(get_version_major)
    local curr_int=$(echo "$RELEASE_CURR" | tr -d .)
    local stable_int=$(echo "$stable" | tr -d .)
    if [ "$curr_int" -ge "$stable_int" ]; then
        log "Release '${RELEASE_CURR}' >= stable branch release '${stable}', merging 'release_${RELEASE_CURR}' to '${STABLE_BRANCH}'"
        log_exec git merge $MERGE_STRATEGY_OPTIONS -m "Merge branch 'release_${RELEASE_CURR}' into '${STABLE_BRANCH}'" "__release_${RELEASE_CURR}"
        PUSH_BRANCHES+=("__stable:${STABLE_BRANCH}")
    else
        log "Release '${RELEASE_CURR}' < stable branch release '${stable}', skipping merge to '${STABLE_BRANCH}'"
    fi
    git checkout "$branch_curr"
}


function _perform_forward_merge() {
    local curr="$1"
    local next="$(release_next "$curr")"
    local curr_branch="${UPSTREAM_REMOTE}/release_${curr}"
    local next_branch="${UPSTREAM_REMOTE}/release_${next}"
    local curr_local_branch="__release_${curr}"
    local next_local_branch="__release_${next}"
    local recurse=true
    log "Performing forward merge of ${curr} to ${next}"
    branch_exists "$curr_local_branch" || { log_error "Missing expected branch: ${curr_local_branch}"; exit 1; }
    branch_exists "$next_local_branch" && { log_error "Unexpected branch exists: ${next_local_branch}"; exit 1; }
    PUSH_BRANCHES+=("${curr_local_branch}:release_${curr}")
    if ! branch_exists "$next_branch"; then
        next_branch="${UPSTREAM_REMOTE}/${DEV_BRANCH}"
        recurse=false
        PUSH_BRANCHES+=("${next_local_branch}:${DEV_BRANCH}")
    fi
    git_checkout_temp "$next_local_branch" "$next_branch"
    # This should necessarily result in conflicts merging version.py
	log_exec git merge -X ours -m "Merge branch 'release_${curr}' into 'release_${next}'" "$curr_local_branch"
    if $recurse; then
        _perform_forward_merge "$next"
    fi
}


function perform_forward_merge() {
    local curr="$1"
    local branch_curr=$(git branch --show-current)
    _perform_forward_merge "$@"
    declare -p PUSH_BRANCHES
    git checkout "$branch_curr"
}


function push_merged() {
    local curr="$1"
    for branch in "${PUSH_BRANCHES[@]}"; do
        log "Pushing '${branch}' to remote '${UPSTREAM_REMOTE}'"
        log_exec git push "$UPSTREAM_REMOTE" "$branch"
    done
    if [ "$RELEASE_TYPE" == 'initial' -o "$RELEASE_TYPE" == 'point' ]; then
        log_exec git push --tags "$UPSTREAM_REMOTE"
    fi
}


function set_package_version_var() {
    local package_version_minor
    local dev_release='false'
    case "$RELEASE_CURR_MINOR_NEXT" in
        [0-9]*)
            package_version_minor="$RELEASE_CURR_MINOR_NEXT"
            ;;
        dev)
            # TODO: you can remove this case once the current dev branch minor version is updated to dev0
            package_version_minor="0dev0"
            dev_release='true'
            ;;
        *)
            package_version_minor="0${RELEASE_CURR_MINOR_NEXT}"
            dev_release='true'
            ;;
    esac
    PACKAGE_VERSION=$(packaging_version "${RELEASE_CURR}.${package_version_minor}" "$dev_release")
}


function increment_minor() {
    local minor="$1"
    case "$minor" in
        +([0-9]))
            [ "$RELEASE_TYPE" != 'rc' ] || {
                log_error "Cannot create rc after release (current version: ${RELEASE_CURR}.${minor})";
                exit 1; }
            echo "$((minor + 1)).dev0"
            ;;
        +([0-9]).dev*)
            [ "$RELEASE_TYPE" != 'rc' ] || {
                log_error "Cannot create rc after release (current version: ${RELEASE_CURR}.${minor})";
                exit 1; }
            echo "${minor%.*}"
            ;;
        rc*)
            if [ "$RELEASE_TYPE" == 'rc' ]; then
                echo "rc$((${minor#rc*} + 1))"
            else
                echo ''
            fi
            ;;
        None|'')
            [ "$RELEASE_TYPE" != 'rc' ] || {
                log_error "Cannot create rc after release (current version: ${RELEASE_CURR}.0)";
                exit 1; }
            echo '1.dev0'
            ;;
        *)
            log_error "Don't know how to increment minor version: ${minor}"
            exit 1
            ;;
    esac
}


function get_version_major() {
    grep '^VERSION_MAJOR' lib/galaxy/version.py | sed -E -e "s/^[^'\"]*['\"]([^'\"]*)['\"]$/\1/"
}


function get_version_minor() {
    grep '^VERSION_MINOR' lib/galaxy/version.py | sed -E -e "s/^[^'\"]*['\"]([^'\"]*)['\"]$/\1/" | tr -d '[[:space:]]'
}


function set_version_vars() {
    RELEASE_CURR="$(get_version_major)"
    RELEASE_CURR_MINOR="$(get_version_minor)"
    [[ "$RELEASE_CURR_MINOR" =~ .*"None"$ ]] && RELEASE_CURR_MINOR='0'
    : ${RELEASE_TYPE:=point}
    RELEASE_CURR_MINOR_NEXT="$(increment_minor "$RELEASE_CURR_MINOR")"
    [ -n "$RELEASE_CURR_MINOR_NEXT" ] || RELEASE_TYPE='initial'
    RELEASE_CURR_MINOR_NEXT_DEV="$(increment_minor "${RELEASE_CURR_MINOR_NEXT}")"
    set_package_version_var
}


function update_galaxy_version() {
    local key="$1"
    local val="$2"
    local match="${3:-.*}"
    log "Updating lib/galaxy/version.py for ${key} = ${val}..."
    sed_inplace -E -e "s/^${key} = ${match}/${key} = \"$val\"/" lib/galaxy/version.py
}


function packages_make_all() {
    local dir
    # subshell to preserve cwd
    (
        cd packages/
        for dir in *; do
            [ ! -d "$dir" -o ! -f "${dir}/setup.cfg" ] && continue
            # can't use log_exec here because we want to capture output
            echo + make -C "$dir" "$@" 1>&2
            make -C "$dir" "$@" >"${dir}/make-${1}.log" 2>&1
        done
    )
}


function update_package_versions() {
    local package_version="${1:-$PACKAGE_VERSION}"
    local project_file
    log "Updating package versions to '${package_version}'..."
    (
        cd packages/
        for dir in *; do
            project_file="${dir}/galaxy/setup.cfg"
            if [ -f "${project_file}" ]; then
                sed_inplace -e "s/^version =.*/version = \"${package_version}\"/" "$project_file"
            fi
        done
    )
    #git diff -- packages/
}


function perform_version_update() {
    local tag_version=
    update_package_versions
    git add -- packages/
    log 'Cleaning package dirs...'
    packages_make_all clean
    log 'Building packages (logs in packages/*/make-dist.log)...'
    if $TEST_MODE; then
        log_debug "Test mode skipping package build"
    else
        packages_make_all dist
    fi
    log 'Committing version changes...'
	log_exec git commit -m "Update version to ${RELEASE_CURR}.${RELEASE_CURR_MINOR_NEXT}"
    case "$RELEASE_TYPE" in
        initial)
            tag_version="${RELEASE_CURR}"
            ;;
        point)
            tag_version="${RELEASE_CURR}.${RELEASE_CURR_MINOR_NEXT}"
            ;;
    esac
    if [ -n "$tag_version" ]; then
        log_exec git tag -m "Tag version ${tag_version}" "v${tag_version}"
        CLEAN_TAGS+=("v${tag_version}")
    fi
}


function perform_version_update_dev() {
    [ "$RELEASE_TYPE" == 'initial' -o "$RELEASE_TYPE" == 'point' ] || return 0
    log "Incrementing release version to '${RELEASE_CURR}.${RELEASE_CURR_MINOR_NEXT_DEV}' for development of next point release"
    update_galaxy_version 'VERSION_MINOR' "$RELEASE_CURR_MINOR_NEXT_DEV"
    log_exec git diff --exit-code && { log_error 'Missing expected version.py changes'; exit 1; } || true
    git add -- lib/galaxy/version.py
    update_package_versions
    git add -- packages/
    log_exec git commit -m "Update version to ${RELEASE_CURR}.${RELEASE_CURR_MINOR_NEXT_DEV}"
}


function create_release_rc_initial() {
    RELEASE_TYPE='rc-initial'
    RELEASE_NEXT="$(release_next "$RELEASE_CURR")"
    RELEASE_CURR_MINOR_NEXT='rc1'
    set_package_version_var
    user_verify_release

    local _dev_branch="${UPSTREAM_REMOTE}/${DEV_BRANCH}"
    git_checkout_temp "__release_${RELEASE_CURR}" "$_dev_branch"

    update_galaxy_version 'VERSION_MAJOR' "$RELEASE_CURR"
    update_galaxy_version 'VERSION_MINOR' "$RELEASE_CURR_MINOR_NEXT"
    log_exec git diff --exit-code && { log_error 'Missing expected version.py changes'; exit 1; } || true
    git add -- lib/galaxy/version.py

    perform_version_update

    # Increment version in dev branch
    git_checkout_temp "__release_${RELEASE_NEXT}" "$_dev_branch"

    update_galaxy_version 'VERSION_MAJOR' "$RELEASE_NEXT"
    update_galaxy_version 'VERSION_MINOR' 'dev0'
    log_exec git diff --exit-code && { log_error 'Missing expected version.py changes'; exit 1; } || true
    git add -- lib/galaxy/version.py
    sed_inplace -e "s/^RELEASE_CURR:=.*/RELEASE_CURR:=${RELEASE_NEXT}/" Makefile
    log_exec git diff --exit-code && { log_error 'Missing expected Makefile changes'; exit 1; } || true
    git add -- Makefile
    local package_version=$(packaging_version "${RELEASE_NEXT}.0dev0" "true")
    update_package_versions "$package_version"
    git add -- packages/
    log_exec git commit -m "Update version to ${RELEASE_NEXT}.dev0"

    # Resolve merge conflicts
	log_exec git merge -X ours -m "Merge branch 'release_${RELEASE_CURR}' into 'dev'" "__release_${RELEASE_CURR}"

    # Push branches for PR
    local owner=$(fork_owner)
    local curr_remote_branch="version-${RELEASE_CURR}.${RELEASE_CURR_MINOR_NEXT}"
    local next_remote_branch="version-${RELEASE_NEXT}.dev"
    log_exec git push "$FORK_REMOTE" "__release_${RELEASE_CURR}:${curr_remote_branch}"
    log_exec git push "$FORK_REMOTE" "__release_${RELEASE_NEXT}:${next_remote_branch}"
    log_exec git push "$UPSTREAM_REMOTE" "refs/remotes/${UPSTREAM_REMOTE}/${DEV_BRANCH}:refs/heads/release_${RELEASE_CURR}"

    #https://github.com/galaxyproject/galaxy/compare/{branch}...{fork_owner}:{branch}
    log "Open a PR from ${owner}/galaxy:${curr_remote_branch} to galaxyproject/galaxy:release_${RELEASE_CURR}"
    echo "- https://github.com/galaxyproject/galaxy/compare/release_${RELEASE_CURR}...${owner}:${curr_remote_branch}" 1>&2
    log "Open a PR from ${owner}/galaxy:${next_remote_branch} to galaxyproject/galaxy:dev"
    echo "- https://github.com/galaxyproject/galaxy/compare/dev...${owner}:${next_remote_branch}" 1>&2
}


function create_release_local() {
    RELEASE_CURR_MINOR="$(get_version_minor)"
    RELEASE_CURR_MINOR_NEXT="${RELEASE_CURR_MINOR}+${RELEASE_LOCAL_VERSION}"
    set_package_version_var
    user_verify_release
    # Append the local portion if this is a point release or the local portion already exists
    update_galaxy_version 'VERSION_MINOR' "\1+${RELEASE_LOCAL_VERSION}" "['\"]([^+]*)[^'\"\]*['\"]$"
    # Set the minor version to 0 and append the local version if the release version is not set (e.g. .0)
    update_galaxy_version 'VERSION_MINOR' "0+${RELEASE_LOCAL_VERSION}" 'None'
    update_galaxy_version 'VERSION_MINOR' "0+${RELEASE_LOCAL_VERSION}" '""'
    log_exec git diff --exit-code && { log_error 'Missing expected version.py changes'; exit 1; } || true
    update_package_versions
    ##git add -- lib/galaxy/version.py packages/*/galaxy/project_*.py
    packages_make_all clean
    log 'Building packages (logs in packages/*/make-dist.log)...'
    packages_make_all dist
    ##git commit -m "Update version to $(RELEASE_CURR)"
    ##git tag -m "Tag version $(RELEASE_CURR)" v$(RELEASE_CURR)
}


function create_release_normal() {
    local _release_curr="$RELEASE_CURR"
    local _release_branch="${UPSTREAM_REMOTE}/release_${RELEASE_CURR}"
    git_checkout_temp "__release_${RELEASE_CURR}" "$_release_branch"
    set_version_vars
    [ "$_release_curr" == "$RELEASE_CURR" ] || {
        log_error "Release is incorrect in branch ${_release_branch}: ${_release_curr} != ${RELEASE_CURR}";
        exit 1; }

    user_verify_release
    test_forward_merge "$RELEASE_CURR"

    update_galaxy_version 'VERSION_MINOR' "$RELEASE_CURR_MINOR_NEXT"
    log_exec git diff --exit-code && { log_error 'Missing expected version.py changes'; exit 1; } || true
    git add -- lib/galaxy/version.py

    perform_version_update
    perform_stable_merge
    perform_version_update_dev
    perform_forward_merge "$RELEASE_CURR"
    push_merged "$RELEASE_CURR"
}


function create_release() {
    log 'Fetching upstream changes...'
    git fetch "$UPSTREAM_REMOTE"
    if [ "$RELEASE_TYPE" == 'local' ]; then
        create_release_local
    elif ! branch_exists "${UPSTREAM_REMOTE}/release_${RELEASE_CURR}"; then
        create_release_rc_initial
    else
        create_release_normal
    fi
}


function main() {
    ensure_upstream
    ensure_prereqs
    create_release
}


main
