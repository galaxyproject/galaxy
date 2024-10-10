#!/bin/sh
set -e

show_help () {
    echo "Usage:  $0 -g GALAXY_DIR [-p PORT] [-e TOX_ENV] [-t BIOBLEND_TESTS] [-r GALAXY_REV] [-c]

  Run tests for BioBlend. Useful for Continuous Integration testing.
  *Please note* that this script overwrites the main.pid file and appends to the
  main.log file inside the specified Galaxy directory (-g).

Options:
  -g GALAXY_DIR
      Path of the local Galaxy git repository.
  -p PORT
      Port to use for the Galaxy server. Defaults to 8080.
  -e TOX_ENV
      Work against specified tox environments. Defaults to py38.
  -t BIOBLEND_TESTS
      Subset of tests to run, e.g.
      'tests/TestGalaxyObjects.py::TestHistory::test_create_delete' . Defaults
      to all tests.
  -r GALAXY_REV
      Branch or commit of the local Galaxy git repository to checkout.
  -v GALAXY_PYTHON
      Python to use for the Galaxy virtual environment.
  -c
      Force removal of the temporary directory created for Galaxy, even if some
      test failed."
}

get_abs_dirname () {
    # $1 : relative dirname
    cd "$1" && pwd
}

e_val=py38
GALAXY_PORT=8080
while getopts 'hcg:e:p:t:r:v:' option; do
    case $option in
        h) show_help
           exit;;
        c) c_val=1;;
        g) GALAXY_DIR=$(get_abs_dirname "$OPTARG");;
        e) e_val=$OPTARG;;
        p) GALAXY_PORT=$OPTARG;;
        t) t_val=$OPTARG;;
        r) r_val=$OPTARG;;
        v) GALAXY_PYTHON=$OPTARG;;
        *) show_help
           exit 1;;
    esac
done

if [ -z "$GALAXY_DIR" ]; then
    echo "Error: missing -g value."
    show_help
    exit 1
fi

# Install BioBlend
BIOBLEND_DIR=$(get_abs_dirname "$(dirname "$0")")
if ! command -v tox >/dev/null; then
    cd "${BIOBLEND_DIR}"
    if [ ! -d .venv ]; then
        virtualenv -p python3 .venv
    fi
    . .venv/bin/activate
    python3 -m pip install --upgrade "tox>=1.8.0"
fi

# Setup Galaxy version
cd "${GALAXY_DIR}"
if [ -n "${r_val}" ]; then
    # Update repository (may change the sample files or the list of eggs)
    git fetch
    git checkout "${r_val}"
    if git show-ref -q --verify "refs/heads/${r_val}" 2>/dev/null; then
        # ${r_val} is a branch
        export GALAXY_VERSION=${r_val}
        git pull --ff-only
    fi
else
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    case $BRANCH in
        dev | release_*)
            export GALAXY_VERSION=$BRANCH
            ;;
    esac
fi

# Setup Galaxy virtualenv
if [ -n "${GALAXY_PYTHON}" ]; then
    if [ ! -d .venv ]; then
        virtualenv -p "${GALAXY_PYTHON}" .venv
    fi
    export GALAXY_PYTHON
fi

# Setup Galaxy master API key and admin user
TEMP_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'mytmpdir')
echo "Created temporary directory $TEMP_DIR"
mkdir "${TEMP_DIR}/config" "${TEMP_DIR}/database"
printf "<?xml version=\"1.0\"?>\n<toolbox tool_path=\"%s\">\n</toolbox>\n" "$TEMP_DIR/shed_tools" > "$TEMP_DIR/config/shed_tool_conf.xml"
# Export BIOBLEND_ environment variables to be used in BioBlend tests
BIOBLEND_GALAXY_MASTER_API_KEY=$(LC_ALL=C tr -dc A-Za-z0-9 < /dev/urandom | head -c 32)
export BIOBLEND_GALAXY_MASTER_API_KEY
export BIOBLEND_GALAXY_USER_EMAIL="${USER}@localhost.localdomain"
DATABASE_CONNECTION=${DATABASE_CONNECTION:-"sqlite:///${TEMP_DIR}/database/universe.sqlite?isolation_level=IMMEDIATE"}
# Update psycopg2 requirement to a version that doesn't use 2to3 for Galaxy release 19.05, see https://github.com/psycopg/psycopg2/issues/1419
sed -i.bak -e 's/psycopg2-binary==2.7.4/psycopg2-binary==2.8.4/' lib/galaxy/dependencies/conditional-requirements.txt
# Start Galaxy and wait for successful server start
export GALAXY_SKIP_CLIENT_BUILD=1
if grep -q wait_arg_set run.sh ; then
    # Galaxy 22.01 or earlier.
    # Export GALAXY_CONFIG_FILE environment variable to be used by run_galaxy.sh
    export GALAXY_CONFIG_FILE="${TEMP_DIR}/config/galaxy.ini"
    eval "echo \"$(cat "${BIOBLEND_DIR}/tests/template_galaxy.ini")\"" > "${GALAXY_CONFIG_FILE}"
    GALAXY_RUN_ALL=1 "${BIOBLEND_DIR}/run_galaxy.sh" --daemon --wait
else
    # Galaxy is controlled via gravity, paste/uwsgi are replaced by gunicorn
    # and the `--wait` option does not work any more.
    # Export GALAXY_CONFIG_FILE environment variable to be used by run.sh
    export GALAXY_CONFIG_FILE="${TEMP_DIR}/config/galaxy.yml"
    if [ -f test/functional/tools/samples_tool_conf.xml ]; then
        # Galaxy 22.05 or earlier
        TEST_TOOLS_CONF_FILE=test/functional/tools/samples_tool_conf.xml
    else
        TEST_TOOLS_CONF_FILE=test/functional/tools/sample_tool_conf.xml
    fi
    eval "echo \"$(cat "${BIOBLEND_DIR}/tests/template_galaxy.yml")\"" > "${GALAXY_CONFIG_FILE}"
    export GRAVITY_STATE_DIR="${TEMP_DIR}/database/gravity"
    ./run.sh --daemon
    if ! .venv/bin/galaxyctl -h > /dev/null; then
        echo 'galaxyctl status not working'
        exit 1
    fi
    while true; do
        sleep 1
        if .venv/bin/galaxyctl status | grep -q 'gunicorn.*RUNNING'; then
            break
        else
            echo 'gunicorn not running yet'
        fi
    done
    while true; do
        sleep 1
        if grep -q "[Ss]erving on http://127.0.0.1:${GALAXY_PORT}" "${GRAVITY_STATE_DIR}/log/gunicorn.log"; then
            break
        else
            echo 'Galaxy not serving yet'
        fi
    done
fi
export BIOBLEND_GALAXY_URL=http://localhost:${GALAXY_PORT}

# Run the tests
cd "${BIOBLEND_DIR}"
set +e  # don't stop the script if tox fails
if [ -n "${t_val}" ]; then
    tox -e "${e_val}" -- "${t_val}"
else
    tox -e "${e_val}"
fi
exit_code=$?

# Stop Galaxy
echo 'Stopping Galaxy'
cd "${GALAXY_DIR}"
if grep -q wait_arg_set run.sh ; then
    GALAXY_RUN_ALL=1 "${BIOBLEND_DIR}/run_galaxy.sh" --daemon stop
else
    ./run.sh --daemon stop
fi
# Remove temporary directory if -c is specified or if all tests passed
if [ -n "${c_val}" ] || [ $exit_code -eq 0 ]; then
    rm -rf "$TEMP_DIR"
fi
exit $exit_code