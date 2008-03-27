#!/bin/sh

. ./scripts/get_python.sh
. ./setup_paths.sh

pyver=`$GALAXY_PYTHON -c 'import sys; print sys.version[:3]'`
export PYTHONPATH=$PYTHONPATH:eggs/py$pyver-noplatform/NoseHTML-0.2-py$pyver.egg

$GALAXY_PYTHON ./scripts/nosetests.py $@
