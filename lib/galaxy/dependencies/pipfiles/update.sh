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
        pipenv lock -v
        pipenv lock -r > pinned-requirements.txt
        pipenv lock -r --dev > pinned-dev-requirements.txt
    fi

    # Strip out hashes and trailing whitespace for unhashed version
    # of this requirements file, needed for pipenv < 11.1.2
    sed -i.raw.orig -e 's/--hash[^[:space:]]*//g' -e 's/[[:space:]]*$//' pinned-requirements.txt pinned-dev-requirements.txt
    # Fix oscillating environment markers
    sed -i.orig -e "s/^\(azure-storage-nspkg==[^ ;]\{1,\}\).*$/\1/" \
                -e "s/^\(cffi==[^ ;]\{1,\}\).*$/\1/" \
                -e "s/^\(cmd2==[^ ;]\{1,\}\).*$/\1/" \
                -e "s/^\(configparser==[^ ;]\{1,\}\).*$/\1 ; python_version < '3.2'/" \
                -e "s/^\(contextlib2==[^ ;]\{1,\}\).*$/\1 ; python_version < '3.5'/" \
                -e "s/^\(enum34==[^ ;]\{1,\}\).*$/\1 ; python_version < '3.4'/" \
                -e "s/^\(funcsigs==[^ ;]\{1,\}\).*$/\1 ; python_version < '3.3'/" \
                -e "s/^\(functools32==[^ ;]\{1,\}\).*$/\1 ; python_version < '3.2'/" \
                -e "s/^\(monotonic==[^ ;]\{1,\}\).*$/\1/" \
                -e "s/^\(more-itertools==[^ ;]\{1,\}\).*$/\1/" \
                -e "s/^\(paste==[^ ;]\{1,\}\).*$/\1/" \
                -e "s/^\(pathlib2==[^ ;]\{1,\}\).*$/\1 ; python_version < '3.6'/" \
                -e "s/^\(py2-ipaddress==[^ ;]\{1,\}\).*$/\1 ; python_version < '3'/" \
                -e "s/^\(pyinotify==[^ ;]\{1,\}\).*$/\1 ; sys_platform != 'win32' and sys_platform != 'darwin' and sys_platform != 'sunos5'/" \
                -e "s/^\(python-dateutil==[^ ;]\{1,\}\).*$/\1/" \
                -e "s/^\(subprocess32==[^ ;]\{1,\}\).*$/\1 ; python_version < '3.0'/" \
                -e "s/^\(typing==[^ ;]\{1,\}\).*$/\1 ; python_version < '3.5'/" \
                -e "s/^\(urllib3==[^ ;]\{1,\}\).*$/\1/" \
                -e "s/^\(wcwidth==[^ ;]\{1,\}\).*$/\1/" \
                pinned-requirements.txt pinned-dev-requirements.txt
    if ! grep '==' pinned-dev-requirements.txt ; then
        rm -f pinned-dev-requirements.txt
    fi
done

if [ "$commit" -eq 1 ]; then
	git add -u "$THIS_DIRECTORY"
	git commit -m "Rev and re-lock Galaxy dependencies"
fi
