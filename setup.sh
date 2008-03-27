#!/bin/sh

. ./scripts/get_python.sh

SAMPLES="
datatype_converters_conf.xml.sample
reports_wsgi.ini.sample
tool_conf.xml.sample
universe_wsgi.ini.sample
"

for sample in $SAMPLES; do
    file=`basename $sample .sample`
    if [ -f $file ]; then
        echo "Not overwriting existing $file"
    else
        echo "Copying $sample to $file"
        cp $sample $file
    fi
done

$GALAXY_PYTHON ./scripts/fetch_eggs.py
