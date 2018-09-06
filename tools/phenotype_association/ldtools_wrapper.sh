#!/usr/bin/env bash
#
# Galaxy wrapper for Aakrosh Ratan's ldtools
# 

set -e

SCRIPT_DIR=$(dirname $0)

## pagetag options
input=
rsquare=0.64
freq=0.00
sample=###

## senatag options
excluded=###
required=###
output=

until [ $# -eq 0 ]
do
  case $1 in
    rsquare=*)
      rsquare=${1#rsquare=}
      ;;
    freq=*)
      freq=${1#freq=}
      ;;
    input=*)
      input=${1#input=}
      ;;
    output=*)
      output=${1#output=}
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

## run pagetag
python $SCRIPT_DIR/pagetag.py --rsquare $rsquare --freq $freq "$input" snps.txt neighborhood.txt
if [ $? -ne 0 ]; then
	echo "failed: pagetag.py --rsquare $rsquare --freq $freq \"$input\" snps.txt neighborhood.txt"
	exit 1
fi

## run sentag
python $SCRIPT_DIR/senatag.py neighborhood.txt snps.txt > "$output"
if [ $? -ne 0 ]; then
	echo "failed: senatag.py neighborhood.txt snps.txt"
	exit 1
fi

