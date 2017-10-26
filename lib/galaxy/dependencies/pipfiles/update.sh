#!/bin/sh

THIS_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENVS=(default develop)

for env in "${ENVS[@]}"
do
        cd "$THIS_DIRECTORY/$env"
        pipenv lock
        pipenv lock -r > pinned-hashed-requirements.txt
        sed 's/--hash[^[:space:]]*//g' pinned-hashed-requirements.txt > pinned-requirements.txt
done
