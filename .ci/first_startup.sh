#!/bin/sh
case "$1" in
    galaxy|"")
        SCRIPT=./run.sh
        PORT=8080
        LOGFILE=galaxy.log
        GRAVITY_LOGFILE=database/gravity/log/gunicorn.log
        SUPERVISORD_LOGFILE=database/gravity/supervisor/supervisord.log
        ;;
    reports)
        SCRIPT=./run_reports.sh
        PORT=9001
        LOGFILE=reports_webapp.log
        ;;
    *)
        echo "ERROR: Unrecognized app"
        exit 1
        ;;
esac
TRIES=120
URL=http://localhost:$PORT
EXIT_CODE=1
i=0
echo "Testing for correct startup:"
$SCRIPT --daemon && \
    while [ "$i" -le $TRIES ]; do
        curl --max-time 1 "$URL" && EXIT_CODE=0 && break
        sleep 1
        i=$((i + 1))
    done
$SCRIPT --skip-wheels --stop-daemon
echo "exit code:$EXIT_CODE, showing startup log:"
if [ -f "$LOGFILE" ]; then
    cat "$LOGFILE"
elif [ ! -f "$LOGFILE" -a -f "$GRAVITY_LOGFILE" ]; then
    echo "Warning: $LOGFILE does not exist, showing gravity startup log instead"
    cat "$GRAVITY_LOGFILE"
elif [ ! -f "$LOGFILE" -a ! -f "$GRAVITY_LOGFILE" -a -f "$SUPERVISORD_LOGFILE" ]; then
    echo "Warning: $LOGFILE and $GRAVITY_LOGFILE do not exist, showing supervisord startup log instead"
    cat "$SUPERVISORD_LOGFILE"
else
    echo "ERROR: No log files found!"
    ls -lR database/gravity
fi
exit $EXIT_CODE
