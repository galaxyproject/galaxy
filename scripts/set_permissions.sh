#!/bin/bash

scripts_dir=`dirname $0`
path_to_galaxy="$scripts_dir/.."
GALAXY_CONFIG_FILE="${path_to_galaxy}/universe_wsgi.ini"
move_location="/root/universe_wsgi.ini"
daemon_username="galaxyuser"
daemon_groupname="galaxy"

userid=`id -un`;
if [ "$userid" != "root" ];
then
  echo "Must run this script as root";
  exit;
fi

cd $path_to_galaxy
mv $GALAXY_CONFIG_FILE $move_location

chown -R ${daemon_username}:${daemon_groupname} ${path_to_galaxy}
chmod a-w -R ${path_to_galaxy}
chmod a+rX -R ${path_to_galaxy}
find ${path_to_galaxy} -type d -exec chmod g-s {} \;
chmod u+w -R ${path_to_galaxy}

#chmod g+rwX -R ${path_to_galaxy}
#find ${path_to_galaxy} -type d -exec chmod g+s {} \;
#chmod a+rX -R ${path_to_galaxy}
#chmod o-w -R ${path_to_galaxy}
#chmod o-rwx universe_wsgi.* 

chown ${daemon_username}:${daemon_groupname} $move_location
chmod a-rwx $move_location
chmod u+rw $move_location
mv $move_location $GALAXY_CONFIG_FILE

sed -e '/id_secret/d' -e '/database_connection/d' -e '/amqp_internal_connection/d' universe_wsgi.ini > safe_universe_wsgi.ini
chown ${daemon_username}:${daemon_groupname} safe_universe_wsgi.ini
chmod a-w safe_universe_wsgi.ini
chmod a+rX safe_universe_wsgi.ini
chmod u+w safe_universe_wsgi.ini

