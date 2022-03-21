#!/usr/bin/env bash

set -x

# Activate the virtualenv, if it exists.
[ -f ./.venv/bin/activate ] && . ./.venv/bin/activate

: "${TOOL_SHED_CONFIG_FILE:=lib/galaxy/config/sample/tool_shed.yml.sample}"
LOCAL_SHED_URL="${LOCAL_SHED_URL:-http://localhost:9009}"
TOOL_SHED_PID=tool_shed_bootstrap.pid
TOOL_SHED_LOG=tool_shed_bootstrap.log
export TOOL_SHED_PID
export TOOL_SHED_LOG
export TOOL_SHED_CONFIG_FILE

stop_err() {
	echo "$1"
	kill "$(cat $TOOL_SHED_PID)"
	exit 1
}

tool_shed=$(./scripts/tool_shed/bootstrap_tool_shed/parse_run_sh_args.sh "$@")

if [ $? -ne 0 ] ; then
	exit 0
fi

log_file="scripts/tool_shed/bootstrap_tool_shed/bootstrap.log"

database_result="$(python ./scripts/tool_shed/bootstrap_tool_shed/bootstrap_util.py --execute check_db --config_file ${TOOL_SHED_CONFIG_FILE})"

if [ $? -ne 0 ] ; then
	stop_err "Unable to bootstrap tool shed. $database_result"
fi

echo "Bootstrapping from tool shed at $tool_shed."
echo -n "Creating database... "
python scripts/create_toolshed_db.py tool_shed

if [ $? -eq 0 ] ; then
	echo "done."
else
	stop_err "failed."
fi

if [ $? -eq 0 ] ; then
	user_auth=$(python ./scripts/tool_shed/bootstrap_tool_shed/bootstrap_util.py --execute admin_user_info --config_file ${TOOL_SHED_CONFIG_FILE})
fi

admin_user_name=$(echo "$user_auth" | awk 'BEGIN { FS="__SEP__" } ; { print $1 }')
admin_user_email=$(echo "$user_auth" | awk 'BEGIN { FS="__SEP__" } ; { print $2 }')
admin_user_password=$(echo "$user_auth" | awk 'BEGIN { FS="__SEP__" } ; { print $3 }')

echo -n "Creating user '$admin_user_name' with email address '$admin_user_email'..."

python ./scripts/tool_shed/bootstrap_tool_shed/create_user_with_api_key.py -c ${TOOL_SHED_CONFIG_FILE} >> $log_file

echo " done."

export TOOL_SHED_CONFIG_ADMIN_USERS=$admin_user_email
echo -n "Starting tool shed in order to populate users and categories... "


if [ -f "$TOOL_SHED_PID" ] ; then
	stop_err "A bootstrap process is already running."
fi

./run_tool_shed.sh -bootstrap_from_tool_shed --daemon > /dev/null

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
	tail -n 2 tool_shed_bootstrap.log | grep -q "Application startup complete."
	if [ $? -eq 0 ] ; then
		echo "done."
		break
	fi
done

echo -n "Retrieving admin user's API key from $LOCAL_SHED_URL..."

curl_response=$(curl -s --user "$admin_user_email":"$admin_user_password" "$LOCAL_SHED_URL"/api/authenticate/baseauth/)
# Gets an empty response only on first attempt for some reason?
sleep 1
curl_response=$(curl -s --user "$admin_user_email":"$admin_user_password" "$LOCAL_SHED_URL"/api/authenticate/baseauth/)
api_key=$(echo "$curl_response" | grep api_key | awk -F\" '{print $4}')

if [[ -z $api_key && ${api_key+x} ]] ; then
		stop_err "Error getting API key for user $admin_user_email. Response: $curl_response"
fi

echo " done."

if [ $? -eq 0 ] ; then
	echo -n "Creating users... "
	python scripts/tool_shed/api/create_users.py -a "$api_key" -f "$tool_shed" -t "$LOCAL_SHED_URL" >> "$log_file"
	echo "done."
	echo -n "Creating categories... "
	python scripts/tool_shed/api/create_categories.py -a "$api_key" -f "$tool_shed" -t "$LOCAL_SHED_URL" >> "$log_file"
	echo "done."
else
	stop_err "Error getting API key from local tool shed."
fi

echo "Bootstrap complete, shutting down temporary tool shed process. A log has been saved to tool_shed_bootstrap.log"
kill "$(cat $TOOL_SHED_PID)"

exit 0
