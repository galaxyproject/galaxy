#!/usr/bin/env python

import argparse


def get_bed12_line(chrom, name, strand, blocks):
    """Returns a BED12 line for given data."""

    # Build lists for transcript blocks' starts, sizes.
    block_starts, block_ends = zip(*blocks)
    # Get transcript start, end.
    t_start = min(block_starts)
    t_end = max(block_ends)
    # Calculate block sizes (as str).
    block_sizes = [str(block_end - block_start) for block_start, block_end in blocks]
    # Adjust block starts, convert to str
    block_starts = [str(block_start - t_start) for block_start in block_starts]

    # BED12 format: chrom, chromStart, chromEnd, name, score, strand,
    # thickStart, thickEnd, itemRgb, blockCount, blockSizes, blockStarts
    #
    # Render complete feature with thick blocks. There's no clear way to do this unless
    # we analyze the block names, but making everything thick makes more sense than
    # making everything thin.
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--bedcols", type=int, choices=[6, 12], help="Type of BED to produce, either bed6 or bed12")
    parser.add_argument("input", type=str)
    parser.add_argument("output", type=str)
    args = parser.parse_args()
    input_name = args.input
    output_name = args.output
    bedcols = args.bedcols

    skipped_lines = 0
    first_skipped_line = 0
    i = 0
    if bedcols == 12:
        from galaxy.datatypes.util.gff_util import parse_gff_attributes

        cur_transcript_chrome = None
        cur_transcript_id = None
        cur_transcript_strand = None
        cur_transcripts_blocks = []  # (start, end) for each block
    with open(input_name) as fh, open(output_name, "w") as out:
        for i, line in enumerate(fh):
            line = line.rstrip("\r\n")
            if line and not line.startswith("#"):
                try:
                    # GFF format: chrom, source, feature, chromStart, chromEnd, score, strand, frame, attributes
                    elems = line.split("\t")
                    start = str(int(elems[3]) - 1)
                    strand = elems[6]
                    if strand not in ["+", "-"]:
                        strand = "+"
                    # Replace any spaces in the name with underscores so UCSC will not complain.
                    name = elems[2].replace(" ", "_")

                    if bedcols == 6:
                        # BED6 format: chrom, chromStart, chromEnd, name, score, strand
                        out.write(f"{elems[0]}\t{start}\t{elems[4]}\t{name}\t0\t{strand}\n")
                        continue

                    coords = (int(start), int(elems[4]))
                    attributes = parse_gff_attributes(elems[8])
                    t_id = attributes.get("transcript_id")
                    if not t_id:
                        #
                        # No transcript ID, so write last transcript and write current line as its own line.
                        #

                        # Write previous transcript.
                        if cur_transcript_id:
                            # Write BED entry.
                            out.write(
                                get_bed12_line(
                                    cur_transcript_chrome,
                                    cur_transcript_id,
                                    cur_transcript_strand,
                                    cur_transcripts_blocks,
                                )
                            )

                        out.write(get_bed12_line(elems[0], name, strand, [coords]))
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
                            get_bed12_line(
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
        if bedcols == 12 and cur_transcript_id:
            # Write BED entry.
            out.write(
                get_bed12_line(cur_transcript_chrome, cur_transcript_id, cur_transcript_strand, cur_transcripts_blocks)
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
