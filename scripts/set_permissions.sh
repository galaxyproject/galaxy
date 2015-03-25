#!/bin/bash
chown -R galaxyuser ../galaxy-dist
chgrp -R galaxy ../galaxy-dist
chmod g+rwX -R ../galaxy-dist
find ../galaxy-dist -type d -exec chmod g+s {} \;
chmod a+rX -R ../galaxy-dist
chmod o-w -R ../galaxy-dist
chmod o-rwx universe_wsgi.* 
sed -e '/id_secret/d' -e '/database_connection/d' universe_wsgi.ini > safe_universe_wsgi.ini
chmod a+rX safe_universe_wsgi.ini

