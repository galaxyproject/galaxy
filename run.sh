#!/bin/sh

source setup_paths.sh

# Create directories
CREATE_DIRS="
$UNIVERSE_HOME/database/$CREATE_DIR/files
$UNIVERSE_HOME/database/$CREATE_DIR/tmp
"

for CREATE_DIR in $CREATE_DIRS; do
    if [ ! -d $CREATE_DIR -o ! -h $CREATE_DIR ]; then
        mkdir -p $CREATE_DIR
    fi
done

python2.4 ./scripts/paster.py serve universe_wsgi.ini $@
