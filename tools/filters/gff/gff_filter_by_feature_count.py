#!/usr/bin/env python
"""
Filter a gff file using a criterion based on feature counts for a transcript.

Usage:
%prog input_name output_name feature_name condition
"""
import sys
from galaxy import eggs
from galaxy.datatypes.util.gff_util import GFFReaderWrapper
from bx.intervals.io import GenomicInterval

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
    kept_features = 0
    skipped_lines = 0
    first_skipped_line = 0
    out = open( output_name, 'w' )
    for i, feature in enumerate( GFFReaderWrapper( open( input_name ) ) ):
        if not isinstance( feature, GenomicInterval ):
            continue
        count = 0
        for interval in feature.intervals:
            if interval.feature == feature_name:
                count += 1
        if eval( '%s %s' % ( count, condition ) ):
            # Keep feature.
            for interval in feature.intervals:
                out.write( "\t".join(interval.fields) + '\n' )
            kept_features += 1

    # Needed because i is 0-based but want to display stats using 1-based.
    i += 1

    # Clean up.
    out.close()
    info_msg = "%i of %i features kept (%.2f%%) using condition %s.  " % \
        ( kept_features, i, float(kept_features)/i * 100.0, feature_name + condition )
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." %( skipped_lines, first_skipped_line )
    print info_msg

if __name__ == "__main__": __main__()
