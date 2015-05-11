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
export CP_PATH=/cluster_share/cp_pipeline
export LABKEY_USERNAME=ccc@ccc.com
export LABKEY_PASSWORD=Intel123
export SEATTLESEQ_GETANNOTATION_JAR_PATH=/opt/Genomics/annotation/getAnnotation/project/
export SEATTLESEQ_WRITEGENOTYPE_JAR_PATH=/opt/Genomics/annotation/writeGenotype/project/
export MUTECT_JAR_PATH=$GENOMICS_DIR/ohsu/dnapipeline/mutect-1.1.7.jar
export BOWTIE_TOOLS_EXE_PATH=$GENOMICS_DIR/ohsu/rnapipeline/bowtie2-2.1.0/
export TOPHAT_EXE_PATH=$GENOMICS_DIR/ohsu/rnapipeline/tophat-2.0.14/
export CUFFLINKS_TOOLS_EXE_PATH=$GENOMICS_DIR/ohsu/rnapipeline/cufflinks-2.2.1/
export CUFFDIFF_SCRIPT_PATH=/opt/Genomics/ohsu/rnapipeline
export PATH=$TOPHAT_EXE_PATH:$CUFFLINKS_TOOLS_EXE_PATH:$BOWTIE_TOOLS_EXE_PATH:$GENOMICS_DIR:$BWA_DIR:$SAMTOOLS_DIR:$PICARD_PATH:$PYTHON_2_7_PATH/bin:$PATH
export NSLOTS=16
export PYTHON_EGG_CACHE=.eggs_cache

