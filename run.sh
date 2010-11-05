#!/bin/sh

cd `dirname $0`

python ./scripts/check_python.py
[ $? -ne 0 ] && exit 1

FROM_SAMPLE="
    datatypes_conf.xml
    reports_wsgi.ini
    tool_conf.xml
    tool_data_table_conf.xml
    universe_wsgi.ini
    tool-data/add_scores.loc
    tool-data/alignseq.loc
    tool-data/annotation_profiler_options.xml
    tool-data/annotation_profiler_valid_builds.txt
    tool-data/bfast_indexes.loc
    tool-data/binned_scores.loc
    tool-data/blastdb.loc
    tool-data/blastdb_p.loc
    tool-data/bowtie_indices.loc
    tool-data/bowtie_indices_color.loc
    tool-data/codingSnps.loc
    tool-data/encode_datasets.loc
    tool-data/funDo.loc
    tool-data/lastz_seqs.loc
    tool-data/liftOver.loc
    tool-data/maf_index.loc
    tool-data/maf_pairwise.loc
    tool-data/microbial_data.loc
    tool-data/phastOdds.loc
    tool-data/perm_base_index.loc
    tool-data/perm_color_index.loc
    tool-data/quality_scores.loc
    tool-data/regions.loc
    tool-data/sam_fa_indices.loc
    tool-data/sift_db.loc
    tool-data/srma_index.loc
    tool-data/twobit.loc
    tool-data/shared/ucsc/builds.txt
"

# Create any missing config/location files
for file in $FROM_SAMPLE; do
    if [ ! -f "$file" -a -f "$file.sample" ]; then
        echo "Initializing $file from `basename $file`.sample"
        cp $file.sample $file
    fi
done

# explicitly attempt to fetch eggs before running
FETCH_EGGS=1
for arg in "$@"; do
    [ "$arg" = "--stop-daemon" ] && FETCH_EGGS=0; break
done
if [ $FETCH_EGGS -eq 1 ]; then
    python ./scripts/check_eggs.py quiet
    if [ $? -ne 0 ]; then
        echo "Some eggs are out of date, attempting to fetch..."
        python ./scripts/fetch_eggs.py
        if [ $? -eq 0 ]; then
            echo "Fetch successful."
        else
            echo "Fetch failed."
            exit 1
        fi
    fi
fi

python ./scripts/paster.py serve universe_wsgi.ini $@
