#!/bin/sh

cd "$(dirname "$0")"


TOOL_SHED_PID=${TOOL_SHED_PID:-tool_shed_webapp.pid}
TOOL_SHED_LOG=${TOOL_SHED_LOG:-tool_shed_webapp.log}
PID_FILE=$TOOL_SHED_PID
LOG_FILE=$TOOL_SHED_LOG

. ./scripts/common_startup_functions.sh

parse_common_args $@

run_common_start_up

setup_python


tool_shed=`./scripts/tool_shed/bootstrap_tool_shed/parse_run_sh_args.sh $parser_args`
args=$parser_args

if [ $? -eq 0 ] ; then
	bash ./scripts/tool_shed/bootstrap_tool_shed/bootstrap_tool_shed.sh $parser_args
	args=`echo $@ | sed "s#-\?-bootstrap_from_tool_shed $tool_shed##"`
fi

if [ -z "$TOOL_SHED_CONFIG_FILE" ]; then
    if [ -f tool_shed_wsgi.ini ]; then
        TOOL_SHED_CONFIG_FILE=tool_shed_wsgi.ini
    elif [ -f config/tool_shed.ini ]; then
        TOOL_SHED_CONFIG_FILE=config/tool_shed.ini
    elif [ -f config/tool_shed.yml ]; then
        TOOL_SHED_CONFIG_FILE=config/tool_shed.yml
    fi
    export TOOL_SHED_CONFIG_FILE
fi

find_server ${TOOL_SHED_CONFIG_FILE:-none} tool_shed
echo "executing: $run_server $server_args"
eval $run_server $server_args
