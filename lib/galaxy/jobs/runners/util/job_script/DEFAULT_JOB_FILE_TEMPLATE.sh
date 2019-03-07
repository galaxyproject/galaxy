#!$shell

$headers

_galaxy_setup_environment() {
    local _use_framework_galaxy="$1"
    _GALAXY_JOB_HOME_DIR="$working_directory/home"
    _GALAXY_JOB_TMP_DIR=$tmp_dir_creation_statement
    $env_setup_commands
    if [ "$GALAXY_LIB" != "None" -a "$_use_framework_galaxy" = "True" ]; then
        if [ -n "$PYTHONPATH" ]; then
            PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
        else
            PYTHONPATH="$GALAXY_LIB"
        fi
        export PYTHONPATH
    fi
    # These don't get cleaned on a re-run but may in the future.
    [ -z "$_GALAXY_JOB_TMP_DIR" -a ! -f "$_GALAXY_JOB_TMP_DIR" ] || mkdir -p "$_GALAXY_JOB_TMP_DIR"
    [ -z "$_GALAXY_JOB_HOME_DIR" -a ! -f "$_GALAXY_JOB_HOME_DIR" ] || mkdir -p "$_GALAXY_JOB_HOME_DIR"
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
cd $working_directory
$memory_statement
$instrument_pre_commands
$command
echo $? > $exit_code_path
$instrument_post_commands
