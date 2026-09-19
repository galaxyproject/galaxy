#!/bin/sh

cd "$(dirname "$0")"/..

GALAXY_SKIP_CLIENT_BUILD=1 ./scripts/common_startup.sh
GALAXY_VIRTUAL_ENV="${GALAXY_VIRTUAL_ENV:-.venv}"
if [ -d "$GALAXY_VIRTUAL_ENV" ]; then
    printf "Activating virtualenv at $GALAXY_VIRTUAL_ENV\n"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

xsd_path="lib/galaxy/tool_util/xsd/galaxy.xsd"

err_tmp=$(mktemp)
count=0
exit=0
for p in "$@"; do
    count=$((count+1))
    path="$p"
    echo "$path"
    PYTHONPATH=lib:$PYTHONPATH
    export PYTHONPATH
    python -c "import galaxy.tool_util.loader; import lxml.etree; lxml.etree.dump(galaxy.tool_util.loader.load_tool('$path').getroot())" | xmllint --nowarning --noout --schema "$xsd_path" - 2> "$err_tmp"
    if [ $? -eq 0 ]; then
        echo "ok $count";
    else
        echo "not ok $count $path";
        sed 's/^/    /' "$err_tmp"
        exit=1
    fi
done
rm "$err_tmp"
exit $exit
