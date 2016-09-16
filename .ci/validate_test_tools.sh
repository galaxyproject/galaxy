#! /bin/bash

cd `dirname $0`/..

./scripts/common_startup.sh
GALAXY_VIRTUAL_ENV="${GALAXY_VIRTUAL_ENV:-.venv}"
if [ -d "$GALAXY_VIRTUAL_ENV" ];
then
    printf "Activating virtualenv at $GALAXY_VIRTUAL_ENV\n"
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi

xsd_path="lib/galaxy/tools/xsd/galaxy.xsd"
# Lint the XSD
xmllint --noout "$xsd_path"

test_tools_path="test/functional/tools"
tool_files_list=`mktemp`
err_tmp=`mktemp`
# Validate the tools.
ls "$test_tools_path"/*xml | grep -v '_conf.xml$' > "$tool_files_list"

count=`wc -l "$tool_files_list" | cut -f1 -d' '`
echo "1..$count"
count=0
exit=0
while read p; do
    count=$((count+1))
    path="$p"
    echo $path
    PYTHONPATH=lib:$PYTHONPATH
    export PYTHONPATH
    result=`python -c "import galaxy.tools.loader; import xml.etree; xml.etree.ElementTree.dump(galaxy.tools.loader.load_tool('$path').getroot())" | xmllint --nowarning --noout --schema "$xsd_path" - 2> "$err_tmp"`
    if [ $? -eq 0 ]
    then
        echo "ok $count";
    else
        echo "not ok $count $path";
        cat "$err_tmp" | sed 's/^/    /'
        exit=1
    fi
done <"$tool_files_list"
rm "$err_tmp"
exit $exit
