#!$shell

$headers

_galaxy_setup_environment() {
    local _use_framework_galaxy="$1"

    if [ -z "$_GALAXY_JOB_TMP_DIR" ]; then
        _GALAXY_JOB_DIR="$working_directory"
        _GALAXY_JOB_HOME_DIR="$home_directory"
        _GALAXY_JOB_TMP_DIR=$tmp_dir_creation_statement
    fi

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
export PYTHONWARNINGS="ignore"
GALAXY_VIRTUAL_ENV="$galaxy_virtual_env"
_GALAXY_VIRTUAL_ENV="$galaxy_virtual_env"
PRESERVE_GALAXY_ENVIRONMENT="$preserve_python_environment"
GALAXY_LIB="$galaxy_lib"
_galaxy_setup_environment "$PRESERVE_GALAXY_ENVIRONMENT"
export _GALAXY_JOB_HOME_DIR
export _GALAXY_JOB_TMP_DIR

TEMP="${TEMP:-$TMP}"
TMPDIR="${TMPDIR:-$TMP}"

TMP="${TMP:-$TEMP}"
TMPDIR="${TMPDIR:-$TEMP}"

TMP="${TMP:-$TMPDIR}"
TEMP="${TEMP:-$TMPDIR}"

TMP="${TMP:-$_GALAXY_JOB_TMP_DIR}"
TEMP="${TEMP:-$_GALAXY_JOB_TMP_DIR}"
TMPDIR="${TMPDIR:-$_GALAXY_JOB_TMP_DIR}"

export TMP
export TEMP
export TMPDIR

GALAXY_PYTHON=`command -v python`
$prepare_dirs_statement
cd $working_directory
$memory_statement
$instrument_pre_commands
$command
$instrument_post_commands
