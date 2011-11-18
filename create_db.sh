#!/bin/sh

cd `dirname $0`
python ./scripts/create_db.py $@
