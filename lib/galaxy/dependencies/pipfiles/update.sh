#!/bin/sh

commit=0

usage() {
cat << EOF
Usage: ${0##*/} [-c]

Use pipenv to regenerate locked and hashed versions of Galaxy dependencies.
Use -c to automatically commit these changes (be sure you have no staged git
changes).

EOF
}

while getopts ":hc" opt; do
    case "$opt" in
        h)
            usage
            exit 0
            ;;
        c)
            commit=1
            ;;
        '?')
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
    pipenv lock -v
    # Strip out hashes and trailing whitespace for unhashed version
    # of this requirements file, needed for pipenv < 11.1.2
    pipenv lock -r | sed -e 's/--hash[^[:space:]]*//g' -e 's/[[:space:]]*$//' > pinned-requirements.txt
    pipenv lock -r --dev | sed -e 's/--hash[^[:space:]]*//g' -e 's/[[:space:]]*$//' > pinned-dev-requirements.txt
    # Fix oscillating environment markers
    sed -i.orig -e "s/^azure-storage-nspkg==\([^ ;]\{1,\}\).*$/azure-storage-nspkg==\1/" \
                -e "s/^cffi==\([^ ;]\{1,\}\).*$/cffi==\1/" \
                -e "s/^cmd2==\([^ ;]\{1,\}\).*$/cmd2==\1/" \
                -e "s/^configparser==\([^ ;]\{1,\}\).*$/configparser==\1 ; python_version < '3.2'/" \
                -e "s/^enum34==\([^ ;]\{1,\}\).*$/enum34==\1 ; python_version < '3.4'/" \
                -e "s/^funcsigs==\([^ ;]\{1,\}\).*$/funcsigs==\1 ; python_version < '3.3'/" \
                -e "s/^functools32==\([^ ;]\{1,\}\).*$/functools32==\1 ; python_version < '3.2'/" \
                -e "s/^futures==\([^ ;]\{1,\}\).*$/futures==\1 ; python_version == '2.6' or python_version == '2.7'/" \
                -e "s/^monotonic==\([^ ;]\{1,\}\).*$/monotonic==\1/" \
                -e "s/^more-itertools==\([^ ;]\{1,\}\).*$/more-itertools==\1/" \
                -e "s/^py2-ipaddress==\([^ ;]\{1,\}\).*$/py2-ipaddress==\1 ; python_version < '3'/" \
                -e "s/^pyinotify==\([^ ;]\{1,\}\).*$/pyinotify==\1 ; sys_platform != 'win32' and sys_platform != 'darwin' and sys_platform != 'sunos5'/" \
                -e "s/^python-dateutil==\([^ ;]\{1,\}\).*$/python-dateutil==\1/" \
                -e "s/^subprocess32==\([^ ;]\{1,\}\).*$/subprocess32==\1 ; python_version < '3.0'/" \
                pinned-requirements.txt pinned-dev-requirements.txt
done

if [ "$commit" -eq "1" ];
then
	git add -u "$THIS_DIRECTORY"
	git commit -m "Rev and re-lock Galaxy dependencies"
fi
