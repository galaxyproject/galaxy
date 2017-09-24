#!/bin/bash

ped=$1
dat=$2
type=$3

[ "$3" = "" ] && echo "Generates and runs an allegro configuration file based on input parameters.

  `basename $0` <pedigree file> <data file> <[TYPE]>

where TYPE is a string of optional parameters as defined by the Allegro manual, that MUST contain one of:

  MODEL mpt par het
  HAPLOTYPES" && exit -1

# sanity check
has_link=`echo "$type" | grep "MODEL mpt par het"`
has_hapl=`echo "$type" | grep "HAPLOTYPES"`

[ "$has_link" = "" ] && [ "$has_hapl" = "" ]\
    && echo "Type of analysis not specified" && exit -1

# Generate conf
allegro_in=`mktmp`

cat << EOF >> $allegro_in
PREFILE "$ped"
DATFILE "$dat"

"$type"
MAXMEMORY 1200
EOF

./allegro $allegro_in
