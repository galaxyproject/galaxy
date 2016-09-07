#!/bin/sh

#
# Downloads sequence for a S. cerevisiae from CYGD.  This script
# was used to build the Bowtie index for S. cerevisiae.
#

GENOMES_MIRROR=ftp://ftpmips.gsf.de/yeast/sequences 

BOWTIE_BUILD_EXE=./bowtie2-build
if [ ! -x "$BOWTIE_BUILD_EXE" ] ; then
	if ! which bowtie2-build ; then
		echo "Could not find bowtie2-build in current directory or in PATH"
		exit 1
	else
		BOWTIE_BUILD_EXE=`which bowtie2-build`
	fi
fi

if [ ! -f Scerevisiae_chr.fna ] ; then
	if ! which wget > /dev/null ; then
		echo wget not found, looking for curl...
		if ! which curl > /dev/null ; then
			echo curl not found either, aborting...
		else
			# Use curl
			curl ${GENOMES_MIRROR}/Scerevisiae_chr -o Scerevisiae_chr.fna
		fi
	else
		# Use wget
		wget ${GENOMES_MIRROR}/Scerevisiae_chr
		mv Scerevisiae_chr Scerevisiae_chr.fna
	fi
fi

if [ ! -f Scerevisiae_chr.fna ] ; then
	echo "Could not find Scerevisiae_chr.fna file!"
	exit 2
fi

CMD="$BOWTIE_BUILD_EXE $* Scerevisiae_chr.fna s_cerevisiae"
echo $CMD
if $CMD ; then
	echo "s_cerevisiae index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
