#!/bin/sh

#######
# Database schema migration operaions via alembic's CLI runner.
# Retrieves relevant configuration values and invokes the Alembic CLI runner.
#
# To pass a galaxy config file, use `--galaxy-config` 
# (NOTE: the -c option is used by alembic's CLI runner for passing its own config file, alembic.ini)
# 
# You may also override the galaxy database url and/or the
# tool shed install database url, as well as the database_template
# and database_encoding configuration options with env vars:
# GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION=my-db-url ./scripts/run_alembic.py ...
# GALAXY_INSTALL_CONFIG_OVERRIDE_DATABASE_CONNECTION=my-other-db-url ./scripts/run_alembic.py ...
# 
# For help, run `sh run_alembic.sh -h`. 
#
# Further information:
# Galaxy migration documentation: lib/galaxy/model/migrations/README.md
# Alembic documentation: https://alembic.sqlalchemy.org
#######

cd "$(dirname "$0")" || exit

cd ..

. ./scripts/common_startup_functions.sh

setup_python

python scripts/run_alembic.py "$@"
