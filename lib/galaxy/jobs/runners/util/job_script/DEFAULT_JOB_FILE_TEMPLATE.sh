#!$shell

$headers

_galaxy_setup_environment() {
    local _use_framework_galaxy="$1"
    if [ "$GALAXY_LIB" != "None" -a "$_use_framework_galaxy" = "True" ]; then
        if [ -n "$PYTHONPATH" ]; then
            PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
        else
            PYTHONPATH="$GALAXY_LIB"
        fi
        export PYTHONPATH
    fi
    $env_setup_commands
    if [ "$GALAXY_VIRTUAL_ENV" != "None" -a -f "$GALAXY_VIRTUAL_ENV/bin/activate" \
         -a "`command -v python`" != "$GALAXY_VIRTUAL_ENV/bin/python" ]; then
        . "$GALAXY_VIRTUAL_ENV/bin/activate"
    fi
}

$integrity_injection
$slots_statement
export GALAXY_SLOTS
GALAXY_VIRTUAL_ENV="$galaxy_virtual_env"
_GALAXY_VIRTUAL_ENV="$galaxy_virtual_env"
PRESERVE_GALAXY_ENVIRONMENT="$preserve_python_environment"
GALAXY_LIB="$galaxy_lib"
_galaxy_setup_environment "$PRESERVE_GALAXY_ENVIRONMENT"
GALAXY_PYTHON=`command -v python`
$instrument_pre_commands
cd $working_directory
$command
echo $? > $exit_code_path
$instrument_post_commands
