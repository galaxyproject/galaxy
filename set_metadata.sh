#!/bin/sh

[ -d .venv ] && . .venv/bin/activate

cd `dirname $0`
python ./scripts/set_metadata.py $@
