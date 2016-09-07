#!/bin/sh

#
# Downloads sequence for the hg18 version of H. spiens (human) from
# UCSC.
#
# Note that UCSC's hg18 build has three categories of compressed fasta
# files:
#
# 1. The base files, named chr??.fa.gz
# 2. The unplaced-sequence files, named chr??_random.fa.gz
# 3. The alternative-haplotype files, named chr??_???_hap?.fa.gz
#
# By default, this script indexes files from categories 1 and 2.  To
# change which categories are built by this script, edit the
# CHRS_TO_INDEX variable below.
#

BASE_CHRS="\
chr1 \
chr2 \
chr3 \
chr4 \
chr5 \
chr6 \
chr7 \
chr8 \
chr9 \
chr10 \
chr11 \
chr12 \
chr13 \
chr14 \
chr15 \
chr16 \
chr17 \
chr18 \
chr19 \
chr20 \
chr21 \
chr22 \
chrX \
chrY \
chrM"

RANDOM_CHRS="\
chr1_random \
chr2_random \
chr3_random \
chr4_random \
chr5_random \
chr6_random \
chr7_random \
chr8_random \
chr9_random \
chr10_random \
chr11_random \
chr13_random \
chr15_random \
chr16_random \
chr17_random \
chr18_random \
chr19_random \
chr21_random \
chr22_random \
chrX_random"

ALT_HAP_CHRS="\
chr22_h2_hap1 \
chr5_h2_hap1 \
chr6_cox_hap1 \
chr6_qbl_hap2"

CHRS_TO_INDEX="$BASE_CHRS $RANDOM_CHRS"

UCSC_HG18_BASE=ftp://hgdownload.cse.ucsc.edu/goldenPath/hg18/chromosomes

get() {
	file=$1
	if ! wget --version >/dev/null 2>/dev/null ; then
		if ! curl --version >/dev/null 2>/dev/null ; then
			echo "Please install wget or curl somewhere in your PATH"
			exit 1
		fi
		curl -o `basename $1` $1
		return $?
	else
		wget $1
		return $?
	fi
}

BOWTIE_BUILD_EXE=./bowtie2-build
if [ ! -x "$BOWTIE_BUILD_EXE" ] ; then
	if ! which bowtie2-build ; then
		echo "Could not find bowtie2-build in current directory or in PATH"
		exit 1
	else
		BOWTIE_BUILD_EXE=`which bowtie2-build`
	fi
fi

INPUTS=
for c in $CHRS_TO_INDEX ; do
	if [ ! -f ${c}.fa ] ; then
		F=${c}.fa.gz
		get ${UCSC_HG18_BASE}/$F || (echo "Error getting $F" && exit 1)
		gunzip $F || (echo "Error unzipping $F" && exit 1)
	fi
	[ -n "$INPUTS" ] && INPUTS=$INPUTS,${c}.fa
	[ -z "$INPUTS" ] && INPUTS=${c}.fa
done

CMD="${BOWTIE_BUILD_EXE} $* ${INPUTS} hg18"
echo Running $CMD
if $CMD ; then
	echo "hg18 index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
