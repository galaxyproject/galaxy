#!/usr/bin/env bash
#
# Galaxy wrapper for Yu Zhang's BEAM2 adds two new options
#  significance=foo    renames significance.txt to foo after BEAM2 is run
#  posterior=bar       renames posterior.txt    to bar after BEAM2 is run
# 

set -e

export PATH=$PATH:$(dirname $0)

significance=
posterior=
new_args=
map=
ped=
TFILE="/tmp/BEAM2.$$.tmp"

## separate significance and posterior arguments from arguments to BEAM2
until [ $# -eq 0 ]
do
	if [[ $1 =~ "^significance=" ]]; then
		significance=${1#significance=}
	elif [[ $1 =~ "^posterior=" ]]; then
		posterior=${1#posterior=}
	elif [[ $1 =~ "^map=" ]]; then
		map=${1#map=}
	elif [[ $1 =~ "^ped=" ]]; then
		ped=${1#ped=}
	else
		if [ -z "$new_args" ]; then
			new_args=$1
		else
			new_args="$new_args $1"
		fi
	fi

	shift
done

lped_to_geno.pl $map $ped > $TFILE
BEAM2 $TFILE $new_args 1>/dev/null
mergeSnps.pl significance.txt $TFILE
mv significance.txt $significance
mv posterior.txt $posterior
rm $TFILE

