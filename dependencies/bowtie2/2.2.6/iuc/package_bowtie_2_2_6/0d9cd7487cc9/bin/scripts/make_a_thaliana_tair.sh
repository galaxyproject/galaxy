#!/bin/sh

#
# Downloads sequence for A. thaliana from TAIR v10 and build Bowtie 2 index.
#

GENOMES_MIRROR=ftp://ftp.arabidopsis.org/home/tair

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

FC=
for c in 1 2 3 4 5 C M ; do
	if [ ! -f TAIR10_chr$c.fas ] ; then
		FN=TAIR10_chr$c.fas
		F=${GENOMES_MIRROR}/Sequences/whole_chromosomes/${FN}
		[ -n "$FC" ] && FC="$FC,$FN"
		[ -z "$FC" ] && FC=$FN
		get $F || (echo "Error getting $F" && exit 1)
	fi
	
	if [ ! -f TAIR10_chr$c.fas ] ; then
		echo "Could not find chr$c.fas file!"
		exit 2
	fi
done

CMD="${BOWTIE_BUILD_EXE} $* $FC a_thaliana"
echo $CMD
if $CMD ; then
	echo "a_thaliana index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
