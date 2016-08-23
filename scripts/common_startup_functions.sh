#!/bin/sh

uwsgi_args="--master --pythonpath=lib"

parse_common_args() {
    INITIALIZE_TOOL_DEPENDENCIES=1
    # Pop args meant for common_startup.sh
    while :
    do
        case "$1" in
            --skip-eggs|--skip-wheels|--skip-samples|--dev-wheels|--no-create-venv|--no-replace-pip|--replace-pip)
                common_startup_args="$common_startup_args $1"
                shift
                ;;
            --skip-tool-dependency-initialization)
                INITIALIZE_TOOL_DEPENDENCIES=0
                shift
                ;;
            --skip-venv)
                skip_venv=1
                common_startup_args="$common_startup_args $1"
                shift
                ;;
            --stop-daemon)
                common_startup_args="$common_startup_args $1"
                paster_args="$paster_args $1"
                uwsgi_args="$uwsgi_args --stop $PID_FILE"
                stop_daemon_arg_set=1
                shift
                ;;
            --restart|restart)
                if [ "$1" = "--restart" ]
                then
                    paster_args="$paster_args restart"
                else
                    paster_args="$paster_args $1"
                fi
                uwsgi_args="$uwsgi_args --reload $PID_FILE"
                daemon_or_restart_arg_set=1
                shift
                ;;
            --daemon)
                paster_args="$paster_args $1"
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
                paster_args="$paster_args $1"
                uwsgi_args="$uwsgi_args $1"
                shift
                ;;
        esac
    done
}

run_common_start_up() {
    ./scripts/common_startup.sh $common_startup_args || exit 1
}

setup_python() {
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
}

find_uwsgi() {
    # Look for uwsgi
    if [ -z "$skip_venv" -a -x $GALAXY_VIRTUAL_ENV/bin/uwsgi ]; then
        UWSGI=$GALAXY_VIRTUAL_ENV/bin/uwsgi
    elif command -v uwsgi >/dev/null 2>&1; then
        UWSGI=uwsgi
    else
        echo 'ERROR: Could not find uwsgi executable'
        exit 1
    fi
}

find_server() {
    server_config="$1"
    server_config_style="ini-paste"
    default_webserver="paste"
    case "$server_config" in
        *.y*ml*)
            server_config_style="yaml"
            default_webserver="uwsgi"  # paste incapable of this
            ;;
    esac

    APP_WEBSERVER=${APP_WEBSERVER:-$default_webserver}
    if [ "$APP_WEBSERVER" = "uwsgi" ];
    then
        # Look for uwsgi
        if [ -z "$skip_venv" -a -x $GALAXY_VIRTUAL_ENV/bin/uwsgi ]; then
            UWSGI=$GALAXY_VIRTUAL_ENV/bin/uwsgi
        elif command -v uwsgi >/dev/null 2>&1; then
            UWSGI=uwsgi
        else
            echo 'ERROR: Could not find uwsgi executable'
            exit 1
        fi
        run_server="$UWSGI"
        server_args="--$server_config_style $server_config $uwsgi_args"
    else
        run_server="python"
        server_args="./scripts/paster.py serve $server_config $paster_args --pid-file $PID_FILE --log-file $LOG_FILE $paster_args"
    fi
}
