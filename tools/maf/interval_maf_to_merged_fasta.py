#!/usr/bin/env python
"""
Reads an interval or gene BED and a MAF Source.
Produces a FASTA file containing the aligned intervals/gene sequences, based upon the provided coordinates

Alignment blocks are layered ontop of each other based upon score.

usage: %prog maf_file [options]
   -d, --dbkey=d: Database key, ie hg17
   -c, --chromCol=c: Column of Chr
   -s, --startCol=s: Column of Start
   -e, --endCol=e: Column of End
   -S, --strandCol=S: Column of Strand
   -G, --geneBED: Input is a Gene BED file, process and join exons as one region
   -t, --mafSourceType=t: Type of MAF source to use
   -m, --mafSource=m: Path of source MAF file, if not using cached version
   -I, --mafIndex=I: Path of precomputed source MAF file index, if not using cached version
   -i, --interval_file=i:       Input interval file
   -o, --output_file=o:      Output MAF file
   -p, --species=p: Species to include in output
   -O, --overwrite_with_gaps=O: Overwrite bases found in a lower-scoring block with gaps interior to the sequence for a species.
   -z, --mafIndexFileDir=z: Directory of local maf_index.loc file

usage: %prog dbkey_of_BED comma_separated_list_of_additional_dbkeys_to_extract comma_separated_list_of_indexed_maf_files input_gene_bed_file output_fasta_file cached|user GALAXY_DATA_INDEX_DIR
"""
# Dan Blankenberg
from __future__ import print_function

import sys

import bx.intervals.io
from bx.cookbook import doc_optparse

from galaxy.tools.util import maf_utilities


def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()


def __main__():
    # Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    mincols = 0
    strand_col = -1

    if options.dbkey:
        primary_species = options.dbkey
    else:
        primary_species = None
    if primary_species in [None, "?", "None"]:
        stop_err( "You must specify a proper build in order to extract alignments. You can specify your genome build by clicking on the pencil icon associated with your interval file." )

    include_primary = True
    secondary_species = maf_utilities.parse_species_option( options.species )
    if secondary_species:
        species = list( secondary_species )  # make copy of species list
        if primary_species in secondary_species:
            secondary_species.remove( primary_species )
        else:
            include_primary = False
    else:
        species = None

    if options.interval_file:
        interval_file = options.interval_file
    else:
        stop_err( "Input interval file has not been specified." )

    if options.output_file:
        output_file = options.output_file
    else:
        stop_err( "Output file has not been specified." )

    if not options.geneBED:
        if options.chromCol:
            chr_col = int( options.chromCol ) - 1
        else:
            stop_err( "Chromosome column not set, click the pencil icon in the history item to set the metadata attributes." )

        if options.startCol:
            start_col = int( options.startCol ) - 1
        else:
            stop_err( "Start column not set, click the pencil icon in the history item to set the metadata attributes." )

        if options.endCol:
            end_col = int( options.endCol ) - 1
        else:
            stop_err( "End column not set, click the pencil icon in the history item to set the metadata attributes." )

        if options.strandCol:
            strand_col = int( options.strandCol ) - 1

    mafIndexFile = "%s/maf_index.loc" % options.mafIndexFileDir

    overwrite_with_gaps = True
    if options.overwrite_with_gaps and options.overwrite_with_gaps.lower() == 'false':
        overwrite_with_gaps = False

    # Finish parsing command line

    # get index for mafs based on type
    index = index_filename = None
    # using specified uid for locally cached
    if options.mafSourceType.lower() in ["cached"]:
        index = maf_utilities.maf_index_by_uid( options.mafSource, mafIndexFile )
        if index is None:
            stop_err( "The MAF source specified (%s) appears to be invalid." % ( options.mafSource ) )
    elif options.mafSourceType.lower() in ["user"]:
        # index maf for use here, need to remove index_file when finished
        index, index_filename = maf_utilities.open_or_build_maf_index( options.mafSource, options.mafIndex, species=[primary_species] )
        if index is None:
            stop_err( "Your MAF file appears to be malformed." )
    else:
        stop_err( "Invalid MAF source type specified." )

    # open output file
    output = open( output_file, "w" )

    if options.geneBED:
        region_enumerator = maf_utilities.line_enumerator( open( interval_file, "r" ).readlines() )
    else:
        region_enumerator = enumerate(bx.intervals.io.NiceReaderWrapper(
            open( interval_file, 'r' ), chrom_col=chr_col, start_col=start_col,
            end_col=end_col, strand_col=strand_col, fix_strand=True,
            return_header=False, return_comments=False ) )

    # Step through intervals
    regions_extracted = 0
    line_count = 0
    for line_count, line in region_enumerator:
        try:
            if options.geneBED:  # Process as Gene BED
                try:
                    starts, ends, fields = maf_utilities.get_starts_ends_fields_from_gene_bed( line )
                    # create spliced alignment object
                    alignment = maf_utilities.get_spliced_region_alignment(
                        index, primary_species, fields[0], starts, ends,
                        strand='+', species=species, mincols=mincols,
                        overwrite_with_gaps=overwrite_with_gaps )
                    primary_name = secondary_name = fields[3]
                    alignment_strand = fields[5]
                except Exception as e:
                    print("Error loading exon positions from input line %i: %s" % ( line_count, e ))
                    continue
            else:  # Process as standard intervals
                try:
                    # create spliced alignment object
                    alignment = maf_utilities.get_region_alignment(
                        index, primary_species, line.chrom, line.start,
                        line.end, strand='+', species=species, mincols=mincols,
                        overwrite_with_gaps=overwrite_with_gaps )
                    primary_name = "%s(%s):%s-%s" % ( line.chrom, line.strand, line.start, line.end )
                    secondary_name = ""
                    alignment_strand = line.strand
                except Exception as e:
                    print("Error loading region positions from input line %i: %s" % ( line_count, e ))
                    continue

            # Write alignment to output file
            # Output primary species first, if requested
            if include_primary:
                output.write( ">%s.%s\n" % ( primary_species, primary_name ) )
                if alignment_strand == "-":
                    output.write( alignment.get_sequence_reverse_complement( primary_species ) )
                else:
                    output.write( alignment.get_sequence( primary_species ) )
                output.write( "\n" )
            # Output all remainging species
            for spec in secondary_species or alignment.get_species_names( skip=primary_species ):
                if secondary_name:
                    output.write( ">%s.%s\n" % ( spec, secondary_name ) )
                else:
                    output.write( ">%s\n" % ( spec ) )
                if alignment_strand == "-":
                    output.write( alignment.get_sequence_reverse_complement( spec ) )
                else:
                    output.write( alignment.get_sequence( spec ) )
                output.write( "\n" )

            output.write( "\n" )
            regions_extracted += 1
        except Exception as e:
            print("Unexpected error from input line %i: %s" % ( line_count, e ))
            continue

    # close output file
    output.close()

    # remove index file if created during run
    maf_utilities.remove_temp_index_file( index_filename )

    # Print message about success for user
    if regions_extracted > 0:
        print("%i regions were processed successfully." % ( regions_extracted ))
    else:
        print("No regions were processed successfully.")
        if line_count > 0 and options.geneBED:
            print("This tool requires your input file to conform to the 12 column BED standard.")


if __name__ == "__main__":
    __main__()
