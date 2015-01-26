#!/bin/sh

cd `dirname $0`/../..
# Make sure your config is at config/tool_shed.ini
# and that you specified toolshed_whoosh_index_dir in it.
python scripts/tool_shed/build_ts_whoosh_index.py config/tool_shed.ini
