#!/usr/bin/env bash
#
# Galaxy wrapper for Yu Zhang's BEAM2 adds two new options
#  significance=foo    renames significance.txt to foo after BEAM2 is run
#  posterior=bar       renames posterior.txt    to bar after BEAM2 is run
# 

set -e

export PATH=$PATH:$(dirname $0)

## options
significance=
posterior=
new_args=
map=
ped=

TFILE="/tmp/BEAM2.$$.tmp"

## separate significance and posterior arguments from arguments to BEAM2
until [ $# -eq 0 ]
do
  case $1 in
    significance=*)
      significance=${1#significance=}
      ;;
    posterior=*)
      posterior=${1#posterior=}
      ;;
    map=*)
      map=${1#map=}
      ;;
    ped=*)
      ped=${1#ped=}
      ;;
    *)
      if [ -z "$new_args" ]; then
        new_args=$1
      else
        new_args="$new_args $1"
      fi
      ;;
  esac

  shift
done

## convert input for use with BEAM2
lped_to_geno.pl $map $ped > $TFILE
if [ $? -ne 0 ]; then
  echo "failed: lped_to_geno.pl $map $ped > $TFILE"
  exit 1
fi

## run BEAM2
BEAM2 $TFILE $new_args 1>/dev/null
if [ $? -ne 0 ]; then
  echo "failed: BEAM2 $TFILE $new_args"
  exit 1
fi

mergeSnps.pl significance.txt $TFILE
if [ $? -ne 0 ]; then
  echo "failed: mergeSnps.pl significance.txt $TFILE"
  exit 1
fi

## move output files
mv significance.txt $significance
mv posterior.txt $posterior

## cleanup
rm -f $TFILE

