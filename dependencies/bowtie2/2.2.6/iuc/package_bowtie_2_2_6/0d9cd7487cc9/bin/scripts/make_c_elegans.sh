#!/bin/sh

#
# Downloads sequence and builds Bowtie index for for C. elegans
# versions WS200 from wormbase.
#

GENOMES_MIRROR=ftp://ftp.wormbase.org/pub/wormbase/species/c_elegans/sequence/genomic

BOWTIE_BUILD_EXE=./bowtie2-build
if [ ! -x "$BOWTIE_BUILD_EXE" ] ; then
	if ! which bowtie2-build ; then
		echo "Could not find bowtie2-build in current directory or in PATH"
		exit 1
	else
		BOWTIE_BUILD_EXE=`which bowtie2-build`
	fi
fi

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

F=c_elegans.WS235.genomic.fa
if [ ! -f $F ] ; then
	FGZ=$F.gz
	wget ${GENOMES_MIRROR}/$FGZ || (echo "Error getting $F" && exit 1)
	gunzip $FGZ || (echo "Error unzipping $F" && exit 1)
fi

CMD="${BOWTIE_BUILD_EXE} $* $F c_elegans_ws235"
echo "Running $CMD"
if $CMD ; then
	echo "c_elegans_ws235 index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi

