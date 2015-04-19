#!/bin/bash
PYTHON_2_7_PATH=/opt/installed/python-2.7.8
export GALAXY_RUN_ALL=1
#Creating env variables for location of exe/jar files, to be used by xml/py files.
GENOMICS_DIR=/opt/installed
export BWA_DIR=$GENOMICS_DIR
export BWA_EXE_PATH=$BWA_DIR/bwa
export SAMTOOLS_DIR=$GENOMICS_DIR
export SAMTOOLS_EXE_PATH=$SAMTOOLS_DIR/samtools
export PICARD_PATH=/opt/installed/picard/picard-tools-1.110/
export GATK_JAR_PATH=$GENOMICS_DIR/GATK/GenomeAnalysisTK-3.2.jar
export CP_PATH=/mnt/app_hdd/imaging/cp_pipeline
export SEATTLESEQ_GETANNOTATION_JAR_PATH=/opt/installed/SeattleSeq_tools/
export SEATTLESEQ_WRITEGENOTYPE_JAR_PATH=/opt/installed/SeattleSeq_tools/
export MUTECT_JAR_PATH=$GENOMICS_DIR/ohsu/dnapipeline/mutect-1.1.7.jar	#does not exist
export BOWTIE_TOOLS_EXE_PATH=$GENOMICS_DIR
export TOPHAT_EXE_PATH=$GENOMICS_DIR
export CUFFLINKS_TOOLS_EXE_PATH=$GENOMICS_DIR
export CUFFDIFF_SCRIPT_PATH=/opt/Genomics/ohsu/rnapipeline	#does not exist
export PATH=$TOPHAT_EXE_PATH:$CUFFLINKS_TOOLS_EXE_PATH:$BOWTIE_TOOLS_EXE_PATH:$GENOMICS_DIR:$BWA_DIR:$SAMTOOLS_DIR:$PICARD_PATH:$PYTHON_2_7_PATH/bin:$PATH
export LD_LIBRARY_PATH=/opt/installed/lib:$LD_LIBRARY_PATH
export NSLOTS=16
export PYTHON_EGG_CACHE=.eggs_cache

