#!/bin/sh
$headers
$slots_statement
export GALAXY_SLOTS
GALAXY_LIB="$galaxy_lib"
if [ "$GALAXY_LIB" != "None" ]; then
    if [ -n "$PYTHONPATH" ]; then
        PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
    else
        PYTHONPATH="$GALAXY_LIB"
    fi
    export PYTHONPATH
fi
$env_setup_commands
$instrument_pre_commands
cd $working_directory
$command
echo $? > $exit_code_path
$instrument_post_commands
