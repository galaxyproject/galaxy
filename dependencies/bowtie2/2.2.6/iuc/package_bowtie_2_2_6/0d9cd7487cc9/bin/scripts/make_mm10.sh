#!/bin/sh

#
# Downloads sequence for the mm10 version of M. musculus (mouse) from
# UCSC.
#
# Note that UCSC's mm10 build has two categories of compressed fasta
# files:
#
# 1. The base files, named chr??.fa.gz
# 2. The unplaced-sequence files, named chr??_random.fa.gz
#
# By default, this script indexes all these files.  To change which
# categories are built by this script, edit the CHRS_TO_INDEX
# variable below.
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
chrX \
chrY \
chrM"

RANDOM_CHRS="\
chr1_GL456210_random \
chr1_GL456211_random \
chr1_GL456212_random \
chr1_GL456213_random \
chr1_GL456221_random \
chr4_GL456216_random \
chr4_GL456350_random \
chr4_JH584292_random \
chr4_JH584293_random \
chr4_JH584294_random \
chr4_JH584295_random \
chr5_GL456354_random \
chr5_JH584296_random \
chr5_JH584297_random \
chr5_JH584298_random \
chr5_JH584299_random \
chr7_GL456219_random \
chrX_GL456233_random \
chrY_JH584300_random \
chrY_JH584301_random \
chrY_JH584302_random \
chrY_JH584303_random \
chrUn_GL456239 \
chrUn_GL456359 \
chrUn_GL456360 \
chrUn_GL456366 \
chrUn_GL456367 \
chrUn_GL456368 \
chrUn_GL456370 \
chrUn_GL456372 \
chrUn_GL456378 \
chrUn_GL456379 \
chrUn_GL456381 \
chrUn_GL456382 \
chrUn_GL456383 \
chrUn_GL456385 \
chrUn_GL456387 \
chrUn_GL456389 \
chrUn_GL456390 \
chrUn_GL456392 \
chrUn_GL456393 \
chrUn_GL456394 \
chrUn_GL456396 \
chrUn_JH584304"

CHRS_TO_INDEX="$BASE_CHRS $RANDOM_CHRS"

UCSC_MM10_BASE=ftp://hgdownload.cse.ucsc.edu/goldenPath/mm10/chromosomes

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
		get ${UCSC_MM10_BASE}/$F || (echo "Error getting $F" && exit 1)
		gunzip $F || (echo "Error unzipping $F" && exit 1)
	fi
	[ -n "$INPUTS" ] && INPUTS=$INPUTS,${c}.fa
	[ -z "$INPUTS" ] && INPUTS=${c}.fa
done

CMD="${BOWTIE_BUILD_EXE} $* ${INPUTS} mm10"
echo Running $CMD
if $CMD ; then
	echo "mm10 index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
