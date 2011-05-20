#!/bin/sh

cd `dirname $0`/../..
python ./scripts/tool_shed/migrate_tools_to_repositories.py ./community_wsgi.ini >> ./scripts/tool_shed/migrate_tools_to_repositories.log
