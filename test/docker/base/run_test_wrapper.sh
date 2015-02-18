#!/bin/bash
set -e

# TODO: switch on environment to boot mysql here...
if [ "$GALAXY_TEST_DATABASE_TYPE" = "postgres" ];
then
    su -c '/usr/lib/postgresql/9.3/bin/pg_ctl -o "-F" start -D /opt/galaxy/db' postgres
	sleep 3
    export GALAXY_TEST_DBURI="postgres://galaxy@localhost:5930/galaxy"
elif [ "$GALAXY_TEST_DATABASE_TYPE" = "mysql" ];
then
    sh /opt/galaxy/start_mysql.sh
    export GALAXY_TEST_DBURI="mysql://galaxy:galaxy@localhost/galaxy?unix_socket=/var/run/mysqld/mysqld.sock"
elif [ "$GALAXY_TEST_DATABASE_TYPE" = "sqlite" ];
then
    export GALAXY_TEST_DBURI="sqlite:////opt/galaxy/galaxy.sqlite"
else
	echo "Unknown database type"
	exit 1
fi
cd /galaxy
GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION="$GALAXY_TEST_DBURI" sh manage_db.sh upgrade
sh run_tests.sh $@
