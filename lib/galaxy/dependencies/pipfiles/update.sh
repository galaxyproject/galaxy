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
ENVS="develop
flake8
default"

for env in $ENVS; do
    cd "$THIS_DIRECTORY/$env"
    pipenv lock
    # Strip out hashes and trailing whitespace for unhashed version
    # of this requirements file, needed for pipenv < 11.1.2
    pipenv lock -r | sed -e 's/--hash[^[:space:]]*//g' -e 's/[[:space:]]*$//' > pinned-requirements.txt
    # Fix oscillating environment markers
    sed -i.orig -e "s/^cffi==\([^;]*\).*$/cffi==\1/" \
                -e "s/^enum34==\([^;]*\).*$/enum34==\1; python_version < '3.4'/" \
                -e "s/^funcsigs==\([^;]*\).*$/funcsigs==\1; python_version < '3.3'/" pinned-requirements.txt
done

if [ "$commit" -eq "1" ];
then
	git add -u "$THIS_DIRECTORY"
	git commit -m "Rev and re-lock Galaxy dependencies"
fi
