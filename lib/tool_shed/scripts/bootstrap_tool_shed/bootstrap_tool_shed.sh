#!/bin/bash

: ${TOOL_SHED_CONFIG_FILE:=config/tool_shed.ini.sample}

stop_err() {
	echo $1
	python ./scripts/paster.py serve ${TOOL_SHED_CONFIG_FILE} --pid-file=tool_shed_bootstrap.pid --log-file=tool_shed_bootstrap.log --stop-daemon
	exit 1
}

tool_shed=`./lib/tool_shed/scripts/bootstrap_tool_shed/parse_run_sh_args.sh $@`

if [ $? -ne 0 ] ; then
	exit 0
fi

log_file="lib/tool_shed/scripts/bootstrap_tool_shed/bootstrap.log"

database_result=`python ./lib/tool_shed/scripts/bootstrap_tool_shed/bootstrap_util.py --execute check_db --config_file ${TOOL_SHED_CONFIG_FILE}`

if [ $? -ne 0 ] ; then
	stop_err "Unable to bootstrap tool shed. $database_result"
fi

echo "Bootstrapping from tool shed at $tool_shed."
echo -n "Creating database... "
python scripts/create_db.py tool_shed

if [ $? -eq 0 ] ; then
	echo "done."
else
	stop_err "failed."
fi

if [ $? -eq 0 ] ; then
	user_auth=`python ./lib/tool_shed/scripts/bootstrap_tool_shed/bootstrap_util.py --execute admin_user_info --config_file ${TOOL_SHED_CONFIG_FILE}`
	local_shed_url=`python ./lib/tool_shed/scripts/bootstrap_tool_shed/bootstrap_util.py --execute get_url --config_file ${TOOL_SHED_CONFIG_FILE}`
fi

admin_user_name=`echo $user_auth | awk 'BEGIN { FS="__SEP__" } ; { print \$1 }'`
admin_user_email=`echo $user_auth | awk 'BEGIN { FS="__SEP__" } ; { print \$2 }'`
admin_user_password=`echo $user_auth | awk 'BEGIN { FS="__SEP__" } ; { print \$3 }'`

echo -n "Creating user '$admin_user_name' with email address '$admin_user_email'..."

python lib/tool_shed/scripts/bootstrap_tool_shed/create_user_with_api_key.py ${TOOL_SHED_CONFIG_FILE} >> $log_file

echo " done."

sed -i "s/#admin_users = user1@example.org,user2@example.org/admin_users = $admin_user_email/" ${TOOL_SHED_CONFIG_FILE}
echo -n "Starting tool shed in order to populate users and categories... "

if [ -f tool_shed_bootstrap.pid ] ; then
	stop_err "A bootstrap process is already running."
fi

python ./scripts/paster.py serve ${TOOL_SHED_CONFIG_FILE} --pid-file=tool_shed_bootstrap.pid --log-file=tool_shed_bootstrap.log --daemon > /dev/null

shed_pid=`cat tool_shed_bootstrap.pid`

while : ; do
	tail -n 1 tool_shed_bootstrap.log | grep -q "Removing PID file tool_shed_webapp.pid"
	if [ $? -eq 0 ] ; then
		echo "failed."
		echo "More information about this failure may be found in the following log snippet from tool_shed_bootstrap.log:"
		echo "========================================"
		tail -n 40 tool_shed_bootstrap.log
		echo "========================================"
		stop_err " "
	fi
	tail -n 2 tool_shed_bootstrap.log | grep -q "Starting server in PID $shed_pid"
	if [ $? -eq 0 ] ; then
		echo "done."
		break
	fi
done

echo -n "Retrieving admin user's API key from $local_shed_url..."
api_key=`curl -s --user $admin_user_email:$admin_user_password $local_shed_url/api/authenticate/baseauth/ | sed 's/.\+api_key[^0-9a-f]\+\([0-9a-f]\+\).\+/\1/'`

if [[ -z $api_key && ${api_key+x} ]] ; then
		stop_err "Error getting API key for user $admin_user_email."
fi

echo " done."

if [ $? -eq 0 ] ; then
	echo -n "Creating users... "
	python lib/tool_shed/scripts/api/create_users.py -a $api_key -f $tool_shed -t $local_shed_url >> $log_file
	echo "done."
	echo -n "Creating categories... "
	python lib/tool_shed/scripts/api/create_categories.py -a $api_key -f $tool_shed -t $local_shed_url >> $log_file
	echo "done."
else
	stop_err "Error getting API key from local tool shed."
fi

echo "Bootstrap complete, shutting down temporary tool shed process. A log has been saved to tool_shed_bootstrap.log"
python ./scripts/paster.py serve ${TOOL_SHED_CONFIG_FILE} --pid-file=tool_shed_bootstrap.pid --log-file=tool_shed_bootstrap.log --stop-daemon

exit 0
