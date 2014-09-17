#!/bin/sh

cd `dirname $0`

# If there is a .venv/ directory, assume it contains a virtualenv that we
# should run this instance in.
if [ -d .venv ];
then
    . .venv/bin/activate
fi

python ./scripts/check_python.py
[ $? -ne 0 ] && exit 1

./scripts/common_startup.sh

if [ -n "$GALAXY_UNIVERSE_CONFIG_DIR" ]; then
    python ./scripts/build_universe_config.py "$GALAXY_UNIVERSE_CONFIG_DIR"
fi

if [ -z "$GALAXY_CONFIG_FILE" ]; then
    if [ -f universe_wsgi.ini ]; then
        GALAXY_CONFIG_FILE=universe_wsgi.ini
    elif [ -f config/galaxy.ini ]; then
        GALAXY_CONFIG_FILE=config/galaxy.ini
    else
        GALAXY_CONFIG_FILE=config/galaxy.ini.sample
    fi
    export GALAXY_CONFIG_FILE
fi

if [ -n "$GALAXY_RUN_ALL" ]; then
    servers=`sed -n 's/^\[server:\(.*\)\]/\1/  p' $GALAXY_CONFIG_FILE | xargs echo`
    daemon=`echo "$@" | grep -q daemon`
    if [ $? -ne 0 ]; then
        echo 'ERROR: $GALAXY_RUN_ALL cannot be used without the `--daemon` or `--stop-daemon` arguments to run.sh'
        exit 1
    fi
    for server in $servers; do
        echo "Handling $server with log file $server.log..."
        python ./scripts/paster.py serve $GALAXY_CONFIG_FILE --server-name=$server --pid-file=$server.pid --log-file=$server.log $@
    done
else
    python ./scripts/paster.py serve $GALAXY_CONFIG_FILE $@
fi
