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

servers=`sed -n 's/^\[server:\(.*\)\]/\1/  p' $GALAXY_CONFIG_FILE | xargs echo`
for server in $servers; do
    # If there's a pid
    if [ -e $server.pid ]; then
        # Then kill it
        echo "Killing $server"
        pid=`cat $server.pid`
        kill $pid
    else
        # Otherwise just continue
        echo "$server not running"
    fi
    # Start the server (and background) (should this be nohup'd?)
    python ./scripts/paster.py serve $GALAXY_CONFIG_FILE --server-name=$server --pid-file=$server.pid --log-file=$server.log --daemon $@
    while true; do
        sleep 1
        printf "."
        # Grab the current pid from the pid file
        if ! current_pid_in_file=$(cat $server.pid); then
            echo "A Galaxy process died, interrupting" >&2
            exit 1
        fi
        # Search for all pids in the logs and tail for the last one
        latest_pid=`egrep '^Starting server in PID [0-9]+\.$' $server.log -o | sed 's/Starting server in PID //g;s/\.$//g' | tail -n 1`
        # If they're equivalent, then the current pid file agrees with our logs
        # and we've succesfully started
        [ -n "$latest_pid" ] && [ $latest_pid -eq $current_pid_in_file ] && break
    done
    echo
done
