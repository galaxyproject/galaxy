#!/bin/sh

parse_common_args() {
    # Pop args meant for common_startup.sh
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
                paster_args="$paster_args $1"
                stop_daemon_arg_set=1
                shift
                ;;
            --daemon|--restart|restart)
                if [ "$1" = "--restart" ]
                then
                    paster_args="$paster_args restart"
                else
                    paster_args="$paster_args $1"
                fi

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
