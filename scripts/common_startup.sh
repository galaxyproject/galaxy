#!/bin/sh
set -e

# The caller may do this as well, but since common_startup.sh can be called independently, we need to do it here
. ./scripts/common_startup_functions.sh

SET_VENV=1
for arg in "$@"; do
    if [ "$arg" = "--skip-venv" ]; then
        SET_VENV=0
        skip_venv=1  # for common startup functions
    fi
done

DEV_WHEELS=0
FETCH_WHEELS=1
CREATE_VENV=1
REPLACE_PIP=$SET_VENV
COPY_SAMPLE_FILES=1
SKIP_CLIENT_BUILD=${GALAXY_SKIP_CLIENT_BUILD:-0}
NODE_VERSION=${GALAXY_NODE_VERSION:-"$(cat client/.node_version)"}
YARN_INSTALL_OPTS=${YARN_INSTALL_OPTS:-"--network-timeout 300000 --check-files"}

for arg in "$@"; do
    [ "$arg" = "--skip-eggs" ] && FETCH_WHEELS=0
    [ "$arg" = "--skip-wheels" ] && FETCH_WHEELS=0
    [ "$arg" = "--dev-wheels" ] && DEV_WHEELS=1
    [ "$arg" = "--no-create-venv" ] && CREATE_VENV=0
    [ "$arg" = "--no-replace-pip" ] && REPLACE_PIP=0
    [ "$arg" = "--replace-pip" ] && REPLACE_PIP=1
    [ "$arg" = "--stop-daemon" ] && FETCH_WHEELS=0
    [ "$arg" = "--skip-samples" ] && COPY_SAMPLE_FILES=0
    [ "$arg" = "--skip-client-build" ] && SKIP_CLIENT_BUILD=1
done

SAMPLES="
    lib/tool_shed/scripts/bootstrap_tool_shed/user_info.xml.sample
    tool-data/shared/ucsc/builds.txt.sample
    tool-data/shared/ucsc/manual_builds.txt.sample
    static/welcome.html.sample
"

RMFILES="
    lib/pkg_resources.pyc
"

# return true if $1 is in $2 else false
in_dir() {
    case $1 in
        $2*)
            return 0
            ;;
        ''|*)
            return 1
            ;;
    esac
}

# return true if $1 is in $VIRTUAL_ENV else false
in_venv() {
    in_dir "$1" "$VIRTUAL_ENV"
}

# return true if $1 is in $CONDA_PREFIX else false
in_conda_env() {
    in_dir "$1" "$CONDA_PREFIX"
}

if [ $COPY_SAMPLE_FILES -eq 1 ]; then
    # Create any missing config/location files
    for sample in $SAMPLES; do
        file=${sample%.sample}
        if [ ! -f "$file" ] && [ -f "$sample" ]; then
            echo "Initializing $file from $(basename "$sample")"
            cp "$sample" "$file"
        fi
    done
fi

# remove problematic cached files
for rmfile in $RMFILES; do
    [ -f "$rmfile" ] && rm -f "$rmfile"
done

# Determine branch (if using git)
if command -v git >/dev/null && [ -d .git ]; then
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    case $GIT_BRANCH in
        release_*|master)
            # All branches should now build the client as necessary, turn this
            # back into an if?  Or is there more we need to do here?
            ;;
        *)
            DEV_WHEELS=1
            # SKIP_CLIENT_BUILD will default to false, but can be overridden by the command line argument
            ;;
    esac
else
    GIT_BRANCH=0
fi

: ${GALAXY_VIRTUAL_ENV:=.venv}
# GALAXY_CONDA_ENV is not set here because we don't want to execute the Galaxy version check if we don't need to

