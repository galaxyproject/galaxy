#!/bin/sh

cd `dirname $0`
python -ES ./scripts/manage_db.py $@
