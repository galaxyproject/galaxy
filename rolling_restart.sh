#!/bin/bash
cd `dirname $0`

check_if_not_started(){
	# Search for all pids in the logs and tail for the last one
	latest_pid=`egrep '^Starting server in PID [0-9]+\.$' $1 -o | sed 's/Starting server in PID //g;s/\.$//g' | tail -n 1`
	# Grab the current pid from the file we were given
	current_pid_in_file=$(cat $2);
	# If they're equivalent, then the current pid file agrees with our logs
	# and we've succesfully started
	if [[ $latest_pid -eq $current_pid_in_file ]];
	then
		echo 0;
	else
		echo 1;
	fi
}


GALAXY_CONFIG_FILE=config/galaxy.ini
if [ ! -f $GALAXY_CONFIG_FILE ]; then
    GALAXY_CONFIG_FILE=universe_wsgi.ini
fi

servers=`sed -n 's/^\[server:\(.*\)\]/\1/  p' $GALAXY_CONFIG_FILE | xargs echo`
for server in $servers;
do
	# If there's a pid
	if [[ -e $server.pid ]]
	then
		# Then kill it
		echo "Killing $server"
		pid=`cat $server.pid`
		kill $pid
	else
		# Otherwise just continue
		echo "$server not running"
	fi
	# Start the server (and background) (should this be nohup'd?)
	python ./scripts/paster.py serve $GALAXY_CONFIG_FILE --server-name=$server --pid-file=$server.pid --log-file=$server.log --daemon $@
	# Wait for the server to start
	sleep 1
	# Grab the new pid
	pid=`cat $server.pid`
	result=1
	# Wait for the latest pid in the file to be the pid we've grabbed
	while [[ $result -eq 1 ]]
	do
		result=$(check_if_not_started $server.log $server.pid)
		echo -n "."
		sleep 1
	done
	echo ""
done

