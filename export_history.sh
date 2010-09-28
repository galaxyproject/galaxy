#!/bin/sh

cd `dirname $0`
python ./scripts/export_history.py $@
