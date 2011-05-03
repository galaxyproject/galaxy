#
# Filters a GFF file using a list of attribute values. Attribute values must 
# be in the first column of the file; subsequent columns are ignored.
# Usage:
# python gff_filter_by_attribute_values.py <gff_file> <attribute_name> <ids_file> <output_file>
#

import sys

def parse_gff_attributes( attr_str ):
    """
    Parses a GFF/GTF attribute string and returns a dictionary of name-value 
    pairs. The general format for a GFF3 attributes string is 
        name1=value1;name2=value2
    The general format for a GTF attribute string is 
        name1 "value1" ; name2 "value2"
    The general format for a GFF attribute string is a single string that
    denotes the interval's group; in this case, method returns a dictionary 
    with a single key-value pair, and key name is 'group'
    """    
    attributes_list = attr_str.split(";")
    attributes = {}
    for name_value_pair in attributes_list:
        # Try splitting by space and, if necessary, by '=' sign.
        pair = name_value_pair.strip().split(" ")
        if len( pair ) == 1:
            pair = name_value_pair.strip().split("=")
        if len( pair ) == 1:
            # Could not split for some reason -- raise exception?
            continue
        if pair == '':
            continue
        name = pair[0].strip()
        if name == '':
            continue
        # Need to strip double quote from values
        value = pair[1].strip(" \"")
        attributes[ name ] = value
        
    if len( attributes ) == 0:
        # Could not split attributes string, so entire string must be 
        # 'group' attribute. This is the case for strictly GFF files.
        attributes['group'] = attr_str
    return attributes

def filter( gff_file, attribute_name, ids_file, output_file ):
    # Put ids in dict for quick lookup.
    ids_dict = {}
    for line in open( ids_file ):
        ids_dict[ line.split('\t')[0].strip() ] = True

    # Filter GFF file using ids.
    output = open( output_file, 'w' )
    for line in open( gff_file ):
        fields = line.split( '\t' )
        attributes = parse_gff_attributes( fields[8] )
        if ( attribute_name in attributes ) and ( attributes[ attribute_name ] in ids_dict ):
            output.write( line )
    output.close()
        
if __name__ == "__main__":
    # Handle args.
    if len( sys.argv ) != 5:
        print >> sys.stderr, "usage: python %s <gff_file> <attribute_name> <ids_file> <output_file>"  % sys.argv[0]
        sys.exit( -1 )
    gff_file, attribute_name, ids_file, output_file = sys.argv[1:]
    filter( gff_file, attribute_name, ids_file, output_file )
