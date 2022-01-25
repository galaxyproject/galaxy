#!/bin/sh

#######
# The purpose of this script is to preserve the legacy interface provided by
# manage_db.sh, which was a thin wrapper around SQLAlchemy Migrate. Unless you
# need to use the legacy interface, to manage migrations of the "galaxy" and
# "install" databases, you are encouraged to use run_alembic.sh directly and
# take advantage of Alembic's command line options.
#
# Use this script to upgrade or downgrade your database.
# Database options: galaxy (default), install, tool_shed
# To pass a galaxy config file, you may use `-c|--config|--config-file your-config-file`

# To upgrade or downgrade to some version X:
# sh manage_db.sh [upgrade|downgrade] --version=X [tool_shed|install|galaxy]
#
# You may also skip the version argument when upgrading, in which case the database
# will be upgraded to the latest version.
#
# Example 1: upgrade "galaxy" database to version "abc123" using default config:
# sh manage_db.sh upgrade --version=xyz567
#
# Example 2: downgrade "install" database to version "xyz789" passing config file "mygalaxy.yml":
# sh manage_db.sh downgrade --version=abc123 -c mygalaxy.yml install
#
# Example 3: upgrade "galaxy" database to latest version using defualt config:
# sh manage_db.sh upgrade
#
# (Note: Tool Shed migrations use the legacy migrations system, so we check the
# last argument (the database) to invoke the appropriate script. Therefore, if
# you don't specify the database (galaxy is used by default) and pass a config
# file, your config file should not be named `tool_shed`.)
#######

ALEMBIC_CONFIG='lib/galaxy/model/migrations/alembic.ini'

cd `dirname $0`

. ./scripts/common_startup_functions.sh

setup_python

for i; do :; done
if [ "$i" == "tool_shed" ]; then
    python ./scripts/migrate_toolshed_db.py $@ tool_shed
else
    find lib/galaxy/model/migrations/alembic -name '*.pyc' -delete
    python ./scripts/manage_db_adapter.py --alembic-config "$ALEMBIC_CONFIG" "$@"
fi
