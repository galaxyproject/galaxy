#!/bin/sh

### Run Galaxy using uwsgi.
###
### Compatibility options are implemented for the previous PasteScript based
### run.sh:
### --daemon: Daemonize, write pid to PID_FILE and log to LOG_FILE
### --stop-daemon: Shutdown daemond using PID_FILE
### --restart: Graceful reload using PID_FILE
###
### No special handling of --reload is done since it is already a uwsgi
### option but does something different than for paster. If you want
### this functionality you can provide the --py-auto-reload option. 
### But you probably don't want to do that. 
 
PID_FILE="${PID_FILE:-uwsgi.pid}"
LOG_FILE="${LOG_FILE:-uwsgi.log}"

cd "$(dirname "$0")"

# If there is a file that defines a shell environment specific to this
# instance of Galaxy, source the file.
if [ -z "$GALAXY_LOCAL_ENV_FILE" ];
then
    GALAXY_LOCAL_ENV_FILE='./config/local_env.sh'
fi

if [ -f $GALAXY_LOCAL_ENV_FILE ];
then
    . $GALAXY_LOCAL_ENV_FILE
fi

uwsgi_args="--master --pythonpath=lib"

# Pop args meant for common_startup.sh and translate any old paster style 
# args for uwsgi
while :
do
    case "$1" in
        --skip-eggs|--skip-wheels|--skip-samples|--dev-wheels|--no-create-venv|--no-replace-pip|--replace-pip)
            common_startup_args="$common_startup_args $1"
            shift
            ;;
        --skip-venv)
            skip_venv=1
            common_startup_args="$common_startup_args $1"
            shift
            ;;
        --stop-daemon)
            common_startup_args="$common_startup_args $1"
            uwsgi_args="$uwsgi_args --stop $PID_FILE"
            stop_daemon_arg_set=1
            shift
            ;;
        --restart)
            # --reload does a gracefull reload if multiple processes are
            # configured
            uwsgi_args="$uwsgi_args --reload $PID_FILE"
            daemon_or_restart_arg_set=1
            shift
            ;;
        --daemon)
            # --daemonize2 waits until after the application has loaded
            # to daemonize, thus it stops if any errors are found
            uwsgi_args="$uwsgi_args --daemonize2 $LOG_FILE --safe-pidfile $PID_FILE"
            daemon_or_restart_arg_set=1
            shift
            ;;
        --wait)
            wait_arg_set=1
            shift
            ;;
        "")
            break
            ;;
        *)
            uwsgi_args="$uwsgi_args $1"
            shift
            ;;
    esac
done

./scripts/common_startup.sh $common_startup_args || exit 1

# If there is a .venv/ directory, assume it contains a virtualenv that we
# should run this instance in.
GALAXY_VIRTUAL_ENV="${GALAXY_VIRTUAL_ENV:-.venv}"
if [ -d "$GALAXY_VIRTUAL_ENV" -a -z "$skip_venv" ];
then
    [ -n "$PYTHONPATH" ] && { echo 'Unsetting $PYTHONPATH'; unset PYTHONPATH; }
    echo "Activating virtualenv at $GALAXY_VIRTUAL_ENV"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

# If you are using --skip-venv we assume you know what you are doing but warn
# in case you don't.
[ -n "$PYTHONPATH" ] && echo 'WARNING: $PYTHONPATH is set, this can cause problems importing Galaxy dependencies'

python ./scripts/check_python.py || exit 1

if [ ! -z "$GALAXY_RUN_WITH_TEST_TOOLS" ];
then
    export GALAXY_CONFIG_OVERRIDE_TOOL_CONFIG_FILE="test/functional/tools/samples_tool_conf.xml"
    export GALAXY_CONFIG_ENABLE_BETA_WORKFLOW_MODULES="true"
    export GALAXY_CONFIG_OVERRIDE_ENABLE_BETA_TOOL_FORMATS="true"
fi

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
    echo 'ERROR: $GALAXY_RUN_ALL is no longer supported. Configure multiple processes with uwsgi'
    echo 'https://wiki.galaxyproject.org/Admin/Config/Performance/Scaling'
    exit 1
fi

# Look for uws
if [ -z "$skip_venv" -a -x $GALAXY_VIRTUAL_ENV/bin/uwsgi ]; then
    UWSGI=$GALAXY_VIRTUAL_ENV/bin/uwsgi
elif command -v uwsgi >/dev/null 2>&1; then
    UWSGI=uwsgi
else
    echo 'ERROR: Could not find uwsgi executable'
    exit 1
fi

$UWSGI --ini-paste $GALAXY_CONFIG_FILE $uwsgi_args 
