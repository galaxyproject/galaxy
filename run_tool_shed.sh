#!/bin/sh

cd `dirname $0`

./scripts/common_startup.sh

tool_shed=`./lib/tool_shed/scripts/bootstrap_tool_shed/parse_run_sh_args.sh $@`
args=$@

if [ $? -eq 0 ] ; then
	bash ./lib/tool_shed/scripts/bootstrap_tool_shed/bootstrap_tool_shed.sh $@
	args=`echo $@ | sed "s#-\?-bootstrap_from_tool_shed $tool_shed##"`
fi

python ./scripts/paster.py serve tool_shed_wsgi.ini --pid-file=tool_shed_webapp.pid --log-file=tool_shed_webapp.log $args
