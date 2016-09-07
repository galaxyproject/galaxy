#!/bin/sh

#
# Downloads assembled sequence for M. musculus (mouse) from NCBI.
#
# From README_CURRENT_BUILD:
#  Organism: Mus musculus (mouse)
#  NCBI Build Number: 37
#  Version: 1
#  Release date: 05 July 2007
#

M_MUS_FTP=ftp://ftp.ncbi.nih.gov/genomes/M_musculus/Assembled_chromosomes
M_MUS_MT_FTP=ftp://ftp.ncbi.nih.gov/genomes/M_musculus/CHR_MT
OUTPUT=m_musculus_ncbi37

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
append() {
	[ -n "$INPUTS" ] && INPUTS=$INPUTS,$1
	[ -z "$INPUTS" ] && INPUTS=$1
}

for c in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 X Y ; do
	F=mm_ref_chr$c.fa
	if [ ! -f mm_ref_chr$c.fa ] ; then
		FGZ=$F.gz
		get $M_MUS_FTP/$FGZ || (echo "Error getting $FGZ" && exit 1)
		gunzip $FGZ || (echo "Error unzipping $FGZ" && exit 1)
	fi
	append $F
done

F=mm_ref_chrMT.fa
if [ ! -f mm_ref_chrMT.fa ] ; then
	FGZ=$F.gz
	get $M_MUS_MT_FTP/$FGZ  || (echo "Error getting $FGZ" && exit 1)
	gunzip $FGZ || (echo "Error unzipping $FGZ" && exit 1)
fi
append $F

CMD="$BOWTIE_BUILD_EXE $* $INPUTS $OUTPUT"
echo $CMD
if $CMD ; then
	echo "$OUTPUT index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
