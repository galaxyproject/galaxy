#!/bin/bash

userid=`id -un`;
if [ "$userid" != "root" ];
then
  echo "Must run this script as root";
  exit;
fi

move_location="/root/universe_wsgi.ini"
GALAXY_CONFIG_FILE=universe_wsgi.ini
mv $GALAXY_CONFIG_FILE $move_location

chown -R galaxyuser ../galaxy-dist
chgrp -R galaxy ../galaxy-dist
chmod a-w -R ../galaxy-dist
chmod a+rX -R ../galaxy-dist
find ../galaxy-dist -type d -exec chmod g-s {} \;
chmod u+w -R ../galaxy-dist

#chmod g+rwX -R ../galaxy-dist
#find ../galaxy-dist -type d -exec chmod g+s {} \;
#chmod a+rX -R ../galaxy-dist
#chmod o-w -R ../galaxy-dist
#chmod o-rwx universe_wsgi.* 

chown galaxyuser $move_location
chgrp galaxy $move_location
chmod a-rwx $move_location
chmod u+rw $move_location
mv $move_location $GALAXY_CONFIG_FILE

sed -e '/id_secret/d' -e '/database_connection/d' universe_wsgi.ini > safe_universe_wsgi.ini
chown galaxyuser safe_universe_wsgi.ini
chgrp galaxy safe_universe_wsgi.ini
chmod a-w safe_universe_wsgi.ini
chmod a+rX safe_universe_wsgi.ini
chmod u+w safe_universe_wsgi.ini

