#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import tempfile

assert sys.version_info[:2] >= ( 2, 4 )


def __main__():
    # Read parms.
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    attribute_name = sys.argv[3]

    # Create temp files.
    tmp_name1 = tempfile.NamedTemporaryFile().name
    tmp_name2 = tempfile.NamedTemporaryFile().name

    # Do conversion.
    skipped_lines = 0
    first_skipped_line = 0
    out = open( tmp_name1, 'w' )

    # Write track data to temporary file.
    i = 0
    for i, line in enumerate( open( input_name ) ):
        line = line.rstrip( '\r\n' )

        if line and not line.startswith( '#' ):
            try:
                elems = line.split( '\t' )
                start = str( int( elems[3] ) - 1 )  # GTF coordinates are 1-based, BedGraph are 0-based.
                strand = elems[6]
                if strand not in ['+', '-']:
                    strand = '+'
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
                value = attributes[ attribute_name ]
                # GTF format: chrom source, name, chromStart, chromEnd, score, strand, frame, attributes.
                # BedGraph format: chrom, chromStart, chromEnd, value
                out.write( "%s\t%s\t%s\t%s\n" % ( elems[0], start, elems[4], value ) )
            except:
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = i + 1
        else:
            skipped_lines += 1
            if not first_skipped_line:
                first_skipped_line = i + 1
    out.close()

    # Sort tmp file by chromosome name and chromosome start to create ordered track data.
    cmd = "sort -k1,1 -k2,2n < %s > %s" % ( tmp_name1, tmp_name2 )
    try:
        os.system(cmd)
        os.remove(tmp_name1)
    except Exception as ex:
        sys.stderr.write( "%s\n" % ex )
        sys.exit(1)

    # Create bedgraph file by combining track definition with ordered track data.
    cmd = "echo 'track type=bedGraph' | cat - %s > %s " % ( tmp_name2, output_name )
    try:
        os.system(cmd)
        os.remove(tmp_name2)
    except Exception as ex:
        sys.stderr.write( "%s\n" % ex )
        sys.exit(1)

    info_msg = "%i lines converted to BEDGraph.  " % ( i + 1 - skipped_lines )
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." % ( skipped_lines, first_skipped_line )
    print(info_msg)


if __name__ == "__main__":
    __main__()
