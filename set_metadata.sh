#!/bin/sh

cd `dirname $0`
`python ./scripts/check_python.py` ./scripts/set_metadata.py $@
