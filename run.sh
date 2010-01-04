#!/bin/sh

cd `dirname $0`

CLEAN_PYTHON=`python ./scripts/check_python.py`

# explicitly attempt to fetch eggs before running
FETCH_EGGS=1
for arg in "$@"; do
    [ "$arg" = "--stop-daemon" ] && FETCH_EGGS=0; break
done
if [ $FETCH_EGGS -eq 1 ]; then
    $CLEAN_PYTHON ./scripts/check_eggs.py quiet
    if [ $? -ne 0 ]; then
        echo "Some eggs are out of date, attempting to fetch..."
        $CLEAN_PYTHON ./scripts/fetch_eggs.py
        if [ $? -eq 0 ]; then
            echo "Fetch successful."
        else
            echo "Fetch failed."
            exit 1
        fi
    fi
fi
$CLEAN_PYTHON ./scripts/paster.py serve universe_wsgi.ini $@
