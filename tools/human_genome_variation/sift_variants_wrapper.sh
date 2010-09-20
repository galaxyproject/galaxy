#!/usr/bin/env bash

input_file=$1
output_file=$2
org=$3
db_loc=$4
chrom_col=$5
pos_col=$6
base=$7
allele_col=$8
strand_col=$9
output_opts=${10}

working_dir=$PWD
sift_input="$working_dir/sift_input.txt"
sift_output="$working_dir/sift_output.txt"


##
## get/check the db directory from the argument org,db_loc
##
db_dir=$( awk '$1 == org { print $2 }' org=$org $db_loc )

if [ -z "$db_dir" ]; then
    echo "Can't find dbkey \"$org\" in loc file \"$db_loc\"" 1>&2
    exit 1
fi

if [ ! -d "$db_dir" ]; then
    echo "Can't access SIFT database directory \"$db_dir\"" 1>&2
    exit 1
fi

##
## create input file for SIFT_exome_nssnvs.pl
##
if [ ! -r "$input_file" ]; then
    echo "Can't read input file \"$input_file\"" 1>&2
    exit 1
fi

if [ $base -eq 0 ]; then
    beg_col="$pos_col"
    end_col="$pos_col + 1"
    pos_adj='$2 = $2 - 1'
else
    beg_col="$pos_col - 1"
    end_col="$pos_col"
    pos_adj=''
fi

strand_cvt=''
if [ \( "$strand_col" = "+" \) ]; then
    strand='"1"'
elif [ \( "$strand_col" = "-" \) ]; then
    strand='"-1"'
else
    strand="\$$strand_col"
    strand_cvt='if ( '"${strand}"' == "+") { '"${strand}"' = "1" } else if ( '"${strand}"' == "-") { '"${strand}"' = "-1"}'
fi

awk '
BEGIN {FS="\t";OFS=","}
{
    $'"${chrom_col}"' = tolower($'"${chrom_col}"')
    sub(/^chr/, "", $'"${chrom_col}"')
    '"${strand_cvt}"'
    print $'"${chrom_col}"', $'"${beg_col}"', $'"${end_col}"', '"${strand}"', $'"${allele_col}"'
}
' "$input_file" > "$sift_input"

##
## run SIFT variants command line program
##
if [ "$output_opts" = "None" ]; then
    output_opts=""
else
    output_opts=$( echo "$output_opts" | sed -e 's/,/ 1 -/g' )
    output_opts="-$output_opts 1"
fi

SIFT_exome_nssnvs.pl -i "$sift_input" -d "$db_dir" -o "$working_dir" $output_opts &> "$sift_output"
if [ $? -ne 0 ]; then
  echo "failed: SIFT_exome_nssnvs.pl -i \"$sift_input\" -d \"$db_dir\" -o \"$working_dir\" $output_opts"
  exit 1
fi

##
## locate the output file
##
sift_pid=$( sed -n -e 's/^.*Your job id is \([0-9][0-9]*\) and is currently running.*$/\1/p' "$sift_output" )

if [ -z "$sift_pid" ]; then
  echo "Can't find SIFT pid in \"$sift_output\"" 1>&2
  exit 1
fi

sift_outdir="$working_dir/$sift_pid"
if [ ! -d "$sift_outdir" ]; then
    echo "Can't access SIFT output directory \"$sift_outdir\"" 1>&2
    exit 1
fi

sift_outfile="$sift_outdir/${sift_pid}_predictions.tsv"
if [ ! -r "$sift_outfile" ]; then
    echo "Can't access SIFT output file \"$sift_outfile\"" 1>&2
    exit 1
fi

##
## create output file
##
awk '
BEGIN {FS="\t";OFS="\t"}
NR == 1 {
    $12 = "Num seqs at position"
    $1 = "Chrom\tPosition\tStrand\tAllele"
    print
}
NR != 1 {
    $1 = "chr" $1
    gsub(/,/, "\t", $1)
    print
}
' "$sift_outfile" | awk '
BEGIN {FS="\t";OFS="\t"}
NR == 1 {
    print "#" $0
}
NR != 1 {
    if ($3 == "1") { $3 = "+" } else if ($3 == "-1") { $3 = "-" }
    '"${pos_adj}"'
    print
}
' > "$output_file"

##
## cleanup
##
rm -rf "$sift_outdir" "$sift_input" "$sift_output"

