#!/usr/bin/env python
# By, Guruprasad Ananda.
from __future__ import print_function

import optparse
import re


def __main__():
    parser = optparse.OptionParser()
    parser.add_option('--strip', action='store_true',
                      help='strip leading and trailing whitespaces')
    parser.add_option('--condense', action='store_true',
                      help='condense consecutive delimiters')
    (options, args) = parser.parse_args()
    if len(args) != 3:
        parser.error("usage: convert_characters.py infile from_char outfile")

    char_dict = {
        'T': '\t',
        's': '\s',
        'Dt': '\.',
        'C': ',',
        'D': '-',
        'U': '_',
        'P': '\|',
        'Co': ':',
        'Sc': ';'
    }
    # regexp to match 1 or more occurences.
    from_char = args[1]
    from_ch = char_dict[from_char]
    if options.condense:
        from_ch += '+'

    skipped = 0
    with open(args[0], 'rU') as fin:
        with open(args[2], 'w') as fout:
            for line in fin:
                if options.strip:
                    line = line.strip()
                else:
                    line = line.rstrip('\n')
                try:
                    fout.write("%s\n" % (re.sub(from_ch, '\t', line)))
                except:
                    skipped += 1

    if skipped:
        print("Skipped %d lines as invalid." % skipped)


if __name__ == "__main__":
    __main__()
