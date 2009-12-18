#!/bin/sh

cd `dirname $0`

: ${HOSTTYPE:=`uname -m`}

# link to HYPHY is arch-dependent
case "$OSTYPE" in
    linux-gnu)
        kernel=`uname -r | cut -f1,2 -d.`
        HYPHY="/galaxy/software/linux$kernel-$HOSTTYPE/hyphy"
        ;;
esac

LINKS="
/depot/data2/galaxy/alignseq.loc
/depot/data2/galaxy/binned_scores.loc
/depot/data2/galaxy/blastdb.loc
/depot/data2/galaxy/bowtie_indices.loc
/depot/data2/galaxy/encode_datasets.loc
/galaxy/home/universe/encode_feature_partitions
/depot/data2/galaxy/lastz_seqs.loc
/depot/data2/galaxy/liftOver.loc
/depot/data2/galaxy/maf_index.loc
/depot/data2/galaxy/maf_pairwise.loc
/depot/data2/galaxy/microbes/microbial_data.loc
/depot/data2/galaxy/phastOdds.loc
/depot/data2/galaxy/quality_scores.loc
/depot/data2/galaxy/regions.loc
/depot/data2/galaxy/sam_fa_indices.loc
/depot/data2/galaxy/sequence_index_base.loc
/depot/data2/galaxy/sequence_index_color.loc
/depot/data2/galaxy/taxonomy
/depot/data2/galaxy/twobit.loc
"

SAMPLES="
datatypes_conf.xml.sample
universe_wsgi.ini.sample
"

DIRS="
database
database/files
database/tmp
database/compiled_templates
database/job_working_directory
database/import
database/pbs
"

for link in $LINKS; do
    echo "Linking $link"
    ln -sf $link tool-data
done

if [ -d "$HYPHY" ]; then
    echo "Linking $HYPHY"
    ln -sf $HYPHY tool-data/HYPHY
fi

for sample in $SAMPLES; do
    file=`echo $sample | sed -e 's/\.sample$//'`
    echo "Copying $sample to $file"
    cp $sample $file
done

for dir in $DIRS; do
    if [ ! -d $dir ]; then
        echo "Creating $dir"
        mkdir $dir
    fi
done

python ./scripts/fetch_eggs.py all
