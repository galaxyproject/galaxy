"""
Creates a feature location index (FLI) for a given BED/GFF file.
FLI index has the form::

    [line_length]
    <symbol1_in_lowercase><tab><symbol1><tab><location>
    <symbol2_in_lowercase><tab><symbol2><tab><location>
    ...

where location is formatted as:

    contig:start-end

and symbols are sorted in lexigraphical order.
"""

import optparse

from bx.tabular.io import (
    Comment,
    Header,
)

from galaxy.datatypes.util.gff_util import (
    convert_gff_coords_to_bed,
    GFFReaderWrapper,
    read_unordered_gtf,
)


def main():
    # Process arguments.
    parser = optparse.OptionParser()
    parser.add_option("-F", "--format", dest="input_format")
    (options, args) = parser.parse_args()
    in_fname, out_fname = args
    input_format = options.input_format.lower()

    # Create dict of name-location pairings.
    name_loc_dict = {}
    if input_format in ["gff", "gtf"]:
        # GTF/GFF format

        # Create reader.
        if input_format == "gff":
            in_reader = GFFReaderWrapper(open(in_fname))
        else:  # input_format == 'gtf'
            in_reader = read_unordered_gtf(open(in_fname))

        for feature in in_reader:
            if isinstance(feature, (Header, Comment)):
                continue

            for name in feature.attributes:
                val = feature.attributes[name]
                try:
                    float(val)
                    continue
                except ValueError:
                    convert_gff_coords_to_bed(feature)
                    # Value is not a number, so it can be indexed.
                    if val not in name_loc_dict:
                        # Value is not in dictionary.
                        name_loc_dict[val] = {"contig": feature.chrom, "start": feature.start, "end": feature.end}
                    else:
                        # Value already in dictionary, so update dictionary.
                        loc = name_loc_dict[val]
                        if feature.start < loc["start"]:
                            loc["start"] = feature.start
                        if feature.end > loc["end"]:
                            loc["end"] = feature.end
    elif input_format == "bed":
        # BED format.
        for line in open(in_fname):
            # Ignore track lines.
            if line.startswith("track"):
                continue

            fields = line.split()

            # Ignore lines with no feature name.
            if len(fields) < 4:
                continue

            # Process line
            name_loc_dict[fields[3]] = {"contig": fields[0], "start": int(fields[1]), "end": int(fields[2])}

    # Create sorted list of entries.
    max_len = 0
    entries = []
    for name in sorted(name_loc_dict.keys()):
        loc = name_loc_dict[name]
        entry = "{}\t{}\t{}".format(name.lower(), name, "%s:%i-%i" % (loc["contig"], loc["start"], loc["end"]))
        if len(entry) > max_len:
            max_len = len(entry)
        entries.append(entry)

    # Write padded entries.
    with open(out_fname, "w") as out:
        out.write(f"{str(max_len + 1).ljust(max_len)}\n")
        for entry in entries:
            out.write(f"{entry.ljust(max_len)}\n")


if __name__ == "__main__":
    main()
