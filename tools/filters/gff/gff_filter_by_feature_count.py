#!/usr/bin/env python
"""
Filter a gff file using a criterion based on feature counts for a transcript.

Usage:
%prog input_name output_name feature_name condition
"""
import sys
from galaxy import eggs
from galaxy.datatypes.util.gff_util import parse_gff_attributes

assert sys.version_info[:2] >= ( 2, 4 )

# Valid operators, ordered so that complex operators (e.g. '>=') are
# recognized before simple operators (e.g. '>')
ops = [
    '>=',
    '<=',
    '<',
    '>',
    '==',
    '!='
]

# Escape sequences for valid operators.
mapped_ops = {
    '__ge__': ops[0],
    '__le__': ops[1],
    '__lt__': ops[2],
    '__gt__': ops[3],
    '__eq__': ops[4],
    '__ne__': ops[5],
}


def __main__():
    # Get args.
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    feature_name = sys.argv[3]
    condition = sys.argv[4]
    
    # Unescape operations in condition str.
    for key, value in mapped_ops.items():
        condition = condition.replace( key, value )
    
    # Error checking: condition should be of the form <operator><number>
    for op in ops:
        if op in condition:
            empty, number_str = condition.split( op )
            try:
                number = float( number_str )
            except:
                number = None
            if empty != "" or not number:
                print >> sys.stderr, "Invalid condition: %s, cannot filter." % condition
                return
            break

    # Do filtering.
    kept_lines = 0
    skipped_lines = 0
    first_skipped_line = 0
    out = open( output_name, 'w' )
    i = 0
    cur_transcript_id = None
    cur_transcript_lines = []
    cur_transcript_feature_counts = {} # Key is feature name, value is feature count.
    for i, line in enumerate( file( input_name ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            try:
                # GFF format: chrom, source, feature, chromStart, chromEnd, score, strand, attributes
                elems = line.split( '\t' )
                feature = elems[2]
                start = str( long( elems[3] ) - 1 )
                coords = [ long( start ), long( elems[4] ) ]
                strand = elems[6]
                attributes = parse_gff_attributes( elems[8] )
                t_id = attributes.get( "transcript_id", None )
                    
                if not t_id:
                    # No transcript id, so pass line to output.
                    out.write( line )
                    kept_lines += 1
                    continue
                
                # There is a transcript ID, so process line at transcript level.
                if t_id == cur_transcript_id:
                    # Line is element of transcript; increment feature count.
                    if not feature in cur_transcript_feature_counts:
                        cur_transcript_feature_counts[feature] = 0
                    cur_transcript_feature_counts[feature] += 1
                    cur_transcript_lines.append( line )
                    continue
                    
                #
                # Line is part of new transcript; filter previous transcript.
                #
                
                # Filter/write previous transcript.
                result = eval( '%s %s' % ( cur_transcript_feature_counts.get( feature_name, 0 ), condition ) )
                if cur_transcript_id and result:
                    # Transcript passes filter; write transcript line to file."
                    out.write( "\n".join( cur_transcript_lines ) + "\n" )
                    kept_lines += len( cur_transcript_lines )

                # Start new transcript.
                cur_transcript_id = t_id
                cur_transcript_feature_counts = {}
                cur_transcript_feature_counts[feature] = 1
                cur_transcript_lines = [ line ]
            except Exception, e:
                print e
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = i + 1
        else:
            skipped_lines += 1
            if not first_skipped_line:
                first_skipped_line = i + 1
    
    # Write last transcript.
    if cur_transcript_id and eval( '%s %s' % ( cur_transcript_feature_counts[feature_name], condition ) ):
        # Transcript passes filter; write transcript lints to file.
        out.write( "\n".join( cur_transcript_lines ) + "\n" )
        kept_lines += len( cur_transcript_lines )

    # Clean up.
    out.close()
    info_msg = "%i lines kept (%.2f%%) using condition %s.  " % ( kept_lines, float(kept_lines)/i * 100.0, feature_name + condition )
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." %( skipped_lines, first_skipped_line )
    print info_msg

if __name__ == "__main__": __main__()
