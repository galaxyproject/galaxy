#!/bin/sh

#
# Downloads sequence for the hg19 version of H. spiens (human) from
# UCSC.
#
# Note that UCSC's hg19 build has three categories of compressed fasta
# files:
#
# 1. The base files, named chr??.fa.gz
# 2. The unplaced-sequence files, named chr??_gl??????_random.fa.gz
# 3. The alternative-haplotype files, named chr??_?????_hap?.fa.gz
#
# By default, this script indexes files from categories 1 and 2.  To
# change which categories are built by this script, edit the
# CHRS_TO_INDEX variable below.
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
chr20 \
chr21 \
chr22 \
chrX \
chrY \
chrM"

RANDOM_CHRS="\
chr1_gl000191_random \
chr1_gl000192_random \
chr4_gl000193_random \
chr4_gl000194_random \
chr7_gl000195_random \
chr8_gl000196_random \
chr8_gl000197_random \
chr9_gl000198_random \
chr9_gl000199_random \
chr9_gl000200_random \
chr9_gl000201_random \
chr11_gl000202_random \
chr17_gl000203_random \
chr17_gl000204_random \
chr17_gl000205_random \
chr17_gl000206_random \
chr18_gl000207_random \
chr19_gl000208_random \
chr19_gl000209_random \
chr21_gl000210_random \
chrUn_gl000211 \
chrUn_gl000212 \
chrUn_gl000213 \
chrUn_gl000214 \
chrUn_gl000215 \
chrUn_gl000216 \
chrUn_gl000217 \
chrUn_gl000218 \
chrUn_gl000219 \
chrUn_gl000220 \
chrUn_gl000221 \
chrUn_gl000222 \
chrUn_gl000223 \
chrUn_gl000224 \
chrUn_gl000225 \
chrUn_gl000226 \
chrUn_gl000227 \
chrUn_gl000228 \
chrUn_gl000229 \
chrUn_gl000230 \
chrUn_gl000231 \
chrUn_gl000232 \
chrUn_gl000233 \
chrUn_gl000234 \
chrUn_gl000235 \
chrUn_gl000236 \
chrUn_gl000237 \
chrUn_gl000238 \
chrUn_gl000239 \
chrUn_gl000240 \
chrUn_gl000241 \
chrUn_gl000242 \
chrUn_gl000243 \
chrUn_gl000244 \
chrUn_gl000245 \
chrUn_gl000246 \
chrUn_gl000247 \
chrUn_gl000248 \
chrUn_gl000249"

ALT_HAP_CHRS="\
chr4_ctg9_hap1 \
chr6_apd_hap1 \
chr6_cox_hap2 \
chr6_dbb_hap3 \
chr6_mann_hap4 \
chr6_mcf_hap5 \
chr6_qbl_hap6 \
chr6_ssto_hap7 \
chr17_ctg5_hap1"

CHRS_TO_INDEX="$BASE_CHRS $RANDOM_CHRS"

UCSC_HG19_BASE=ftp://hgdownload.cse.ucsc.edu/goldenPath/hg19/chromosomes

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
		get ${UCSC_HG19_BASE}/$F || (echo "Error getting $F" && exit 1)
		gunzip $F || (echo "Error unzipping $F" && exit 1)
	fi
	[ -n "$INPUTS" ] && INPUTS=$INPUTS,${c}.fa
	[ -z "$INPUTS" ] && INPUTS=${c}.fa
done

CMD="${BOWTIE_BUILD_EXE} $* ${INPUTS} hg19"
echo Running $CMD
if $CMD ; then
	echo "hg19 index built; you may remove fasta files"
else
	echo "Index building failed; see error message"
fi
