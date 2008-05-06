#!/bin/sh
#set -xv
#
# Runs the scripts/check_galaxy.py script in a way that's easy to handle from cron
#

# defaults (note: default sleep is below since it depends on debug)
DEBUG=0
STAGGER=0
INTERVAL=3
MAIL=
PAGE=
NEWHIST=
BARDARG=0
# get commandline opts
while getopts dsi:l:m:p:n optname
do
    case $optname in
        d)  DEBUG=1 ;;
        s)  STAGGER=1 ;;
        i)  INTERVAL=$OPTARG ;;
        l)  SLEEP=$OPTARG ;;
        m)  MAIL="$MAIL $OPTARG" ;;
        p)  PAGE="$PAGE $OPTARG" ;;
        n)  NEWHIST="-n" ;;
        *)  BADARG=1 ;;
    esac
done
shift `expr $OPTIND - 1`

if [ -z "$1" -o "$BADARG" ]; then
    cat <<EOF
usage: `basename $0` [-ds] [-i interval] [-m email_address]+ [-p pager_address]+ <galaxy_host>"
  -d            Print debugging information.
  -s            Stagger mailing the pagers/emails, instead of all at once when
                there's a problem.  Useful for running check_galaxy at night.
  -i <interval> The number of times this wrapper should execute before mailing
                the next address, when staggering is enabled.  Mail is sent
                every <interval> runs of the program, so the actual time
                between emails is:
                  time = (<interval>) * (how often wrapper runs from cron)
  -l <seconds>  This wrapper runs check_galaxy a second time if the first check
                fails, in case the problem is intermittent.  <seconds> is how
                many seconds to sleep between checks.
  -m <address>  Email addresses to send the full check_galaxy output to, if
                Galaxy is down.  Use multiple -m options to specify multiple
                addresses.  When staggering, email will be sent in the order
                which you specify -m options on the command line.
  -p <address>  Like -m, but sends just the last line of check_galaxy's output.
                Useful for pagers.  When staggering is enabled and both -m and
                -p options are present, the first -m address and the first -p
                address are mailed simultaneously, followed by the second -m
                and second -p, and so on.
  -n            Create a new history (passes the -n option to check_galaxy.py).
  <galaxy_host> The hostname of the Galaxy server to check.  Use a : if running
                on a non-80 port (e.g. galaxy.example.com:8080).
EOF
    exit 1
fi

if [ -z "$SLEEP" ]; then
    if [ $DEBUG ]; then
        SLEEP=2
    else
        SLEEP=60
    fi
fi

# globals
CRON_DIR=`dirname $0`
SCRIPTS_DIR="$CRON_DIR/../scripts"
CHECK_GALAXY="$SCRIPTS_DIR/check_galaxy.py"
VAR="$HOME/.check_galaxy"

# sanity
if [ ! -f $CHECK_GALAXY ]; then
    [ $DEBUG = 1 ] && echo "$CHECK_GALAXY is missing"
    exit 0
fi

# Do any other systems' default ps not take BSD ps args?
case `uname -s` in
    SunOS)  PS="/usr/ucb/ps" ;;
    *)      PS="ps" ;;
esac

NOTIFIED_MAIL="$VAR/$1/mail"
NOTIFIED_PAGE="$VAR/$1/page"
MUTEX="$VAR/$1/wrap.mutex"
COUNT="$VAR/$1/wrap.count"
STAGGER_FILE="$VAR/$1/wrap.stagger"
for dir in $VAR/$1 $NOTIFIED_MAIL $NOTIFIED_PAGE; do
    if [ ! -d $dir ]; then
        mkdir -p -m 0700 $dir
        if [ $? -ne 0 ]; then
            [ $DEBUG = 1 ] && echo "unable to create dir: $dir"
            exit 0
        fi
    fi
done

if [ ! -f "$VAR/$1/login" ]; then
    [ $DEBUG = 1 ] && cat <<EOF
Please create the file:
  $VAR/$1/login
