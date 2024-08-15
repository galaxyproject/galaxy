#!/bin/sh

cd "$(dirname "$0")"

. ./scripts/common_startup_functions.sh

setup_python

python ./scripts/check_model.py "$@"

[ $? -ne 0 ] && exit 1;
exit 0;
