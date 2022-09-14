#!/usr/bin/env python
# Dan Blankenberg

import sys

assert sys.version_info[:2] >= (2, 6)
HEADER_STARTS_WITH = "@"


def __main__():
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    skipped_lines = 0
    first_skipped_line = 0
    header_lines = 0
    i = 0
    with open(input_name) as fh, open(output_name, "w") as out:
        for i, line in enumerate(fh):
            line = line.rstrip("\r\n")
            if line:
                if line.startswith(HEADER_STARTS_WITH):
                    header_lines += 1
                else:
                    try:
                        elems = line.split("\t")
                        out.write(f"{elems[0]}\t{int(elems[1]) - 1}\t{elems[2]}\t{elems[4]}\t0\t{elems[3]}\n")
                    except Exception as e:
                        print(e)
                        skipped_lines += 1
                        if not first_skipped_line:
                            first_skipped_line = i + 1
            else:
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = i + 1
    info_msg = "%i lines converted to BED.  " % (i + 1 - skipped_lines)
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." % (
            skipped_lines,
            first_skipped_line,
        )
    print(info_msg)


if __name__ == "__main__":
    __main__()
