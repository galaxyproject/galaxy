#!/bin/sh
set -e

usage() {
cat << EOF
Usage: ${0##*/} [-c] [-d]

Use pipenv to regenerate locked and hashed versions of Galaxy dependencies.
Use -c to automatically commit these changes (be sure you have no staged git
changes).
Use -d to rebuild with Pipenv from the galaxy/update-python-dependencies
container. This container can be built by running 'make' from the docker
subdirectory.

EOF
}

commit=0
docker=0
while getopts ":hcd" opt; do
    case "$opt" in
        c)
            commit=1
            ;;
        d)
            docker=1
            ;;
        h)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 1
            ;;
    esac
done

THIS_DIRECTORY="$(cd "$(dirname "$0")" > /dev/null && pwd)"
ENVS="flake8
default"

export PIPENV_IGNORE_VIRTUALENVS=1
for env in $ENVS; do
    cd "$THIS_DIRECTORY/$env"
    if [ "$docker" -eq 1 ]; then
        docker run -v "$(pwd):/working" -t 'galaxy/update-python-dependencies'
    else
        sh ../docker/docker_script.sh
    fi

    if ! grep '==' pinned-dev-requirements.txt ; then
        rm -f pinned-dev-requirements.txt
    fi
done

if [ "$commit" -eq 1 ]; then
	git add -u "$THIS_DIRECTORY"
	git commit -m "Rev and re-lock Galaxy dependencies"
fi
