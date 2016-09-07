#!/bin/sh

#
# Downloads sequence for H. sapiens (human) from NCBI.
#
# A relatively new directory structure (as of Oct 2011) seems to have collected
# all the relevant files in one directory (MT no longer separate) and
# eliminated the alternative haplotype assembles from the main directory
#
# It's generally a good idea to consult:
# ftp://ftp.ncbi.nlm.nih.gov/genbank/genomes/Eukaryotes/vertebrates_mammals/Homo_sapiens
# To check for updates to the assembly or the FTP directory structure.
#

BASE_CHRS="\
assembled_chromosomes/FASTA/chr1.fa \
assembled_chromosomes/FASTA/chr2.fa \
assembled_chromosomes/FASTA/chr3.fa \
assembled_chromosomes/FASTA/chr4.fa \
assembled_chromosomes/FASTA/chr5.fa \
assembled_chromosomes/FASTA/chr6.fa \
assembled_chromosomes/FASTA/chr7.fa \
assembled_chromosomes/FASTA/chr8.fa \
assembled_chromosomes/FASTA/chr9.fa \
assembled_chromosomes/FASTA/chr10.fa \
assembled_chromosomes/FASTA/chr11.fa \
assembled_chromosomes/FASTA/chr12.fa \
assembled_chromosomes/FASTA/chr13.fa \
assembled_chromosomes/FASTA/chr14.fa \
assembled_chromosomes/FASTA/chr15.fa \
assembled_chromosomes/FASTA/chr16.fa \
assembled_chromosomes/FASTA/chr17.fa \
assembled_chromosomes/FASTA/chr18.fa \
assembled_chromosomes/FASTA/chr19.fa \
assembled_chromosomes/FASTA/chr20.fa \
assembled_chromosomes/FASTA/chr21.fa \
assembled_chromosomes/FASTA/chr22.fa \
assembled_chromosomes/FASTA/chrX.fa \
assembled_chromosomes/FASTA/chrY.fa"

UNLOCALIZED="\
unlocalized_scaffolds/FASTA/chr1.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr4.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr7.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr8.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr9.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr11.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr17.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr18.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr19.unlocalized.scaf.fa \
unlocalized_scaffolds/FASTA/chr21.unlocalized.scaf.fa"

UNPLACED="unplaced_scaffolds/FASTA/unplaced.scaf.fa"

CHRS_TO_INDEX="$BASE_CHRS $UNLOCALIZED $UNPLACED"

FTP_BASE=ftp://ftp.ncbi.nlm.nih.gov/genbank/genomes/Eukaryotes/vertebrates_mammals/Homo_sapiens/GRCh37/Primary_Assembly

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
	cbase=`basename ${c}`
	if [ ! -f $cbase ] ; then
		F=${c}.gz
		get ${FTP_BASE}/$F || (echo "Error getting $F" && exit 1)
		gunzip ${cbase}.gz || (echo "Error unzipping ${cbase}.gz" && exit 1)
	fi
	[ -n "$INPUTS" ] && INPUTS=$INPUTS,$cbase
	[ -z "$INPUTS" ] && INPUTS=$cbase
done

echo Running ${BOWTIE_BUILD_EXE} $* ${INPUTS} h_sapiens_37_asm
${BOWTIE_BUILD_EXE} $* ${INPUTS} h_sapiens_37_asm

if [ "$?" = "0" ] ; then
	echo "h_sapiens_37_asm index built:"
	echo "   h_sapiens_37_asm.1.ebwt h_sapiens_37_asm.2.ebwt"
	echo "   h_sapiens_37_asm.3.ebwt h_sapiens_37_asm.4.ebwt"
	echo "   h_sapiens_37_asm.rev.1.ebwt h_sapiens_37_asm.rev.2.ebwt"
	echo "You may remove hs_ref_chr*.fa"
else
	echo "Index building failed; see error message"
fi
