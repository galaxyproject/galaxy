#!/bin/bash

# explicitly attempt to fetch eggs before running
FETCH_EGGS=1
COPY_SAMPLE_FILES=1
for arg in "$@"; do
    [ "$arg" = "--skip-eggs" ] && FETCH_EGGS=0
    [ "$arg" = "--stop-daemon" ] && FETCH_EGGS=0
    [ "$arg" = "--skip-samples" ] && COPY_SAMPLE_FILES=0
done

SAMPLES="
    tool_shed_wsgi.ini.sample
    datatypes_conf.xml.sample
    external_service_types_conf.xml.sample
    migrated_tools_conf.xml.sample
    reports_wsgi.ini.sample
    shed_tool_conf.xml.sample
    tool_conf.xml.sample
    shed_tool_data_table_conf.xml.sample
    tool_data_table_conf.xml.sample
    tool_sheds_conf.xml.sample
    data_manager_conf.xml.sample
    shed_data_manager_conf.xml.sample
    openid_conf.xml.sample
    job_metrics_conf.xml.sample
    universe_wsgi.ini.sample
    lib/tool_shed/scripts/bootstrap_tool_shed/user_info.xml.sample
    tool-data/shared/ncbi/builds.txt.sample
    tool-data/shared/ensembl/builds.txt.sample
    tool-data/shared/ucsc/builds.txt.sample
    tool-data/shared/ucsc/publicbuilds.txt.sample
    tool-data/shared/ucsc/ucsc_build_sites.txt.sample
    tool-data/shared/igv/igv_build_sites.txt.sample
    tool-data/shared/rviewer/rviewer_build_sites.txt.sample
    tool-data/*.sample
    static/welcome.html.sample
"

if [ $COPY_SAMPLE_FILES -eq 1 ]; then
	# Create any missing config/location files
	for sample in $SAMPLES; do
		file=${sample%.sample}
	    if [ ! -f "$file" -a -f "$sample" ]; then
	        echo "Initializing $file from `basename $sample`"
	        cp $sample $file
	    fi
	done
fi

if [ $FETCH_EGGS -eq 1 ]; then
    python ./scripts/check_eggs.py -q
    if [ $? -ne 0 ]; then
        echo "Some eggs are out of date, attempting to fetch..."
        python ./scripts/fetch_eggs.py
        if [ $? -eq 0 ]; then
            echo "Fetch successful."
        else
            echo "Fetch failed."
            exit 1
        fi
    fi
fi	
