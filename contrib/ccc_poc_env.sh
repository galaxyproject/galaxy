#!/bin/bash
export http_proxy=http://gateway:3128
export https_proxy=${http_proxy}
export ftp_proxy=${http_proxy}
export GALAXY_RUN_ALL=1
#Creating env variables for location of exe/jar files, to be used by xml/py files.
GENOMICS_DIR=/opt/sync/Genomics
CCC_SYNC_DIR=/cluster_share/ccc_sync
PYTHON_2_7_PATH=$CCC_SYNC_DIR/tools/galaxy/venv
source $PYTHON_2_7_PATH/bin/activate
export BWA_DIR=$GENOMICS_DIR/ohsu/dnapipeline/bwa-0.7.4
export BWA_EXE_PATH=$BWA_DIR/bwa
export SAMTOOLS_DIR=$GENOMICS_DIR/ohsu/dnapipeline/samtools-0.1.19
export SAMTOOLS_EXE_PATH=$SAMTOOLS_DIR/samtools
export SAMTOOLS_v020_EXE_PATH=$GENOMICS_DIR/ohsu/dnapipeline/samtools/samtools/samtools
export PICARD_PATH=$GENOMICS_DIR/ohsu/dnapipeline/picard-tools-1.110
export GATK_JAR_PATH=$GENOMICS_DIR/GATK-3.2/target/GenomeAnalysisTK.jar
#FIXME
export CP_PATH=$CCC_SYNC_DIR/tools/cellprofiler/cp_pipeline
export LABKEY_USERNAME=ccc@ccc.com
export LABKEY_PASSWORD=Intel123
export OMERO_IMAGE_SELECTION=$CCC_SYNC_DIR/tools/omero
#END FIXME
export SEATTLESEQ_GETANNOTATION_JAR_PATH=$GENOMICS_DIR/annotation/getAnnotation/project/
export SEATTLESEQ_WRITEGENOTYPE_JAR_PATH=$GENOMICS_DIR/annotation/writeGenotype/project/
export MUTECT_JAR_PATH=$GENOMICS_DIR/ohsu/dnapipeline/mutect-1.1.7.jar
export BOWTIE_TOOLS_EXE_PATH=$GENOMICS_DIR/ohsu/rnapipeline/bowtie2-2.1.0/
export TOPHAT_EXE_PATH=$GENOMICS_DIR/ohsu/rnapipeline/tophat-2.0.14/
export CUFFLINKS_TOOLS_EXE_PATH=$GENOMICS_DIR/ohsu/rnapipeline/cufflinks-2.2.1/
export CUFFDIFF_SCRIPT_PATH=$GENOMICS_DIR/ohsu/rnapipeline
export SNPEFF_JAR_PATH=$GENOMICS_DIR/annotation/snpEff/
export ONCOTATOR_PATH=$GENOMICS_DIR/annotation/Oncotator/oncotator-1.5.1.0/virt_test_env/bin/
export ONCOTATOR_DB_SOURCE=$CCC_SYNC_DIR/tools/Oncotator/oncotator_v1_ds_Jan262014/
export BREAKDANCER_PATH=$GENOMICS_DIR/ohsu/dnapipeline/breakdancer-1.4.5-unstable/
export PINDEL_PATH=$GENOMICS_DIR/ohsu/dnapipeline/pindel/
export PATH=$PINDEL_PATH:$BREAKDANCER_PATH:$TOPHAT_EXE_PATH:$CUFFLINKS_TOOLS_EXE_PATH:$BOWTIE_TOOLS_EXE_PATH:$GENOMICS_DIR:$BWA_DIR:$SAMTOOLS_DIR:$SAMTOOLS_v020_EXE_PATH:$PICARD_PATH:$PYTHON_2_7_PATH/bin:$PATH
export NSLOTS=16
export PYTHON_EGG_CACHE=.eggs_cache
export BIOBLEND_REPO_DIR=$CCC_SYNC_DIR/tools/galaxy/bioblend
export FASTQC_PERL_SCRIPT=$GENOMICS_DIR/ohsu/dnapipeline/FastQC/fastqc
export BCFTOOLS=$CCC_SYNC_DIR/tools/bcftools/bcftools
export TILEDB_IMPORT_EXE=$CCC_SYNC_DIR/tools/TileDB/example/bin/gt_example_loader
export GCC49_PREFIX_PATH=/opt/sync/softwares/compilers/gcc-4.9.1/
