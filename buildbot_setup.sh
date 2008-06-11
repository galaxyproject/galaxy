#!/bin/sh

cd `dirname $0`

LINKS="
/depot/data2/galaxy/alignseq.loc
/depot/data2/galaxy/binned_scores.loc
/depot/data2/galaxy/encode_datasets.loc
/home/universe/linux-i686/HYPHY
/depot/data2/galaxy/liftOver.loc
/depot/data2/galaxy/maf_index.loc
/depot/data2/galaxy/maf_pairwise.loc
/depot/data2/galaxy/microbes/microbial_data.loc
/depot/data2/galaxy/phastOdds.loc
/depot/data2/galaxy/quality_scores.loc
/depot/data2/galaxy/regions.loc
/depot/data2/galaxy/taxonomy
/depot/data2/galaxy/twobit.loc
"

SAMPLES="
datatypes_conf.xml.sample
"

for link in $LINKS; do
    echo "Linking $link"
    ln -sf $link tool-data
done

for sample in $SAMPLES; do
    file=`echo $sample | sed -e 's/\.sample$//'`
    echo "Copying $sample to $file"
    cp $sample $file
done

python ./scripts/fetch_eggs.py all
