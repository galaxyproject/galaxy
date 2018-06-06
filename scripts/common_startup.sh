#!/bin/sh
set -e

SET_VENV=1
for arg in "$@"; do
    [ "$arg" = "--skip-venv" ] && SET_VENV=0
done

# Conda Python is in use, do not use virtualenv
if python -V 2>&1 | grep -q -e 'Anaconda' -e 'Continuum Analytics' ; then
    CONDA_ALREADY_INSTALLED=1
elif python -c 'import sys; print(sys.version.replace("\n", " "))' | grep -q -e 'packaged by conda-forge' ; then
    CONDA_ALREADY_INSTALLED=1
else
    CONDA_ALREADY_INSTALLED=0
fi

DEV_WHEELS=0
FETCH_WHEELS=1
CREATE_VENV=1
REPLACE_PIP=$SET_VENV
COPY_SAMPLE_FILES=1
SKIP_CLIENT_BUILD=${GALAXY_SKIP_CLIENT_BUILD:-0}

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
    config/migrated_tools_conf.xml.sample
    config/shed_tool_conf.xml.sample
    config/shed_tool_data_table_conf.xml.sample
    config/shed_data_manager_conf.xml.sample
    lib/tool_shed/scripts/bootstrap_tool_shed/user_info.xml.sample
    tool-data/shared/ucsc/builds.txt.sample
    tool-data/shared/ucsc/manual_builds.txt.sample
    static/welcome.html.sample
"

RMFILES="
    lib/pkg_resources.pyc
"

# return true if $1 is in $VIRTUAL_ENV else false
in_venv() {
    case $1 in
        $VIRTUAL_ENV*)
            return 0
            ;;
        ''|*)
            return 1
            ;;
    esac
}

if [ $COPY_SAMPLE_FILES -eq 1 ]; then
	# Create any missing config/location files
	for sample in $SAMPLES; do
		file=${sample%.sample}
	    if [ ! -f "$file" -a -f "$sample" ]; then
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
            # All non-release branches should build the client as necessary
            SKIP_CLIENT_BUILD=1
            ;;
        *)
            # Ensure nodeenv is installed
            DEV_WHEELS=1
            # SKIP_CLIENT_BUILD will default to false, but can be overridden by the command line argument
            ;;
    esac
else
    GIT_BRANCH=0
    DEV_WHEELS=1
fi

: ${GALAXY_VIRTUAL_ENV:=.venv}

if [ $SET_VENV -eq 1 -a $CREATE_VENV -eq 1 ]; then
    if [ ! -d "$GALAXY_VIRTUAL_ENV" ]
    then
        if [ $CONDA_ALREADY_INSTALLED -eq 1 ]; then
            echo "There is no existing Galaxy virtualenv and Conda is available, so we are skipping virtualenv creation.  Please be aware that this may cause missing dependencies."
            SET_VENV=0
        else
            # If .venv does not exist, and there is no conda available, attempt to create it.
            # Ensure Python is a supported version before creating .venv
            python ./scripts/check_python.py || exit 1
            if command -v virtualenv >/dev/null; then
                virtualenv -p "$(command -v python)" "$GALAXY_VIRTUAL_ENV"
            else
                vvers=13.1.2
                vurl="https://pypi.python.org/packages/source/v/virtualenv/virtualenv-${vvers}.tar.gz"
                vsha="aabc8ef18cddbd8a2a9c7f92bc43e2fea54b1147330d65db920ef3ce9812e3dc"
                vtmp=$(mktemp -d -t galaxy-virtualenv-XXXXXX)
                vsrc="$vtmp/$(basename $vurl)"
                # SSL certificates are not checked to prevent problems with messed
                # up client cert environments. We verify the download using a known
                # good sha256 sum instead.
                echo "Fetching $vurl"
                if command -v curl >/dev/null; then
                    curl --insecure -L -o "$vsrc" "$vurl"
                elif command -v wget >/dev/null; then
                    wget --no-check-certificate -O "$vsrc" "$vurl"
                else
                    python -c "import urllib; urllib.urlretrieve('$vurl', '$vsrc')"
                fi
                echo "Verifying $vsrc checksum is $vsha"
                python -c "import hashlib; assert hashlib.sha256(open('$vsrc', 'rb').read()).hexdigest() == '$vsha', '$vsrc: invalid checksum'"
                tar zxf "$vsrc" -C "$vtmp"
                python "$vtmp/virtualenv-$vvers/virtualenv.py" "$GALAXY_VIRTUAL_ENV"
                rm -rf "$vtmp"
            fi
        fi
    fi
