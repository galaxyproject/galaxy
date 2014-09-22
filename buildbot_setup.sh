#!/bin/sh

cd `dirname $0`

: ${HOSTTYPE:=`uname -m`}

LINKS="
/galaxy/data/location/add_scores.loc
/galaxy/data/location/all_fasta.loc
/galaxy/data/location/alignseq.loc
/galaxy/data/annotation_profiler
/galaxy/data/annotation_profiler/annotation_profiler.loc
/galaxy/data/annotation_profiler/annotation_profiler_options.xml
/galaxy/data/annotation_profiler/annotation_profiler_valid_builds.txt
/galaxy/data/location/bfast_indexes.loc
/galaxy/data/location/binned_scores.loc
/galaxy/data/location/blastdb.loc
/galaxy/data/location/bowtie_indices.loc
/galaxy/data/location/bowtie_indices_color.loc
/galaxy/data/location/bwa_index.loc
/galaxy/data/location/bwa_index_color.loc
/galaxy/data/location/ccat_configurations.loc
/galaxy/data/location/codingSnps.loc
/galaxy/data/location/encode_datasets.loc
/galaxy/home/universe/encode_feature_partitions
/galaxy/data/location/lastz_seqs.loc
/galaxy/data/location/liftOver.loc
/galaxy/data/location/maf_index.loc
/galaxy/data/location/maf_pairwise.loc
/galaxy/data/location/microbial_data.loc
/galaxy/data/location/mosaik_index.loc
/galaxy/data/location/perm_base_index.loc
/galaxy/data/location/perm_color_index.loc
/galaxy/data/location/phastOdds.loc
/galaxy/data/location/picard_index.loc
/galaxy/data/location/quality_scores.loc
/galaxy/data/location/regions.loc
/galaxy/data/location/sam_fa_indices.loc
/galaxy/data/location/srma_index.loc
/galaxy/data/taxonomy
/galaxy/data/location/twobit.loc
/galaxy/software/tool-data/gatk
"

SAMPLES="
config/galaxy.ini.sample
config/shed_tool_data_table_conf.xml.sample
config/migrated_tools_conf.xml.sample
config/shed_data_manager_conf.xml.sample
tool-data/shared/igv/igv_build_sites.txt.sample
tool-data/shared/rviewer/rviewer_build_sites.txt.sample
tool-data/shared/ucsc/builds.txt.sample
tool-data/shared/ucsc/ucsc_build_sites.txt.sample
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

JARS="/galaxy/software/jars"

if [ ! $1 ]; then
	type="standard"
elif [ $1 == "-ec2" ]; then
	type="external-ec2"
else
	type="unknown"
fi

case $type in
	external*)
		echo "Running standalone buildbot setup..."
		for sample in tool-data/*.sample; do
			basename=${sample%.sample}
			if [ ! -f $basename ]; then
				echo "Copying $sample to $basename"
				cp "$sample" "$basename"
			fi
		done
		;;
	*)
		echo "Running standard buildbot setup..."
		for link in $LINKS; do
		    echo "Linking $link"
		    rm -f tool-data/`basename $link`
		    ln -sf $link tool-data
		done
		
		if [ -d "$JARS" ]; then
		    echo "Linking $JARS"
		    rm -f tool-data/shared/jars
		    ln -sf $JARS tool-data/shared/jars
		fi
		;;
esac

for sample in $SAMPLES; do
    file=${sample%.sample}
    echo "Copying $sample to $file"
    cp $sample $file
done

echo "Copying job_conf.xml.sample_basic to job_conf.xml"
cp config/job_conf.xml.sample_basic config/job_conf.xml

for dir in $DIRS; do
    if [ ! -d $dir ]; then
        echo "Creating $dir"
        mkdir $dir
    fi
done

# for wig_to_bigWig and bed_to_bigBed
for build in hg17 hg18; do
    if [ -f "test-data/chrom/$build.len" ]; then
        echo "Copying test-data/chrom/$build.len to tool-data/shared/ucsc/chrom/"
        mkdir -p tool-data/shared/ucsc/chrom
        cp test-data/chrom/$build.len tool-data/shared/ucsc/chrom/$build.len
    fi
done

if [ -d "test-data-repo" ]; then
    echo "Updating test data repository"
    cd test-data-repo
    hg pull
    hg update
    cd ..
else
    echo "Cloning test data repository"
    hg clone http://bitbucket.org/natefoo/galaxy-test-data/ test-data-repo
fi
echo "Setting up test data location files"
python test-data-repo/location/make_location.py

echo "Appending tool-data/shared/ucsc/builds.txt.buildbot to tool-data/shared/ucsc/builds.txt"
cat tool-data/shared/ucsc/builds.txt.buildbot >> tool-data/shared/ucsc/builds.txt

python ./scripts/fetch_eggs.py all
