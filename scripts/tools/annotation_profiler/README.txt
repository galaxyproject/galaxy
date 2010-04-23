This file explains how to create annotation indexes for the annotation profiler tool. Annotation profiler indexes are an exceedingly simple binary format, 
containing no header information and consisting of an ordered linear list of (start,stop encoded individually as '<I') regions which are covered by a UCSC table partitioned 
by chromosome name. Genomic regions are merged by overlap / direct adjacency (e.g. a table having ranges of: 1-10, 6-12, 12-20 and 25-28 results in two merged ranges of: 1-20 and 25-28).

Files are arranged like:
/profiled_annotations/DBKEY/TABLE_NAME/
                                       CHROMOSOME_NAME.covered
                                       CHROMOSOME_NAME.total_coverage
                                       CHROMOSOME_NAME.total_regions
/profiled_annotations/DBKEY/
                            DBKEY_tables.xml
                            chromosomes.txt
                            profiled_info.txt


where CHROMOSOME_NAME.covered is the binary file, CHROMOSOME_NAME.total_coverage is a text file containing the integer count of bases covered by the 
table and CHROMOSOME_NAME.total_regions contains the integer count of the number of regions found in CHROMOSOME_NAME.covered

DBKEY_tables.xml should be appended to the annotation profile available table configuration file (tool-data/annotation_profiler_options.xml).
The DBKEY should also be added as a new line to the annotation profiler valid builds file (annotation_profiler_valid_builds.txt).
The output (/profiled_annotations/DBKEY) should be made available as GALAXY_ROOT/tool-data/annotation_profiler/DBKEY.

profiled_info.txt contains info on the generated annotations, separated by lines with tab-delimited label,value pairs:
        profiler_version - the version of the build_profile_indexes.py script that was used to generate the profiled data
        dbkey - the dbkey used for the run
        chromosomes - contains the names and lengths of chromosomes that were used to parse single-chromosome tables (tables divided into individual files by chromosome)
        dump_time - the declared dump time of the database, taken from trackDb.txt.gz
        profiled_time - seconds since epoch in utc for when the database dump was profiled
        database_hash - a md5 hex digest of all the profiled table info 


Typical usage includes:

python build_profile_indexes.py -d hg19 -i /ucsc_data/hg19/database/ > hg19.txt

where the genome build is hg19 and /ucsc_data/hg19/database/ contains the downloaded database dump from UCSC (e.g. obtained by rsync: rsync -avzP rsync://hgdownload.cse.ucsc.edu/goldenPath/hg19/database/ /ucsc_data/hg19/database/).



By default, chromosome names come from a file named 'chromInfo.txt.gz' found in the input directory, with FTP used as a backup.
When FTP is used to obtain the names of chromosomes from UCSC for a particular genome build, alternate ftp sites and paths can be specified by using the --ftp_site and --ftp_path attributes. 
Chromosome names can instead be provided on the commandline via the --chromosomes option, which accepts a comma separated list of:ChromName1[=length],ChromName2[=length],...



    usage = "usage: %prog options"
    parser = OptionParser( usage=usage )
    parser.add_option( '-d', '--dbkey', dest='dbkey', default='hg18', help='dbkey to process' )
    parser.add_option( '-i', '--input_dir', dest='input_dir', default=os.path.join( 'golden_path','%s', 'database' ), help='Input Directory' )
    parser.add_option( '-o', '--output_dir', dest='output_dir', default=os.path.join( 'profiled_annotations','%s' ), help='Output Directory' )
    parser.add_option( '-c', '--chromosomes', dest='chromosomes', default='', help='Comma separated list of: ChromName1[=length],ChromName2[=length],...' )
    parser.add_option( '-b', '--bitset_size', dest='bitset_size', default=DEFAULT_BITSET_SIZE, type='int', help='Default BitSet size; overridden by sizes specified in chromInfo.txt.gz or by --chromosomes' )
    parser.add_option( '-f', '--ftp_site', dest='ftp_site', default='hgdownload.cse.ucsc.edu', help='FTP site; used for chromosome info when chromInfo.txt.gz method fails' )
    parser.add_option( '-p', '--ftp_path', dest='ftp_path', default='/goldenPath/%s/chromosomes/', help='FTP Path; used for chromosome info when chromInfo.txt.gz method fails' )
