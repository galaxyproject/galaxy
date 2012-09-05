'''
Creates a feature location index (FLI) for a given BED/GFF file.
FLI index has the form:
    [line_length]
    <symbol1_in_lowercase><tab><symbol1><tab><location>
    <symbol2_in_lowercase><tab><symbol2><tab><location>
    ...
where location is formatted as:
    contig:start-end
and symbols are sorted in lexigraphical order.
'''

import sys, optparse
from galaxy import eggs
from galaxy.datatypes.util.gff_util import read_unordered_gtf, convert_gff_coords_to_bed

def main():
    # Process arguments.
    parser = optparse.OptionParser()
    parser.add_option( '-B', '--bed', action="store_true", dest="bed_input" )
    parser.add_option( '-G', '--gff', action="store_true", dest="gff_input" )
    (options, args) = parser.parse_args()
    in_fname, out_fname = args


    # Create dict of name-location pairings.
    name_loc_dict = {}
    if options.gff_input:
        # GFF format
        for feature in read_unordered_gtf( open( in_fname, 'r' ) ):
            for name in feature.attributes:
                val = feature.attributes[ name ]
                try:
                    float( val )
                    continue
                except:
                    convert_gff_coords_to_bed( feature )
                    # Value is not a number, so it can be indexed.
                    if val not in name_loc_dict:
                        # Value is not in dictionary.
                        name_loc_dict[ val ] = {
                            'contig': feature.chrom,
                            'start': feature.start,
                            'end': feature.end
                        }
                    else:
                        # Value already in dictionary, so update dictionary.
                        loc = name_loc_dict[ val ]
                        if feature.start < loc[ 'start' ]:
                            loc[ 'start' ] = feature.start
                        if feature.end > loc[ 'end' ]:
                            loc[ 'end' ] = feature.end
    else:
        # BED format.
        for line in open( in_fname, 'r' ):
            fields = line.split()
            name_loc_dict[ fields[3] ] = {
                'contig': fields[0],
                'start': int( fields[1] ),
                'end': int ( fields[2] )
            }
        
    # Create sorted list of entries.
    out = open( out_fname, 'w' )
    max_len = 0
    entries = []
    for name in sorted( name_loc_dict.iterkeys() ):
        loc = name_loc_dict[ name ]
        entry = '%s\t%s\t%s' % ( name.lower(), name, '%s:%i-%i' % ( loc[ 'contig' ], loc[ 'start' ], loc[ 'end' ] ) )
        if len( entry ) > max_len:
            max_len = len( entry )
        entries.append( entry )
    
    # Write padded entries.
    out.write( str( max_len + 1 ).ljust( max_len ) + '\n' )
    for entry in entries:
        out.write( entry.ljust( max_len ) + '\n' )
    out.close()

if __name__ == '__main__':
    main()