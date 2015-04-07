#!/bin/bash
PYTHON_2_7_PATH=/opt/python-2.7/
export http_proxy=http://sparkdmz1:4000
export https_proxy=${http_proxy}
export ftp_proxy=${http_proxy}
export GALAXY_RUN_ALL=1
#Creating env variables for location of exe/jar files, to be used by xml/py files.
GENOMICS_DIR=/opt/Genomics
export BWA_DIR=$GENOMICS_DIR/ohsu/dnapipeline/bwa-0.7.4
export BWA_EXE_PATH=$BWA_DIR/bwa
export SAMTOOLS_DIR=$GENOMICS_DIR/ohsu/dnapipeline/samtools-0.1.19
export SAMTOOLS_EXE_PATH=$SAMTOOLS_DIR/samtools
export PICARD_PATH=$GENOMICS_DIR/ohsu/dnapipeline/picard-tools-1.110
export GATK_JAR_PATH=/opt/gsa-unstable/target/GenomeAnalysisTK.jar
export CP_PATH=/mnt/app_hdd/imaging/cp_pipeline
export SEATTLESEQ_GETANNOTATION_JAR_PATH=/opt/Genomics/annotation/getAnnotation/project/
export SEATTLESEQ_WRITEGENOTYPE_JAR_PATH=/opt/Genomics/annotation/writeGenotype/project/
export MUTECT_JAR_PATH=$GENOMICS_DIR/ohsu/dnapipeline/mutect-1.1.7.jar
export PATH=$GENOMICS_DIR:$BWA_DIR:$SAMTOOLS_DIR:$PICARD_PATH:$PYTHON_2_7_PATH/bin:$PATH
export NSLOTS=16
export PYTHON_EGG_CACHE=.eggs_cache
