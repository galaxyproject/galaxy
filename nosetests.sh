#!/bin/sh

source setup_paths.sh

export PYTHONPATH=$PYTHONPATH:eggs/NoseHTML-0.2-py2.4.egg

python2.4 ./scripts/nosetests.py $@
