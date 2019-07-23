#
# Filters a GFF file using a list of attribute values. Attribute values must
# be in the first column of the file; subsequent columns are ignored.
# Usage:
# python gff_filter_by_attribute_values.py <gff_file> <attribute_name> <ids_file> <output_file>
#
from __future__ import print_function

import re
import sys


def gff_filter(gff_file, attribute_name, ids_file, output_file):
    # Put ids in dict for quick lookup.
    ids_dict = {}
    with open(ids_file) as ids:
        for line in ids:
            ids_dict[line.split('\t')[0].strip()] = True

    # Filter GFF file using ids.
    with open(output_file, 'w') as output:
        with open(gff_file) as gff:
            for line in gff:
                # Keep commented lines
                if line.startswith('#'):
                    output.write(line)
                else:
                    # Create pattern using attribute to filter 
                    prog = re.compile(r".*" + re.escape(attribute_name) + r" \"(.+?)\"\;")
                    line_match = prog.match(line)
                    # If there is a match and the id after the filtered attribute (attribut "id";) is in the list, we print it
                    if line_match and line_match.group(1) in ids_dict:
                        output.write(line)


if __name__ == "__main__":
    # Handle args.
    if len(sys.argv) != 5:
        print("usage: python %s <gff_file> <attribute_name> <ids_file> <output_file>" % sys.argv[0], file=sys.stderr)
        sys.exit(-1)
    gff_file, attribute_name, ids_file, output_file = sys.argv[1:]
    gff_filter(gff_file, attribute_name, ids_file, output_file)
