#!/bin/sh

cd `dirname $0`
python scripts/galaxy_messaging/server/amqp_consumer.py --config-file=universe_wsgi.ini --http-server-section=server:main 2>&1