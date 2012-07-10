#!/bin/sh

cd `dirname $0`/../..
python ./scripts/migrate_tools/migrate_tools.py 0003_tools.xml $@
