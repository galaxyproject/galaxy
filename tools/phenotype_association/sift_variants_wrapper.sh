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
comment_col=${10}
output_opts=${11}

working_dir=$PWD
sift_input="$working_dir/sift_input.txt"
sift_output="$working_dir/sift_output.txt"

################################################################################
## make sure input file column selections are mutually exclusive              ##
################################################################################
ERROR=0
declare -a col_use

function check_col () {
    local col=$1
    local use=$2
    local int=$3

    if [ -n "${col//[0-9]}" ]; then
        if [ $int -eq 1 ]; then
            echo "ERROR: invalid value for $use column: $col" 1>&2
            ERROR=1
        fi
        return
    fi

    local cur=${col_use[$col]}
    if [ -n "$cur" ]; then
        echo "ERROR: $use column is the same as $cur column" 1>&2
        col_use[$col]="${cur},$use"
        ERROR=1
    else
        col_use[$col]=$use
    fi
}

check_col $chrom_col   'chromosome' 1
check_col $pos_col     'position'   1
check_col $allele_col  'allele'     1
check_col $strand_col  'strand'     0
check_col $comment_col 'comment'    0

if [ $ERROR -ne 0 ]; then
    exit 1
fi

################################################################################
## get/check the db directory from the argument org,db_loc                    ##
################################################################################
db_dir=$( awk '$1 == org { print $2 }' org=$org $db_loc )

if [ -z "$db_dir" ]; then
    echo "Can't find dbkey \"$org\" in loc file \"$db_loc\"" 1>&2
    exit 1
fi

if [ ! -d "$db_dir" ]; then
    echo "Can't access SIFT database directory \"$db_dir\"" 1>&2
    exit 1
fi

################################################################################
## create input file for SIFT_exome_nssnvs.pl                                 ##
################################################################################
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
    strand_cvt='if ('"${strand}"' == "+") {'"${strand}"' = "1"} else if ('"${strand}"' == "-") {'"${strand}"' = "-1"}'
fi

print_row='print $'"${chrom_col}"', $'"${beg_col}"', $'"${end_col}"', '"${strand}"', $'"${allele_col}"''
if [ "$comment_col" != "-" ]; then
    print_row=''"${print_row}"', $'"${comment_col}"''
fi

awk '
BEGIN {FS="\t";OFS=","}
$'"${chrom_col}"' ~ /^[cC][hH][rR]/ {$'"${chrom_col}"' = substr($'"${chrom_col}"',4)}
{
    '"${strand_cvt}"'
    '"${print_row}"'
}
' "$input_file" > "$sift_input"

################################################################################
## run SIFT_exome_nssnvs.pl command line program                              ##
################################################################################
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

################################################################################
## locate the SIFT_exome_nssnvs.pl output file                                ##
################################################################################
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

################################################################################
## create galaxy output file                                                  ##
################################################################################
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
    if ($3 == "1") {$3 = "+"} else if ($3 == "-1") {$3 = "-"}
    '"${pos_adj}"'
    print
}
' > "$output_file"

################################################################################
## cleanup                                                                    ##
################################################################################
rm -rf "$sift_outdir" "$sift_input" "$sift_output"

