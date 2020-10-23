#!/bin/bash
# Prepare
python -m venv .venv

source ".venv/bin/activate" # activate virtualenv
pip install -r lib/galaxy/dependencies/dev-requirements.txt -r requirements.txt  &> /dev/null
python test/manual/test_parser.py