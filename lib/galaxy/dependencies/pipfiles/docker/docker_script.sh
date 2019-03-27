#!/bin/sh

pipenv lock -v
pipenv lock -r > pinned-requirements.txt
pipenv lock -r --dev > pinned-dev-requirements.txt
