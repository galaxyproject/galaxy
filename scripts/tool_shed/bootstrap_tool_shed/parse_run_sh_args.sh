#!/bin/bash

while (( $# )) ; do
    case "$1" in
	-bootstrap_from_tool_shed|--bootstrap_from_tool_shed)
		bootstrap="true"
		tool_shed=$2
		echo $tool_shed
		exit 0
		break
		;;
	esac
	shift 1
done
exit 1