#!/bin/sh

cd `dirname $0`

python ./scripts/check_python.py
[ $? -ne 0 ] && exit 1

./scripts/copy_sample_files.sh

if [ -n "$GALAXY_UNIVERSE_CONFIG_DIR" ]; then
    python ./scripts/build_universe_config.py "$GALAXY_UNIVERSE_CONFIG_DIR"
fi

# explicitly attempt to fetch eggs before running
FETCH_EGGS=1
for arg in "$@"; do
    [ "$arg" = "--stop-daemon" ] && FETCH_EGGS=0; break
done
if [ $FETCH_EGGS -eq 1 ]; then
    python ./scripts/check_eggs.py -q
    if [ $? -ne 0 ]; then
        echo "Some eggs are out of date, attempting to fetch..."
        python ./scripts/fetch_eggs.py
        if [ $? -eq 0 ]; then
            echo "Fetch successful."
        else
            echo "Fetch failed."
            exit 1
        fi
    fi
fi

if [ -n "$GALAXY_RUN_ALL" ]; then
    servers=`sed -n 's/^\[server:\(.*\)\]/\1/  p' universe_wsgi.ini | xargs echo`
    daemon=`echo "$@" | grep -q daemon`
    if [ $? -ne 0 ]; then
        echo 'ERROR: $GALAXY_RUN_ALL cannot be used without the `--daemon` or `--stop-daemon` arguments to run.sh'
        exit 1
    fi
    for server in $servers; do
        echo "Handling $server with log file $server.log..."
        python ./scripts/paster.py serve universe_wsgi.ini --server-name=$server --pid-file=$server.pid --log-file=$server.log $@
    done
else
    python ./scripts/paster.py serve universe_wsgi.ini $@
fi
