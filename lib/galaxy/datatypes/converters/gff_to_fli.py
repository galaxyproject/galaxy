'''
Creates a feature location index for a given GFF file.
'''

import sys
from galaxy import eggs
from galaxy.datatypes.util.gff_util import read_unordered_gtf, convert_gff_coords_to_bed

# Process arguments.
in_fname = sys.argv[1]
out_fname = sys.argv[2]

# Create dict of name-location pairings.
name_loc_dict = {}
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

# Print name, loc in sorted order.
out = open( out_fname, 'w' )
max_len = 0
entries = []
for name in sorted( name_loc_dict.iterkeys() ):
	loc = name_loc_dict[ name ]
	entry = '%s\t%s' % ( name, '%s:%i-%i' % ( loc[ 'contig' ], loc[ 'start' ], loc[ 'end' ] ) )
	if len( entry ) > max_len:
		max_len = len( entry )
	entries.append( entry )
	
out.write( str( max_len + 1 ).ljust( max_len ) + '\n' )
for entry in entries:
	out.write( entry.ljust( max_len ) + '\n' )
out.close()