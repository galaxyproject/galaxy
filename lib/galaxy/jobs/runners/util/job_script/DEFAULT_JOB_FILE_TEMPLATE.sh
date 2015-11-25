#!/bin/sh

# The following block can be used by the job creation system
# to ensure this script is runnable before running it directly
# or submitting it to a cluster manager.
if [ -n "$ABC_TEST_JOB_SCRIPT_INTEGRITY_XYZ" ]; then
    exit 42
fi

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
GALAXY_VIRTUAL_ENV="$galaxy_virtual_env"
if [ "$GALAXY_VIRTUAL_ENV" != "None" -a -z "$VIRTUAL_ENV" \
     -a -f "$GALAXY_VIRTUAL_ENV/bin/activate" ]; then
    . "$GALAXY_VIRTUAL_ENV/bin/activate"
fi
$instrument_pre_commands
cd $working_directory
$command
echo $? > $exit_code_path
$instrument_post_commands
