#!/bin/sh

# This script must be executed from the $UNIVERSE_HOME directory
# e.g., sh ./scripts/update_database/update_database_with_security_libraries.sh

. ./scripts/get_python.sh
. ./setup_paths.sh

$GALAXY_PYTHON ./scripts/update_database/update_database_with_security_libraries.py ./universe_wsgi.ini $@
