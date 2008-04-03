#!/bin/sh

# This script must be executed from the $UNIVERSE_HOME directory
# e.g., sh ./scripts/cleanup_datasets/update_metadata.sh

. ./scripts/get_python.sh
. ./setup_paths.sh

$GALAXY_PYTHON ./scripts/cleanup_datasets/update_metadata.py ./universe_wsgi.ini $@
