#!/bin/sh
case "$1" in
    galaxy|"")
        SCRIPT=./run.sh
        PORT=8080
        LOGFILE=galaxy.log
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
cat "$LOGFILE"
exit $EXIT_CODE