if [ $SET_VENV -eq 1 ] && [ $CREATE_VENV -eq 1 ]; then
    if [ ! -d "$GALAXY_VIRTUAL_ENV" ]; then
        # Locate `conda` and set $CONDA_EXE (if needed). setup_python calls this
        # as well, but in this case we need it done beforehand.
        set_conda_exe
        if [ -n "$CONDA_EXE" ]; then
            echo "Found Conda, will set up a virtualenv using conda."
            echo "To use a virtualenv instead, create one with a non-Conda Python at $GALAXY_VIRTUAL_ENV"
            : ${GALAXY_CONDA_ENV:="_galaxy_"}
            if [ "$CONDA_DEFAULT_ENV" != "$GALAXY_CONDA_ENV" ]; then
                if ! check_conda_env "$GALAXY_CONDA_ENV"; then
                    echo "Creating Conda environment for Galaxy: $GALAXY_CONDA_ENV"
                    echo "To avoid this, use the --no-create-venv flag or set \$GALAXY_CONDA_ENV to an"
                    echo "existing environment before starting Galaxy."
                    $CONDA_EXE create --yes --override-channels --channel conda-forge --channel defaults --name "$GALAXY_CONDA_ENV" 'python=3.7' 'pip>=19.3'
                    unset __CONDA_INFO
                fi
                conda_activate
            fi
            python3 -m venv "$GALAXY_VIRTUAL_ENV"
        else
            # If $GALAXY_VIRTUAL_ENV does not exist, and there is no conda available, attempt to create it.

            # Ensure Python is a supported version before creating $GALAXY_VIRTUAL_ENV
            find_python_command
            "$GALAXY_PYTHON" ./scripts/check_python.py || exit 1
            echo "Creating Python virtual environment for Galaxy: $GALAXY_VIRTUAL_ENV"
            echo "using Python: $GALAXY_PYTHON"
            echo "To avoid this, use the --no-create-venv flag or set \$GALAXY_VIRTUAL_ENV to an"
            echo "existing environment before starting Galaxy."
            # First try to use the venv standard library module, although it is
            # not always installed by default on Linux distributions.
            if ! "$GALAXY_PYTHON" -m venv "$GALAXY_VIRTUAL_ENV"; then
                echo "Creating the Python virtual environment using the venv standard library module failed."
                echo "Trying with virtualenv now."
                if command -v virtualenv >/dev/null; then
                    virtualenv -p "$GALAXY_PYTHON" "$GALAXY_VIRTUAL_ENV"
                else
                    # Download virtualenv zipapp
                    min_python_version=3.7
                    vurl="https://bootstrap.pypa.io/virtualenv/${min_python_version}/virtualenv.pyz"
                    vtmp=$(mktemp -d -t galaxy-virtualenv-XXXXXX)
                    vsrc="$vtmp/$(basename $vurl)"
                    echo "Fetching $vurl"
                    if command -v curl >/dev/null; then
                        curl -L -o "$vsrc" "$vurl"
                    elif command -v wget >/dev/null; then
                        wget -O "$vsrc" "$vurl"
                    else
                        "$GALAXY_PYTHON" -c "try:
        from urllib import urlretrieve
    except:
        from urllib.request import urlretrieve
    urlretrieve('$vurl', '$vsrc')"
                    fi
                    "$GALAXY_PYTHON" "$vsrc" "$GALAXY_VIRTUAL_ENV"
                    rm -rf "$vtmp"
                fi
            fi
        fi
    fi
    setup_gravity_state_dir
fi

# activate virtualenv or conda env, sets $GALAXY_VIRTUAL_ENV and $GALAXY_CONDA_ENV
setup_python

if [ $SET_VENV -eq 1 ] && [ -z "$VIRTUAL_ENV" ]; then
    echo "ERROR: A virtualenv cannot be found. Please create a virtualenv in $GALAXY_VIRTUAL_ENV, or activate one."
    exit 1
fi

: ${GALAXY_WHEELS_INDEX_URL:="https://wheels.galaxyproject.org/simple"}
: ${PYPI_INDEX_URL:="https://pypi.python.org/simple"}
: ${GALAXY_DEV_REQUIREMENTS:="./lib/galaxy/dependencies/dev-requirements.txt"}
if [ $REPLACE_PIP -eq 1 ]; then
    python -m pip install 'pip>=19.3'
fi

requirement_args="-r requirements.txt"
if [ $DEV_WHEELS -eq 1 ]; then
    requirement_args="-r ${GALAXY_DEV_REQUIREMENTS}"
fi

[ "$CI" = 'true' ] && export PIP_PROGRESS_BAR=off

if [ $FETCH_WHEELS -eq 1 ]; then
    pip install $requirement_args --index-url "${GALAXY_WHEELS_INDEX_URL}" --extra-index-url "${PYPI_INDEX_URL}"
    GALAXY_CONDITIONAL_DEPENDENCIES=$(PYTHONPATH=lib python -c "from __future__ import print_function; import galaxy.dependencies; print('\n'.join(galaxy.dependencies.optional('$GALAXY_CONFIG_FILE')))")
    if [ -n "$GALAXY_CONDITIONAL_DEPENDENCIES" ]; then
        if pip list --format=columns | grep "psycopg2[\(\ ]*2.7.3" > /dev/null; then
            echo "An older version of psycopg2 (non-binary, version 2.7.3) has been detected.  Galaxy now uses psycopg2-binary, which will be installed after removing psycopg2."
            pip uninstall -y psycopg2 psycopg2-binary
        fi
        echo "$GALAXY_CONDITIONAL_DEPENDENCIES" | pip install -r /dev/stdin --index-url "${GALAXY_WHEELS_INDEX_URL}" --extra-index-url "${PYPI_INDEX_URL}"
    fi
