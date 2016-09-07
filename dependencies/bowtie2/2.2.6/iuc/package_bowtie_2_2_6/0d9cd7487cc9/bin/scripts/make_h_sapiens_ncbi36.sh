#!/bin/sh

#
# Downloads sequence for H. sapiens (human) from NCBI.  This script was
# used to build the Bowtie index for H. sapiens.
#
# From README_CURRENT_BUILD:
#  Organism: Homo sapiens (human)
#  NCBI Build Number: 36
#  Version: 3
#  Release date: 24 March 2008
#

GENOMES_MIRROR=ftp://ftp.ncbi.nih.gov/genomes
FILE_PATH=${GENOMES_MIRROR}/H_sapiens/ARCHIVE/BUILD.36.3/Assembled_chromosomes

BOWTIE_BUILD_EXE=./bowtie2-build
if [ ! -x "$BOWTIE_BUILD_EXE" ] ; then
	if ! which bowtie2-build ; then
		echo "Could not find bowtie2-build in current directory or in PATH"
		exit 1
	else
		BOWTIE_BUILD_EXE=`which bowtie2-build`
	fi
fi

for c in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 X Y ; do
	if [ ! -f hs_ref_chr$c.fa ] ; then
		if ! which wget > /dev/null ; then
			echo wget not found, looking for curl...
			if ! which curl > /dev/null ; then
				echo curl not found either, aborting...
			else
				# Use curl
				curl ${FILE_PATH}/hs_ref_chr$c.fa.gz
			fi
		else
			# Use wget
			wget ${FILE_PATH}/hs_ref_chr$c.fa.gz
		fi
		gunzip hs_ref_chr$c.fa.gz
	fi
	
	if [ ! -f hs_ref_chr$c.fa ] ; then
		echo "Could not find hs_ref_chr$c.fa file!"
		exit 2
	fi
done

# Special case: get mitochondrial DNA from its home
if [ ! -f hs_ref_chrMT.fa ] ; then
	if ! which wget > /dev/null ; then
		echo wget not found, looking for curl...
		if ! which curl > /dev/null ; then
			echo curl not found either, aborting...
		else
			# Use curl
			curl ${GENOMES_MIRROR}/H_sapiens/CHR_MT/hs_ref_chrMT.fa.gz
		fi
	else
		# Use wget
		wget ${GENOMES_MIRROR}/H_sapiens/CHR_MT/hs_ref_chrMT.fa.gz
	fi
	gunzip hs_ref_chrMT.fa.gz
fi

INPUTS=hs_ref_chr1.fa,hs_ref_chr2.fa,hs_ref_chr3.fa,hs_ref_chr4.fa,hs_ref_chr5.fa,hs_ref_chr6.fa,hs_ref_chr7.fa,hs_ref_chr8.fa,hs_ref_chr9.fa,hs_ref_chr10.fa,hs_ref_chr11.fa,hs_ref_chr12.fa,hs_ref_chr13.fa,hs_ref_chr14.fa,hs_ref_chr15.fa,hs_ref_chr16.fa,hs_ref_chr17.fa,hs_ref_chr18.fa,hs_ref_chr19.fa,hs_ref_chr20.fa,hs_ref_chr21.fa,hs_ref_chr22.fa,hs_ref_chrMT.fa,hs_ref_chrX.fa,hs_ref_chrY.fa

echo Running ${BOWTIE_BUILD_EXE} $* ${INPUTS} h_sapiens_asm
${BOWTIE_BUILD_EXE} $* ${INPUTS} h_sapiens_asm

if [ "$?" = "0" ] ; then
	echo "h_sapiens_asm index built:"
	echo "   h_sapiens_asm.1.ebwt h_sapiens_asm.2.ebwt"
	echo "   h_sapiens_asm.3.ebwt h_sapiens_asm.4.ebwt"
	echo "   h_sapiens_asm.rev.1.ebwt h_sapiens_asm.rev.2.ebwt"
	echo "You may remove hs_ref_chr*.fa"
else
	echo "Index building failed; see error message"
fi