fi

if [ $SET_VENV -eq 1 ]; then
    # If there is a .venv/ directory, assume it contains a virtualenv that we
    # should run this instance in.
    if [ -d "$GALAXY_VIRTUAL_ENV" ];
    then
        echo "Activating virtualenv at $GALAXY_VIRTUAL_ENV"
        . "$GALAXY_VIRTUAL_ENV/bin/activate"
        # Because it's a virtualenv, we assume $PYTHONPATH is unnecessary for
        # anything in the venv to work correctly, and having it set can cause
        # problems when there are conflicts with Galaxy's dependencies outside
        # the venv (e.g. virtualenv-burrito's pip and six).
        #
        # If you are skipping the venv setup we shall assume you know what
        # you're doing and will deal with any conflicts.
        unset PYTHONPATH
    fi

    if [ -z "$VIRTUAL_ENV" ]; then
        echo "ERROR: A virtualenv cannot be found. Please create a virtualenv in $GALAXY_VIRTUAL_ENV, or activate one."
        exit 1
    fi
fi

: ${GALAXY_WHEELS_INDEX_URL:="https://wheels.galaxyproject.org/simple"}
: ${PYPI_INDEX_URL:="https://pypi.python.org/simple"}
: ${GALAXY_DEV_REQUIREMENTS:="./lib/galaxy/dependencies/dev-requirements.txt"}
if [ $REPLACE_PIP -eq 1 ]; then
    pip install 'pip>=8.1'
fi

requirement_args="-r requirements.txt"
if [ $DEV_WHEELS -eq 1 ]; then
    requirement_args="$requirement_args -r ${GALAXY_DEV_REQUIREMENTS}"
fi

if [ $FETCH_WHEELS -eq 1 ]; then
    pip install $requirement_args --index-url "${GALAXY_WHEELS_INDEX_URL}" --extra-index-url "${PYPI_INDEX_URL}"
    GALAXY_CONDITIONAL_DEPENDENCIES=$(PYTHONPATH=lib python -c "import galaxy.dependencies; print('\n'.join(galaxy.dependencies.optional('$GALAXY_CONFIG_FILE')))")
    [ -z "$GALAXY_CONDITIONAL_DEPENDENCIES" ] || echo "$GALAXY_CONDITIONAL_DEPENDENCIES" | pip install -r /dev/stdin --index-url "${GALAXY_WHEELS_INDEX_URL}" --extra-index-url "${PYPI_INDEX_URL}"
fi

# Check client build state.
if [ $SKIP_CLIENT_BUILD -eq 0 ]; then
    if [ -f static/client_build_hash.txt ]; then
        # If git is not used and static/client_build_hash.txt is present, next
        # client rebuilds must be done manually by the admin
        if [ "$GIT_BRANCH" = "0" ]; then
            SKIP_CLIENT_BUILD=1
        else
            # Compare hash.
            githash=$(git rev-parse HEAD)
            statichash=$(cat static/client_build_hash.txt)
            if [ "$githash" = "$statichash" ]; then
                SKIP_CLIENT_BUILD=1
            else
                echo "The Galaxy client is out of date and will be built now."
            fi
        fi
    else
        echo "The Galaxy client has not yet been built and will be built now."
    fi
fi

# Build client if necessary.
if [ $SKIP_CLIENT_BUILD -eq 0 ]; then
    # Ensure dependencies are installed
    if [ -n "$VIRTUAL_ENV" ]; then
        if ! in_venv "$(command -v node)"; then
            echo "Installing node into $VIRTUAL_ENV with nodeenv."
            nodeenv -n 9.11.1 -p
        fi
        if ! in_venv "$(command -v yarn)"; then
            echo "Installing yarn into $VIRTUAL_ENV with npm."
            npm install --global yarn
        fi
    else
        echo "WARNING: Galaxy client build needed but there is no virtualenv enabled. Build may fail."
    fi

    # Build client
    if ! make client; then
        echo "ERROR: Galaxy client build failed. See ./client/README.md for more information, including how to get help."
        exit 1
    fi
fi
