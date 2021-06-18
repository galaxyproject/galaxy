#!/bin/sh


function add_amp_paths() {    
    # Sets python paths needed by amp common code in virtual environment
    _AMP_UTIL_DIR="$PWD/tools/amp_util"
    _AMP_SCHEMA_DIR="$PWD/tools/amp_schema"
    PYTHONPATH="$_AMP_UTIL_DIR:$PYTHONPATH"
    PYTHONPATH="$_AMP_SCHEMA_DIR:$PYTHONPATH"
    echo "Setting AMP python path to $PYTHONPATH"
    export PYTHONPATH
}
function setup_amp_metrics(){
    # Build the UWSGI module needed for the config
    mkdir logs
    pushd amp_metrics
    make || (
        echo "NOTICE: Cannot build the uwsg system_metrics.so file"
        echo "        API metrics will not be collected"
    )
    popd
}



