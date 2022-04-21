#!/bin/sh

#######
# Use this script to manage Galaxy and Tool Shed Install migrations.
# (Use the legacy manage_db.sh script to manage Tool Shed migrations.)
#
# NOTE: If your database is empty OR is not under Alembic version control,
# use create_db.sh instead.
#
# We use branch labels to distinguish between the galaxy and the tool_shed_install models,
# so in most cases you'll need to identify the branch to which your command should be applied.
# Use these identifiers: `gxy` for galaxy, and `tsi` for tool_shed_install.
#
# To create a revision for galaxy:
# ./run_alembic.sh revision --head=gxy@head -m "your description"
#
# To create a revision for tool_shed_install:
# ./run_alembic.sh revision --head=tsi@head -m "your description"
#
# To upgrade:
# ./run_alembic.sh upgrade gxy@head  # upgrade gxy to head revision
# ./run_alembic.sh upgrade gxy@+1  # upgrade gxy to 1 revision above current
# ./run_alembic.sh upgrade [revision identifier]  # upgrade gxy to a specific revision
# ./run_alembic.sh upgrade [revision identifier]+1  # upgrade gxy to 1 revision above specific revision
# ./run_alembic.sh upgrade heads  # upgrade gxy and tsi to head revisions
#
# To downgrade:
# ./run_alembic.sh downgrade gxy@base  # downgrade gxy to base (empty db with empty alembic table)
# ./run_alembic.sh downgrade gxy@-1  # downgrade gxy to 1 revision below current
# ./run_alembic.sh downgrade [revision identifier]  # downgrade gxy to a specific revision
# ./run_alembic.sh downgrade [revision identifier]-1  # downgrade gxy to 1 revision below specific revision
#
# To pass a galaxy config file, use `--galaxy-config`
#
# You may also override the galaxy database url and/or the
# tool shed install database url, as well as the database_template
# and database_encoding configuration options with env vars:
# GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION=my-db-url ./run_alembic.sh ...
# GALAXY_INSTALL_CONFIG_OVERRIDE_DATABASE_CONNECTION=my-other-db-url ./run_alembic.sh ...
#
# For more options, see Alembic's documentation at https://alembic.sqlalchemy.org
#######

ALEMBIC_CONFIG='lib/galaxy/model/migrations/alembic.ini'

cd `dirname $0`

. ./scripts/common_startup_functions.sh

setup_python

find lib/galaxy/model/migrations/alembic -name '*.pyc' -delete
python ./scripts/migrate_db.py --config "$ALEMBIC_CONFIG" "$@"
