#!/bin/sh

THIS_DIRECTORY="$(dirname "$0")"
ENVS=(flake8 flake8_imports)

for env in "${ENVS[@]}"
do
        cd "$THIS_DIRECTORY/$env"
        pipenv lock
        pipenv lock -r > requirements.txt
done

git add -u "$THIS_DIRECTORY"
git commit -m "Rev and re-lock linting dependencies."
