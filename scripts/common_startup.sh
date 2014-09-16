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
    config/migrated_tools_conf.xml.sample
    config/shed_tool_conf.xml.sample
    config/shed_tool_data_table_conf.xml.sample
    config/shed_data_manager_conf.xml.sample
    lib/tool_shed/scripts/bootstrap_tool_shed/user_info.xml.sample
    tool-data/shared/ucsc/builds.txt.sample
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

: ${GALAXY_CONFIG_FILE:=config/galaxy.ini.sample}

if [ $FETCH_EGGS -eq 1 ]; then
    python ./scripts/check_eggs.py -q -c $GALAXY_CONFIG_FILE
    if [ $? -ne 0 ]; then
        echo "Some eggs are out of date, attempting to fetch..."
        python ./scripts/fetch_eggs.py -c $GALAXY_CONFIG_FILE
        if [ $? -eq 0 ]; then
            echo "Fetch successful."
        else
            echo "Fetch failed."
            exit 1
        fi
    fi
fi	
