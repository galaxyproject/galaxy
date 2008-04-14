#!/bin/sh

SAMPLES="
datatype_converters_conf.xml.sample
reports_wsgi.ini.sample
tool_conf.xml.sample
universe_wsgi.ini.sample
tool-data/alignseq.loc.sample
tool-data/binned_scores.loc.sample
tool-data/blastdb.loc.sample
tool-data/encode_datasets.loc.sample
tool-data/liftOver.loc.sample
tool-data/maf_index.loc.sample
tool-data/maf_pairwise.loc.sample
tool-data/microbial_data.loc.sample
tool-data/phastOdds.loc.sample
tool-data/quality_scores.loc.sample
tool-data/regions.loc.sample
tool-data/twobit.loc.sample
"

for sample in $SAMPLES; do
    file=`echo $sample | sed -e 's/\.sample$//'`
    if [ -f $file ]; then
        echo "Not overwriting existing $file"
    else
        echo "Copying $sample to $file"
        cp $sample $file
    fi
done

for dir in database/files database/tmp; do
    if [ ! -d $dir ]; then
        echo "Creating $dir"
        mkdir $dir
    fi
done

python ./scripts/fetch_eggs.py
