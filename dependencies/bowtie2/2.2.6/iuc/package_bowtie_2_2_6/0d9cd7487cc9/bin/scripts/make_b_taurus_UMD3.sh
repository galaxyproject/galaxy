#!/bin/sh

#
# Builds an index from UMD Freeze 3.0 of the Bos Taurus (cow) genome.
#

BASE_CHRS="\
Chr1 \
Chr2 \
Chr3 \
Chr4 \
Chr5 \
Chr6 \
Chr7 \
Chr8 \
Chr9 \
Chr10 \
Chr11 \
Chr12 \
Chr13 \
Chr14 \
Chr15 \
Chr16 \
Chr17 \
Chr18 \
Chr19 \
Chr20 \
Chr21 \
Chr22 \
Chr23 \
Chr24 \
Chr25 \
Chr26 \
Chr27 \
Chr28 \
Chr29 \
ChrX \
ChrU \
ChrY-contigs \
ChrY-contigs.SHOTGUN_ONLY"

CHRS_TO_INDEX=$BASE_CHRS

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

FTP_BASE=ftp://ftp.cbcb.umd.edu/pub/data/Bos_taurus/Bos_taurus_UMD_3.0
OUTPUT=b_taurus

INPUTS=
for c in $CHRS_TO_INDEX ; do
	if [ ! -f ${c}.fa ] ; then
		F=${c}.fa.gz
		get ${FTP_BASE}/$F || (echo "Error getting $F" && exit 1)
		gunzip $F || (echo "Error unzipping $F" && exit 1)
	fi
	[ -n "$INPUTS" ] && INPUTS=$INPUTS,${c}.fa
	[ -z "$INPUTS" ] && INPUTS=${c}.fa
done

CMD="$BOWTIE_BUILD_EXE $* $INPUTS $OUTPUT"
echo $CMD
if $CMD ; then
	echo "$OUTPUT index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
