#!/usr/bin/env python
"""
convert nt and wgs data (fasta format) to giNumber_seqLen
run formatdb in the command line: gunzip -c nt.gz |formatdb -i stdin -p F -n "nt.chunk" -v 2000
"""

import sys

if __name__ == "__main__":
    seq = []
    len_seq = 0
    invalid_lines = 0
    gi = None

    for line in sys.stdin:
        line = line.rstrip("\r\n")
        if line.startswith(">"):
            if len_seq > 0:
                if gi is None:
                    raise Exception("The first sequence does not have an header.")
                print(">%s_%d" % (gi, len_seq))
                print("\n".join(seq))
            title = line
            fields = title.split("|")
            if len(fields) >= 2 and fields[0] == ">gi":
                gi = fields[1]
            else:
                gi = "giunknown"
                invalid_lines += 1
            len_seq = 0
            seq = []
        else:
            seq.append(line)
            len_seq += len(line)
    if len_seq > 0:
        print(">%s_%d" % (gi, len_seq))
        print("\n".join(seq))

    print(
        "Unable to find gi number for %d sequences, the title is replaced as giunknown" % (invalid_lines),
        file=sys.stderr,
    )
