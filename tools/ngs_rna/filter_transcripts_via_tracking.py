#!/usr/bin/env python
import os, sys, tempfile

assert sys.version_info[:2] >= ( 2, 4 )

def __main__():
    """
    Utility script for analyzing Cufflinks data: uses a tracking file (produced by cuffcompare) to filter a GTF file of transcripts (usually the transcripts
    produced by cufflinks). Filtering is done by extracting transcript IDs from tracking file and then filtering the GTF so that the output GTF contains only
    transcript found in the tracking file. Because a tracking file has multiple samples, a sample number is used to filter transcripts for
    a particular sample.
    """
    # Read parms.
    tracking_file_name = sys.argv[1]
    transcripts_file_name = sys.argv[2]
    output_file_name = sys.argv[3]
    sample_number = int ( sys.argv[4] )

    # Open files.
    transcripts_file = open( transcripts_file_name, 'r' )
    output_file = open( output_file_name, 'w' )
    
    # Read transcript IDs from tracking file.
    transcript_ids = {}
    for i, line in enumerate( file( tracking_file_name ) ) :
        # Split line into elements. Line format is 
        # [Transfrag ID] [Locus ID] [Ref Gene ID] [Ref Transcript ID] [Class code] [qJ:<gene_id>|<transcript_id>|<FMI>|<FPKM>|<conf_lo>|<conf_hi>]
        line = line.rstrip( '\r\n' )
        elems = line.split( '\t' )
        
        # Get transcript info.
        if sample_number == 1:
            transcript_info = elems[4]
        elif sample_number == 2:
            transcript_info = elems[5]
        if not transcript_info.startswith('q'):
            # No transcript for this sample.
            continue
        
        # Get and store transcript id.
        transcript_id = transcript_info.split('|')[1]
        transcript_id = transcript_id.strip('"')
        transcript_ids[transcript_id] = ""
        
    # Filter transcripts file using transcript_ids
    for i, line in enumerate( file( transcripts_file_name ) ):
        # GTF format: chrom source, name, chromStart, chromEnd, score, strand, frame, attributes.
        elems = line.split( '\t' )
        
        # Get attributes.
        attributes_list = elems[8].split(";")
        attributes = {}
        for name_value_pair in attributes_list:
            pair = name_value_pair.strip().split(" ")
            name = pair[0].strip()
            if name == '':
                continue
            # Need to strip double quote from values
            value = pair[1].strip(" \"")
            attributes[name] = value
            
        # Get element's transcript id.
        transcript_id = attributes['transcript_id']
        if transcript_id in transcript_ids:
            output_file.write(line)
        
    # Clean up.
    output_file.close()
    
if __name__ == "__main__": __main__()
