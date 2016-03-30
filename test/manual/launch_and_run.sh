#!/bin/bash
#set -e

# Open and few the contents of a docker-galaxy-stable container.
# docker run --rm -i -t bgruening/galaxy-stable /bin/bash

pwd_dir=$(pwd)
GALAXY_ROOT=`dirname $0`/../..
cd $GALAXY_ROOT
GALAXY_ROOT=$(pwd)
SCRIPT_DIR="$GALAXY_ROOT/test/manual"

manual_test_script=$1
shift
manual_test_script_args="$@"

GALAXY_VIRTUAL_ENV="${GALAXY_VIRTUAL_ENV:-.venv}"

# Docker options defined to reflect run_tests.sh names and behavior.
DOCKER_DEFAULT_IMAGE='bgruening/galaxy-stable'

DOCKER_EXTRA_ARGS=${DOCKER_ARGS:-""}
DOCKER_RUN_EXTRA_ARGS=${DOCKER_RUN_EXTRA_ARGS:-""}
DOCKER_IMAGE=${DOCKER_IMAGE:-${DOCKER_DEFAULT_IMAGE}}
# Root for Galaxy in the docker container
DOCKER_GALAXY_ROOT=${DOCKER_GALAXY_ROOT:-/galaxy-central}

# Location of this script's directory when mounted into the container.
DOCKER_SCRIPT_DIR=/etc/galaxy/manual

GALAXY_PORT=${GALAXY_PORT:-"any_free"}
if [ "$GALAXY_PORT" == "any_free" ];
then
    GALAXY_PORT=`python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()'`
fi

GALAXY_URL=${GALAXY_URL:-http://localhost:${GALAXY_PORT}}
GALAXY_MASTER_API_KEY=${GALAXY_MASTER_API_KEY:-HSNiugRFvgT574F43jZ7N9F3}

LOGS_DIR=`cd "$LOGS_DIR"; pwd`
WORK_DIR=`mktemp --tmpdir=$LOGS_DIR -d -t gxperfXXXX`
echo "WORK_DIR is ${WORK_DIR}"
NAME=`basename $WORK_DIR`

GALAXY_HANDLER_NUMPROCS=${GALAXY_HANDLER_NUMPROCS:-1}

DOCKER_ENVIRONMENT="\
-e NONUSE=nodejs,proftp,reports \
-e GALAXY_HANDLER_NUMPROCS=$GALAXY_HANDLER_NUMPROCS \
-e GALAXY_CONFIG_OVERRIDE_TOOL_CONFIG_FILE=$DOCKER_GALAXY_ROOT/test/functional/tools/samples_tool_conf.xml \
-e GALAXY_CONFIG_ENABLE_BETA_WORKFLOW_MODULES=true \
-e GALAXY_CONFIG_OVERRIDE_ENABLE_BETA_TOOL_FORMATS=true \
"

if [ $manual_test_script == "workflows_scaling" ];
then
    DOCKER_ENVIRONMENT="$DOCKER_ENVIRONMENT -e GALAXY_CONFIG_JOB_CONFIG_FILE=$DOCKER_SCRIPT_DIR/workflow_job_conf.xml "
fi

# Mount logs, local galaxy changes, and local galaxy config.
DOCKER_VOLUMES="\
-v $WORK_DIR:/galaxy_logs \
-v $GALAXY_ROOT/lib:$DOCKER_GALAXY_ROOT/lib \
-v $GALAXY_ROOT/test:/galaxy-central/test \
-v $SCRIPT_DIR:$DOCKER_SCRIPT_DIR \
"
DOCKER_RUN_ARGS="$DOCKER_RUN_EXTRA_ARGS -d -p ${GALAXY_PORT}:80 -i -t $DOCKER_VOLUMES $DOCKER_ENVIRONMENT"

docker_image_id=`docker $DOCKER_EXTRA_ARGS run $DOCKER_RUN_ARGS ${DOCKER_IMAGE}`

echo "Docker container with id $docker_image_id launched. Inspect with 'docker exec -i -t $docker_image_id /bin/bash'."

# Wait for Galaxy to be available
for i in {1..40}; do curl --silent --fail ${GALAXY_URL}/api/version && break || sleep 5; done

${GALAXY_VIRTUAL_ENV}/bin/python test/manual/$manual_test_script.py --api_key ${GALAXY_MASTER_API_KEY} --host ${GALAXY_URL} $manual_test_script_args
docker exec -i -t $docker_image_id /bin/bash -c "cp /home/galaxy/*log /galaxy_logs"
docker kill $docker_image_id
