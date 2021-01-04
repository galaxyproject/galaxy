#!/bin/bash
set -e

if [ -n "$USE_SELENIUM" ]; then
    # Start Selenium.
    sudo -E -H -u seluser /opt/bin/entry_point.sh &
fi

echo "Deleting galaxy user - it may not exist and this is fine."
deluser galaxy || true

: "${GALAXY_TEST_UID:=1}"
: "${GALAXY_VIRTUAL_ENV:=/galaxy_venv}"

echo "Creating galaxy group with gid $GALAXY_TEST_UID - it may already exist and this is fine."
groupadd -r galaxy -g "$GALAXY_TEST_UID" || true
echo "Creating galaxy user with uid $GALAXY_TEST_UID - it may already exist and this is fine."
useradd -u $GALAXY_TEST_UID -r -g galaxy -d /home/galaxy -c "Galaxy User" galaxy -s /bin/bash || true
echo "Setting galaxy user password - the operation may fail."
echo "galaxy:galaxy" | chpasswd || true
chown -R "$GALAXY_TEST_UID:$GALAXY_TEST_UID" "$GALAXY_VIRTUAL_ENV"

: "${GALAXY_TEST_DATABASE_TYPE:=postgres}"
if [ "$GALAXY_TEST_DATABASE_TYPE" = "postgres" ]; then
    echo "Starting postgres and then sleeping for 3 seconds"
    su -c '/usr/lib/postgresql/10/bin/pg_ctl -o "-F" start -D /opt/galaxy/db' postgres
    sleep 3
    GALAXY_TEST_INSTALL_DB_MERGED="true"
    GALAXY_TEST_DBURI="postgresql://root@localhost:5930/galaxy?client_encoding=utf8"
    TOOL_SHED_TEST_DBURI="postgresql://root@localhost:5930/toolshed?client_encoding=utf8"
    export GALAXY_CONFIG_OVERRIDE_DATABASE_ENCODING="UTF-8"
elif [ "$GALAXY_TEST_DATABASE_TYPE" = "sqlite" ]; then
    GALAXY_TEST_INSTALL_DB_MERGED="true"
    GALAXY_TEST_DBURI="sqlite:////opt/galaxy/galaxy.sqlite"
    TOOL_SHED_TEST_DBURI="sqlite:////opt/galaxy/toolshed.sqlite"
    chown -R "$GALAXY_TEST_UID:$GALAXY_TEST_UID" /opt/galaxy
else
    echo "Unknown database type '$GALAXY_TEST_DATABASE_TYPE'"
    exit 1
fi
export GALAXY_TEST_DBURI
export TOOL_SHED_TEST_DBURI
export GALAXY_TEST_INSTALL_DB_MERGED

cd /galaxy

echo "Running common startup for updated dependencies (if any)"
sudo -E -H -u "#${GALAXY_TEST_UID}" ./scripts/common_startup.sh --dev-wheels || { echo "common_startup.sh failed"; exit 1; }

# Ensure Selenium is running before starting tests.
if [ -n "$USE_SELENIUM" ]; then
    while ! curl -s "http://localhost:4444";
    do
        printf "."
        sleep 4;
    done;
    GALAXY_TEST_SELENIUM_REMOTE=1
    GALAXY_TEST_SELENIUM_REMOTE_HOST=localhost
    GALAXY_TEST_SELENIUM_REMOTE_PORT=4444

    export GALAXY_TEST_SELENIUM_REMOTE
    export GALAXY_TEST_SELENIUM_REMOTE_HOST
    export GALAXY_TEST_SELENIUM_REMOTE_PORT
fi

if [ -z "$GALAXY_NO_TESTS" ]; then
    sudo -E -H -u "#${GALAXY_TEST_UID}" ./run_tests.sh --skip-common-startup $@
else
    GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION="$GALAXY_TEST_DBURI"
    TOOL_SHED_CONFIG_OVERRIDE_DATABASE_CONNECTION="$TOOL_SHED_TEST_DBURI"
    : "${GALAXY_CONFIG_MASTER_API_KEY:=testmasterapikey}"
    # This is a path baked inside of Docker it seems, so we should support both ini and
    # YAML for some time.
    : "${GALAXY_CONFIG_FILE:=config/galaxy.ini.sample}"
    if [ ! -f "$GALAXY_CONFIG_FILE" ]; then
        GALAXY_CONFIG_FILE=config/galaxy.yml.sample
    fi
    TOOL_SHED_CONFIG_FILE=${GALAXY_CONFIG_FILE:-config/tool_shed.ini.sample}
    if [ ! -f "$TOOL_SHED_CONFIG_FILE" ]; then
        TOOL_SHED_CONFIG_FILE=config/tool_shed.yml.sample
    fi
    GALAXY_CONFIG_CHECK_MIGRATE_TOOLS=false
    : "${GALAXY_CONFIG_JOB_CONFIG_FILE:=config/job_conf.xml.sample}"
    : "${GALAXY_CONFIG_FILE_PATH:=/tmp/gx1}"
    : "${GALAXY_CONFIG_NEW_FILE_PATH:=/tmp/gxtmp}"

    export GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION
    export TOOL_SHED_CONFIG_OVERRIDE_DATABASE_CONNECTION
    export GALAXY_CONFIG_MASTER_API_KEY
    export GALAXY_CONFIG_FILE
    export TOOL_SHED_CONFIG_FILE
    export GALAXY_CONFIG_CHECK_MIGRATE_TOOLS
    export GALAXY_CONFIG_JOB_CONFIG_FILE
    export GALAXY_CONFIG_FILE_PATH
    export GALAXY_CONFIG_NEW_FILE_PATH

    sh run.sh $@
fi
