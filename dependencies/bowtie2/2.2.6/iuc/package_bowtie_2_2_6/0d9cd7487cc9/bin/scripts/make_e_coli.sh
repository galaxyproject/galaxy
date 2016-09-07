#!/bin/sh

#
# Downloads the sequence for a strain of e. coli from NCBI and builds a
# Bowtie index for it
#

GENOMES_MIRROR=ftp://ftp.ncbi.nlm.nih.gov/genomes

BOWTIE_BUILD_EXE=./bowtie2-build
if [ ! -x "$BOWTIE_BUILD_EXE" ] ; then
	if ! which bowtie2-build ; then
		echo "Could not find bowtie2-build in current directory or in PATH"
		exit 1
	else
		BOWTIE_BUILD_EXE=`which bowtie2-build`
	fi
fi

if [ ! -f NC_008253.fna ] ; then
	if ! which wget > /dev/null ; then
		echo wget not found, looking for curl...
		if ! which curl > /dev/null ; then
			echo curl not found either, aborting...
		else
			# Use curl
			curl ${GENOMES_MIRROR}/Bacteria/Escherichia_coli_536_uid58531/NC_008253.fna -o NC_008253.fna
		fi
	else
		# Use wget
		wget ${GENOMES_MIRROR}/Bacteria/Escherichia_coli_536_uid58531/NC_008253.fna
	fi
fi

if [ ! -f NC_008253.fna ] ; then
	echo "Could not find NC_008253.fna file!"
	exit 2
fi

CMD="${BOWTIE_BUILD_EXE} $* -t 8 NC_008253.fna e_coli"
echo $CMD
if $CMD ; then
	echo "e_coli index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
