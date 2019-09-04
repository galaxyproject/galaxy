#!/usr/bin/env bash

# Configure this script in a cron job to run some common cleanup operations
# Set the Environment variable GALAXY_CONFIG_FILE to use a custom galaxy config file.

set -e

display_help(){
  scriptname=$(basename "$0")
  printf "./$scriptname [--help] [--no-dry-run] [--days 10] 
Will run the galaxy cleanup scripts in the recommend order. By default a 'dry-run' is started. Specify --no-dry-run to do the actual cleanup.

--help                  Show this help
--dry-run|--no-dry-run  Dry run(default), will only print out what the scripts would have done. Specify --no-dry-run to do the actual cleanup.
--days                  Number of days to use as a cut off; do not act on objects updated more recently than this
"
}

# number of days to use as a cut off; do not act on objects updated more recently than this
DAYS=10
DRYRUN=true

while :
do
  case "$1" in
    --no-dry-run)
      DRYRUN=false
      shift
      ;;
    --dry-run ) # default
      DRYRUN=true
      shift
      ;;
    --days )
      DAYS="$2"
      shift; shift
      ;;
    -h )
      display_help
      exit 1
      ;;
    --help )
      display_help
      exit 1
      ;;
    "")
      break
      ;;
    *)
      shift
      ;;
  esac
done

cd "$(dirname "$0")"/..

. scripts/common_startup_functions.sh

setup_python

set_galaxy_config_file_var

if [ "$DRYRUN" = true ]; then
  MODE="--info_only"
else
  MODE="-r"
fi

MAINTENANCE_LOG=maintenance.log
COMMANDS=(
"python scripts/cleanup_datasets/cleanup_datasets.py $GALAXY_CONFIG_FILE -d $DAYS $MODE --delete_userless_histories >> $MAINTENANCE_LOG"
"python scripts/cleanup_datasets/cleanup_datasets.py $GALAXY_CONFIG_FILE -d $DAYS $MODE --purge_histories >> $MAINTENANCE_LOG"
"python scripts/cleanup_datasets/cleanup_datasets.py $GALAXY_CONFIG_FILE -d $DAYS $MODE --purge_datasets >> $MAINTENANCE_LOG"
"python scripts/cleanup_datasets/cleanup_datasets.py $GALAXY_CONFIG_FILE -d $DAYS $MODE --purge_folders >> $MAINTENANCE_LOG"
"python scripts/cleanup_datasets/cleanup_datasets.py $GALAXY_CONFIG_FILE -d $DAYS $MODE --delete_datasets >> $MAINTENANCE_LOG"
"python scripts/cleanup_datasets/cleanup_datasets.py $GALAXY_CONFIG_FILE -d $DAYS $MODE --purge_datasets >> $MAINTENANCE_LOG")

printf "\nDry run: $DRYRUN\nDays: $DAYS\n\n"
echo "Will run following commands and output in $MAINTENANCE_LOG"
for (( i = 0; i < ${#COMMANDS[@]} ; i++ )); do
  echo "${COMMANDS[$i]}"
done

if [ "$DRYRUN" = false ]; then
  echo "python scripts/set_user_disk_usage.py >> $MAINTENANCE_LOG"
fi

# Run the commands
for (( i = 0; i < ${#COMMANDS[@]} ; i++ )); do
  eval "${COMMANDS[$i]}"
done

if [ "$DRYRUN" = false ]; then
  python scripts/set_user_disk_usage.py >> $MAINTENANCE_LOG
fi
