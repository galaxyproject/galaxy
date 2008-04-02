#!/bin/sh

. ./scripts/get_python.sh
. ./setup_paths.sh

pyver=`$GALAXY_PYTHON -c 'import sys; print sys.version[:3]'`
PYTHONPATH=$PYTHONPATH:eggs/py$pyver-noplatform/NoseHTML-0.2-py$pyver.egg
export PYTHONPATH

$GALAXY_PYTHON ./scripts/nosetests.py $@
