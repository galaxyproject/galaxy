#!/bin/sh

cd `dirname $0`

# explicitly attempt to fetch eggs before running
FETCH_EGGS=1
for arg in "$@"; do
    [ "$arg" = "--stop-daemon" ] && FETCH_EGGS=0; break
done
if [ $FETCH_EGGS -eq 1 ]; then
    python ./scripts/check_eggs.py quiet
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
python ./scripts/paster.py serve universe_wsgi.ini $@
