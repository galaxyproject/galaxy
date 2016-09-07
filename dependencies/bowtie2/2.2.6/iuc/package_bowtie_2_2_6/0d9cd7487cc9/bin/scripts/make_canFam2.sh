#!/bin/sh

#
# Downloads sequence for the canFam2 version of C. familiaris (dog)
# from UCSC.
#

i=2
BASE_CHRS=chr1
while [ $i -lt 39 ] ; do
	BASE_CHRS="$BASE_CHRS chr$i"
	i=`expr $i + 1`
done
BASE_CHRS="$BASE_CHRS chrX chrM chrUn"
CHRS_TO_INDEX=$BASE_CHRS

CANFAM2_BASE=ftp://hgdownload.cse.ucsc.edu/goldenPath/canFam2/chromosomes

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
		get ${CANFAM2_BASE}/$F || (echo "Error getting $F" && exit 1)
		gunzip $F || (echo "Error unzipping $F" && exit 1)
	fi
	[ -n "$INPUTS" ] && INPUTS=$INPUTS,${c}.fa
	[ -z "$INPUTS" ] && INPUTS=${c}.fa
done

CMD="${BOWTIE_BUILD_EXE} $* ${INPUTS} canFam2"
echo Running $CMD
if $CMD ; then
	echo "canFam2 index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