fi

# Install node if not installed
if [ -n "$VIRTUAL_ENV" ]; then
    if ! in_venv "$(command -v node)" || [ "$(node --version)" != "v${NODE_VERSION}" ]; then
        echo "Installing node into $VIRTUAL_ENV with nodeenv."
        if [ -d "${VIRTUAL_ENV}/lib/node_modules" ]; then
            echo "Removing old ${VIRTUAL_ENV}/lib/node_modules directory."
            rm -rf "${VIRTUAL_ENV}/lib/node_modules"
        fi
        nodeenv -n "$NODE_VERSION" -p
    fi
elif [ -n "$CONDA_DEFAULT_ENV" ] && [ -n "$CONDA_EXE" ]; then
    if ! in_conda_env "$(command -v node)"; then
        echo "Installing node into '$CONDA_DEFAULT_ENV' Conda environment with conda."
        $CONDA_EXE install --yes --override-channels --channel conda-forge --channel defaults --name "$CONDA_DEFAULT_ENV" nodejs="$NODE_VERSION"
    fi
fi

# Check client build state.
if [ $SKIP_CLIENT_BUILD -eq 0 ]; then
    if [ -f static/client_build_hash.txt ]; then
        # If git is not used and static/client_build_hash.txt is present, next
        # client rebuilds must be done manually by the admin
        if [ "$GIT_BRANCH" = "0" ]; then
            echo "Skipping Galaxy client build because git is not in use and the client build state cannot be compared against local changes.  If you have made local modifications, then manual client builds will be required.  See ./client/README.md for more information."
            SKIP_CLIENT_BUILD=1
        else
            # Check if anything has changed in client/ or visualization plugins since the last build
            if git diff --quiet "$(cat static/client_build_hash.txt)" -- client/ config/plugins/visualizations/; then
                echo "The Galaxy client build is up to date and will not be rebuilt at this time."
                SKIP_CLIENT_BUILD=1
            else
                echo "The Galaxy client is out of date and will be built now."
            fi
        fi
    else
        echo "The Galaxy client has not yet been built and will be built now."
    fi
else
    echo "The Galaxy client build is being skipped due to the SKIP_CLIENT_BUILD environment variable."
fi

# Build client if necessary.
if [ $SKIP_CLIENT_BUILD -eq 0 ]; then
    # Ensure dependencies are installed
    if [ -n "$VIRTUAL_ENV" ]; then
        if ! in_venv "$(command -v yarn)"; then
            echo "Installing yarn into $VIRTUAL_ENV with npm."
            npm install --global yarn
        fi
    elif [ -n "$CONDA_DEFAULT_ENV" ] && [ -n "$CONDA_EXE" ]; then
        if ! in_conda_env "$(command -v yarn)"; then
            echo "Installing yarn into '$CONDA_DEFAULT_ENV' Conda environment with conda."
            $CONDA_EXE install --yes --override-channels --channel conda-forge --channel defaults --name "$CONDA_DEFAULT_ENV" yarn
        fi
    else
        echo "WARNING: Galaxy client build needed but there is no virtualenv enabled. Build may fail."
    fi
    # We need galaxy config here, ensure it's set.
    set_galaxy_config_file_var
    # Set plugin path
    GALAXY_PLUGIN_PATH=$(python scripts/config_parse.py --setting=plugin_path --config-file="$GALAXY_CONFIG_FILE")
    # Build client
    cd client
    if yarn install $YARN_INSTALL_OPTS; then
        if ! (export GALAXY_PLUGIN_PATH="$GALAXY_PLUGIN_PATH"; yarn run build-production-maps;) then
            echo "ERROR: Galaxy client build failed. See ./client/README.md for more information, including how to get help."
            exit 1
        fi
    else
        echo "ERROR: Galaxy client dependency installation failed. See ./client/README.md for more information, including how to get help."
        exit 1
    fi
    cd -
fi
