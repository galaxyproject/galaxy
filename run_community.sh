#!/bin/sh

cd `dirname $0`

SAMPLES="
    community_wsgi.ini.sample
    datatypes_conf.xml.sample
    external_service_types_conf.xml.sample
    migrated_tools_conf.xml.sample
    reports_wsgi.ini.sample
    shed_tool_conf.xml.sample
    tool_conf.xml.sample
    shed_tool_data_table_conf.xml.sample
    tool_data_table_conf.xml.sample
    tool_sheds_conf.xml.sample
    openid_conf.xml.sample
    universe_wsgi.ini.sample
    tool-data/shared/ncbi/builds.txt.sample
    tool-data/shared/ensembl/builds.txt.sample
    tool-data/shared/ucsc/builds.txt.sample
    tool-data/shared/ucsc/publicbuilds.txt.sample
    tool-data/shared/igv/igv_build_sites.txt.sample
    tool-data/shared/rviewer/rviewer_build_sites.txt.sample
    tool-data/*.sample
    static/welcome.html.sample
"

# Create any missing config/location files
for sample in $SAMPLES; do
    file=`echo $sample | sed -e 's/\.sample$//'`
    if [ ! -f "$file" -a -f "$sample" ]; then
        echo "Initializing $file from `basename $sample`"
        cp $sample $file
    fi
done

python ./scripts/paster.py serve community_wsgi.ini --pid-file=community_webapp.pid --log-file=community_webapp.log $@
