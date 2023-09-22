#!/usr/bin/env python
from __future__ import print_function

import sys

from galaxy.datatypes.util.gff_util import parse_gff_attributes


def get_bed_line(chrom, name, strand, blocks):
    """Returns a BED line for given data."""

    if len(blocks) == 1:
        # Use simple BED format if there is only a single block:
        #   chrom, chromStart, chromEnd, name, score, strand
        #
        start, end = blocks[0]
        return "%s\t%i\t%i\t%s\t0\t%s\n" % (chrom, start, end, name, strand)

    #
    # Build lists for transcript blocks' starts, sizes.
    #

    # Get transcript start, end.
    t_start = sys.maxsize
    t_end = -1
    for block_start, block_end in blocks:
        if block_start < t_start:
            t_start = block_start
        if block_end > t_end:
            t_end = block_end

    # Get block starts, sizes.
    block_starts = []
    block_sizes = []
    for block_start, block_end in blocks:
        block_starts.append(str(block_start - t_start))
        block_sizes.append(str(block_end - block_start))

    #
    # Create BED entry.
    # Bed format: chrom, chromStart, chromEnd, name, score, strand, \
    #               thickStart, thickEnd, itemRgb, blockCount, blockSizes, blockStarts
    #
    # Render complete feature with thick blocks. There's no clear way to do this unless
    # we analyze the block names, but making everything thick makes more sense than
    # making everything thin.
    #
    return "%s\t%i\t%i\t%s\t0\t%s\t%i\t%i\t0\t%i\t%s\t%s\n" % (
        chrom,
        t_start,
        t_end,
        name,
        strand,
        t_start,
        t_end,
        len(block_starts),
        ",".join(block_sizes),
        ",".join(block_starts),
    )


def __main__():
    input_name = sys.argv[1]
    output_name = sys.argv[2]
    skipped_lines = 0
    first_skipped_line = 0
    i = 0
    cur_transcript_chrome = None
    cur_transcript_id = None
    cur_transcript_strand = None
    cur_transcripts_blocks = []  # (start, end) for each block.
    with open(output_name, "w") as out, open(input_name) as in_fh:
        for i, line in enumerate(in_fh):
            line = line.rstrip("\r\n")
            if line and not line.startswith("#"):
                try:
                    # GFF format: chrom source, name, chromStart, chromEnd, score, strand, attributes
                    elems = line.split("\t")
                    start = str(int(elems[3]) - 1)
                    coords = [int(start), int(elems[4])]
                    strand = elems[6]
                    if strand not in ["+", "-"]:
                        strand = "+"
                    attributes = parse_gff_attributes(elems[8])
                    t_id = attributes.get("transcript_id", None)

                    if not t_id:
                        #
                        # No transcript ID, so write last transcript and write current line as its own line.
                        #

                        # Write previous transcript.
                        if cur_transcript_id:
                            # Write BED entry.
                            out.write(
                                get_bed_line(
                                    cur_transcript_chrome,
                                    cur_transcript_id,
                                    cur_transcript_strand,
                                    cur_transcripts_blocks,
                                )
                            )

                        # Replace any spaces in the name with underscores so UCSC will not complain.
                        name = elems[2].replace(" ", "_")
                        out.write(get_bed_line(elems[0], name, strand, [coords]))
                        continue

                    # There is a transcript ID, so process line at transcript level.
                    if t_id == cur_transcript_id:
                        # Line is element of transcript and will be a block in the BED entry.
                        cur_transcripts_blocks.append(coords)
                        continue

                    #
                    # Line is part of new transcript; write previous transcript and start
                    # new transcript.
                    #

                    # Write previous transcript.
                    if cur_transcript_id:
                        # Write BED entry.
                        out.write(
                            get_bed_line(
                                cur_transcript_chrome, cur_transcript_id, cur_transcript_strand, cur_transcripts_blocks
                            )
                        )

                    # Start new transcript.
                    cur_transcript_chrome = elems[0]
                    cur_transcript_id = t_id
                    cur_transcript_strand = strand
                    cur_transcripts_blocks = []
                    cur_transcripts_blocks.append(coords)
                except Exception:
                    skipped_lines += 1
                    if not first_skipped_line:
                        first_skipped_line = i + 1
            else:
                skipped_lines += 1
                if not first_skipped_line:
                    first_skipped_line = i + 1

        # Write last transcript.
        if cur_transcript_id:
            # Write BED entry.
            out.write(
                get_bed_line(cur_transcript_chrome, cur_transcript_id, cur_transcript_strand, cur_transcripts_blocks)
            )
    info_msg = "%i lines converted to BED.  " % (i + 1 - skipped_lines)
    if skipped_lines > 0:
        info_msg += "Skipped %d blank/comment/invalid lines starting with line #%d." % (
            skipped_lines,
            first_skipped_line,
        )
    print(info_msg)


if __name__ == "__main__":
    __main__()
