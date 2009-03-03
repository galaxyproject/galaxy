#!/bin/sh

cd `dirname $0`
python -ES ./scripts/set_metadata.py $@
