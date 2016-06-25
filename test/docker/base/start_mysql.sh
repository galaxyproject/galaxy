#!/bin/bash
set -e

MYSQL_USER=galaxy
MYSQL_PASSWORD=galaxy
MYSQL_DATABASE=galaxy
SHED_MYSQL_DATABASE=toolshed

mkdir -p /var/lib/mysql
chown -R mysql:mysql /var/lib/mysql

# Derived from
# https://github.com/docker-library/mysql/blob/master/5.7/docker-entrypoint.sh

DATADIR="$(mysqld --verbose --help 2>/dev/null | awk '$1 == "datadir" { print $2; exit }')"

tempSqlFile='/tmp/mysql-first-time.sql'
cat > "$tempSqlFile" <<-EOSQL
	DELETE FROM mysql.user ;
	CREATE USER 'root'@'%' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}' ;
	GRANT ALL ON *.* TO 'root'@'%' WITH GRANT OPTION ;
	DROP DATABASE IF EXISTS test ;
EOSQL

if [ "$MYSQL_DATABASE" ]; then
    echo "CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\` ;" >> "$tempSqlFile"
fi

if [ "$SHED_MYSQL_DATABASE" ]; then
    echo "CREATE DATABASE IF NOT EXISTS \`$SHED_MYSQL_DATABASE\` ;" >> "$tempSqlFile"
fi

if [ "$MYSQL_USER" -a "$MYSQL_PASSWORD" ]; then
    echo "CREATE USER '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD' ;" >> "$tempSqlFile"

    if [ "$MYSQL_DATABASE" ]; then
        echo "GRANT ALL ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%' ;" >> "$tempSqlFile"
    fi
    if [ "$SHED_MYSQL_DATABASE" ]; then
        echo "GRANT ALL ON \`$SHED_MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%' ;" >> "$tempSqlFile"
    fi
fi

echo 'FLUSH PRIVILEGES ;' >> "$tempSqlFile"

mysqld_safe --init-file="$tempSqlFile" &
sleep 5