The Scripts found in this directory are used to download and generate the files relating to Galaxy as a Microbial Resource.
This includes scripts to access the NCBI Genome Projects site, download relevent data, and convert to a form usable in Galaxy. Data is generated for the Microbial Datasource Tool, as well as for Galaxy Interval Operations (chromosome names and lengths), and also the extract Genomic DNA tool.  Information about organisms is also written into '.info' files found in each organism directory.

Step 3 requires a binary 'faToNib' to properly generate sequence files.

Steps should be performed in the order they appear here.

(1.) To Download and process Genome Projects from NCBI into a form usable by Galaxy:
	python /GALAXY_ROOT/scripts/microbes/harvest_bacteria.py /OUTPUT/DIRECTORY/microbes/ > /OUTPUT/DIRECTORY/harvest.txt

(2.) To Walk downloaded Genome Projects and Convert, in place, IDs to match the UCSC Archaea browser, where applicable:
	python /GALAXY_ROOT/scripts/microbes/ncbi_to_ucsc.py /OUTPUT/DIRECTORY/microbes/ > /OUTPUT/DIRECTORY/ncbi_to_ucsc.txt

(3.) To create nib files (for extraction) and to generate the location file content for Microbes used for extracting Genomic DNA:
	python /GALAXY_ROOT/scripts/microbes/create_nib_seq_loc_file.py /OUTPUT/DIRECTORY/microbes/ seq.loc > /OUTPUT/DIRECTORY/sequence.txt

(4.) To create the location file for the Microbial Data Resource tool in Galaxy:
	python /GALAXY_ROOT/scripts/microbes/create_bacteria_loc_file.py /OUTPUT/DIRECTORY/microbes/ > /OUTPUT/DIRECTORY/microbial_data.loc

(5.) To Generate a single file containing the lengths for each chromosome for each species, to be added to 'manual_builds.txt':
	python /GALAXY_ROOT/scripts/microbes/get_builds_lengths.py /OUTPUT/DIRECTORY/microbes/ > /OUTPUT/DIRECTORY/microbes.len

(6.) To Create the Wiki Table listing available Microbial Data in Galaxy:
	python /GALAXY_ROOT/scripts/microbes/create_bacteria_table.py /OUTPUT/DIRECTORY/microbes/ > /OUTPUT/DIRECTORY/microbes.table