This should contain a username and password to log in to
Galaxy with, on one line, separated by whitespace, e.g.:

check_galaxy@example.com password

If the user does not exist, check_galaxy will create it
for you.
EOF
    exit 0
fi

if [ $STAGGER ]; then
    if [ -f "$STAGGER_FILE" ]; then
        STAGGER_COUNT=`cat $STAGGER_FILE`
    else
        STAGGER_COUNT=$INTERVAL
    fi
fi

# only run one at once
if [ -f $MUTEX ]; then
    pid=`cat $MUTEX`
    $PS p $pid >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        if [ -f $COUNT ]; then
            count=`cat $COUNT`
        else
            count=0
        fi
        if [ "$count" -eq 3 ]; then
            echo "A check_galaxy process for $1 has been running for an unusually long time.  Something is broken." \
                | mail -s "$1 problems" $MAIL
        fi
        expr $count + 1 > $COUNT
        exit 0
    else
        # stale mutex
        rm -f $MUTEX
    fi
fi

rm -f $COUNT
echo $$ > $MUTEX

[ $DEBUG = 1 ] && echo "running first check"
first_try=`$CHECK_GALAXY $NEWHIST $1 2>&1`

if [ $? -ne 0 ]; then
    # if failure, wait and try again
    [ $DEBUG = 1 ] && echo "first check failed, sleeping $SLEEP seconds for second run"
    sleep $SLEEP
else
    # if successful
    [ $DEBUG = 1 ] && echo "first check succeeded"
    for file in $NOTIFIED_MAIL/* $NOTIFIED_PAGE/*; do
    	recip=`basename $file`
    	# the literal string including the * will be passed if the dir is empty
	[ "$recip" = '*' ] && continue
        echo "$1 is now okay" | mail -s "$1 OK" $recip
        rm -f $file
        [ $DEBUG = 1 ] && echo "up: mailed $recip"
    done
    rm -f $MUTEX $STAGGER_FILE
    exit 0
fi

[ $DEBUG = 1 ] && echo "running second check"
second_try=`$CHECK_GALAXY $NEWHIST $1 2>&1`

if [ $? -ne 0 ]; then
    [ $DEBUG = 1 ] && echo "second check failed"
    if [ $STAGGER = 1 ]; then
        if [ "$STAGGER_COUNT" -eq "$INTERVAL" ]; then
            # send notification this run
            echo 1 > $STAGGER_FILE
        else
            # don't send notification this run
	    [ $DEBUG = 1 ] && echo "$1 is down, but it's not time to send an email.  STAGGER_COUNT was $STAGGER_COUNT"
            expr $STAGGER_COUNT + 1 > $STAGGER_FILE
            rm -f $MUTEX
            exit 0
        fi
    fi
    for recip in $MAIL; do
        if [ ! -f "$NOTIFIED_MAIL/$recip" ]; then
            cat <<HERE | mail -s "$1 problems" $recip
$second_try
HERE
            touch "$NOTIFIED_MAIL/$recip"
            [ $DEBUG = 1 ] && echo "dn: mailed $recip"
            [ $STAGGER = 1 ] && break
        fi
    done
    for recip in $PAGE; do
        if [ ! -f "$NOTIFIED_PAGE/$recip" ]; then
            cat <<HERE | tail -1 | mail -s "$1 problems" $recip
$second_try
HERE
            touch "$NOTIFIED_PAGE/$recip"
            [ $DEBUG = 1 ] && echo "dn: mailed $recip"
            [ $STAGGER = 1 ] && break
        fi
    done
else
    [ $DEBUG = 1 ] && echo "second check succeeded"
    for file in $NOTIFIED_MAIL/* $NOTIFIED_PAGE/*; do
    	recip=`basename $file`
	[ "$recip" = '*' ] && continue
        echo "$1 is now okay" | mail -s "$1 OK" $recip
        rm -f $file
        [ $DEBUG = 1 ] && echo "up: mailed $recip"
    done
    rm -f $STAGGER_FILE
fi

rm -f $MUTEX
exit 0
