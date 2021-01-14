#!/bin/sh

pipenv lock -v
pipenv lock -r > pinned-requirements.txt
pipenv lock -r --dev-only > pinned-dev-requirements.txt
