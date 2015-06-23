#!/bin/bash
PYTHON_2_7_PATH=/opt/python-2.7/
#export http_proxy=http://sparkdmz1:4000
#export https_proxy=${http_proxy}
#export ftp_proxy=${http_proxy}
#export no_proxy=cluster3.ccc.com,.cluster3.ccc.com,intel.com,.intel.com,10.0.0.0/8,192.168.0.0/16,localhost,127.0.0.0/8,134.134.0.0/16
export GALAXY_RUN_ALL=1
#Creating env variables for location of exe/jar files, to be used by xml/py files.
GENOMICS_DIR=/opt/Genomics
export BWA_DIR=$GENOMICS_DIR/ohsu/dnapipeline/bwa-0.7.4
export BWA_EXE_PATH=$BWA_DIR/bwa
export SAMTOOLS_DIR=$GENOMICS_DIR/ohsu/dnapipeline/samtools-0.1.19
export SAMTOOLS_EXE_PATH=$SAMTOOLS_DIR/samtools
export SAMTOOLS_v020_EXE_PATH=$GENOMICS_DIR/ohsu/dnapipeline/samtools/samtools/samtools
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
export SNPEFF_JAR_PATH=$GENOMICS_DIR/annotation/snpEff/
export ONCOTATOR_PATH=$GENOMICS_DIR/annotation/Oncotator/
export ONCOTATOR_DB_SOURCE=$GENOMICS_DIR/annotation/Oncotator/oncotator_v1_ds_Jan262014/
export BREAKDANCER_PATH=$GENOMICS_DIR/ohsu/dnapipeline/breakdancer-1.4.5-unstable/
export PINDEL_PATH=$GENOMICS_DIR/ohsu/dnapipeline/pindel/
export PATH=$PINDEL_PATH:$BREAKDANCER_PATH:$ONCOTATOR_DB_SOURCE:$ONCOTATOR_PATH:$TOPHAT_EXE_PATH:$CUFFLINKS_TOOLS_EXE_PATH:$BOWTIE_TOOLS_EXE_PATH:$GENOMICS_DIR:$BWA_DIR:$SAMTOOLS_DIR:$SAMTOOLS_v020_EXE_PATH:$PICARD_PATH:$PYTHON_2_7_PATH/bin:$PATH
export NSLOTS=16
export PYTHON_EGG_CACHE=.eggs_cache
export CCC_DRMAA_PYTHON_MODULE_DIRECTORY=/mnt/app_hdd/CCC_central/testDRMAA/
export PYTHONPATH=${CCC_DRMAA_PYTHON_MODULE_DIRECTORY}:$PYTHONPATH
export OMERO_IMAGE_SELECTION=/cluster_share/omero
export BIOBLEND_REPO_DIR=/cluster_share/Galaxy/api/bioblend
export FASTQC_PERL_SCRIPT=/opt/Genomics/ohsu/dnapipeline/FastQC/fastqc
export BCFTOOLS=/home/karthikg/broad/non_variant_db/bcftools/bcftools
export TILEDB_IMPORT_EXE=/home/karthikg/broad/non_variant_db/variantDB/TileDB/example/bin/gt_example_loader
export GCC49_PREFIX_PATH=/opt/gcc-4.9.1
