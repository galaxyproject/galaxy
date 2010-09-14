#!/usr/bin/env bash
#
# Galaxy wrapper for Aakrosh Ratan's ldtools
# 

set -e

# pagetag options
input=
rsquare=0.64
freq=0.00
sample=###

# senatag options
excluded=###
required=###
output=

until [ $# -eq 0 ]
do
    if [[ $1 =~ "^rsquare=" ]]; then
        rsquare=${1#rsquare=}
    elif [[ $1 =~ "^freq=" ]]; then
        freq=${1#freq=}
    elif [[ $1 =~ "^input=" ]]; then
        input=${1#input=}
    elif [[ $1 =~ "^output=" ]]; then
        output=${1#output=}
    else
        if [ -z "$new_args" ]; then
            new_args=$1
        else
            new_args="$new_args $1"
        fi
    fi

    shift
done

pagetag.py --rsquare $rsquare --freq $freq $input snps.txt neighborhood.txt 2> /dev/null
senatag.py neighborhood.txt snps.txt > $output 2> /dev/null
rm -f snps.txt neighborhood.txt

