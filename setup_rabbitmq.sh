#!/bin/sh

cd `dirname $0`
python scripts/galaxy_messaging/server/setup_rabbitmq.py universe_wsgi.ini