#!/bin/bash
#
# When running Galaxy Interactive Environments on a swarm (using Docker Engine
# swarm mode), GIE sessions that have ended will leave behind "shut down"
# Docker services. These must be removed, which you can do with this script.
#
# Note that this is dependent on the specific ordering and output format of
# `docker service ls` and `docker service ps`. As of the time of writing
# (Docker version 1.13.1) these formats cannot be controlled as can be done
# with `docker ps` and the `--format` option, so be careful when upgrading
# Docker releases.


CONTAINER_NAME_PREFIX='galaxy_gie_'
LOG_PATH=${1:-'/tmp/galaxy_gie_service_clean.log'}


{
    echo "Running cleanup at $(date)"
    for service_name in $(docker service ls | awk "\$2 ~ /^$CONTAINER_NAME_PREFIX/ {print \$2}"); do
        docker service ps --no-trunc $service_name | tail -1 | awk '{print $6}' | grep -q '^Shutdown$' && docker service rm $service_name;
    done
    echo "Done"
} >>$LOG_PATH
