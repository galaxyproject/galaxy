"""
Extended version of Dan Blankenberg's fastq joiner (adds support for
recent Illumina headers).
"""

import sys, re
import galaxy_utils.sequence.fastq as fq


class IDManager(object):

    def __init__(self, sep="\t"):
        """
        Recent Illumina FASTQ header format::

          @<COORDS> <FLAGS>
          COORDS = <Instrument>:<Run #>:<Flowcell ID>:<Lane>:<Tile>:<X>:<Y>
          FLAGS = <Read>:<Is Filtered>:<Control Number>:<Index Sequence>

        where the whitespace character between <COORDS> and <FLAGS> can be
        either a space or a tab.
        """
        self.sep = sep

    def parse_id(self, identifier):
        try:
            coords, flags = identifier.strip()[1:].split(self.sep, 1)
        except ValueError:
            raise RuntimeError("bad identifier: %r" % (identifier,))
        return coords.split(":"), flags.split(":")

    def join_id(self, parsed_id):
        coords, flags = parsed_id
        return "@%s%s%s" % (":".join(coords), self.sep, ":".join(flags))

    def get_read_number(self, parsed_id):
        return int(parsed_id[1][0])

    def set_read_number(self, parsed_id, n):
        parsed_id[1][0] = "%d" % n

    def get_paired_identifier(self, read):
        t = self.parse_id(read.identifier)
        n = self.get_read_number(t)
        if n == 1:
            pn = 2
        elif n == 2:
            pn = 1
        else:
            raise RuntimeError("Unknown read number '%d'" % n)
        self.set_read_number(t, pn)
        return self.join_id(t)


class FastqJoiner(fq.fastqJoiner):

    def __init__(self, format, force_quality_encoding=None, sep="\t"):
        super(FastqJoiner, self).__init__(format, force_quality_encoding)
        self.id_manager = IDManager(sep)

    def join(self, read1, read2):
        force_quality_encoding = self.force_quality_encoding
        if not force_quality_encoding:
            if read1.is_ascii_encoded():
                force_quality_encoding = 'ascii'
            else:
                force_quality_encoding = 'decimal'
        read1 = read1.convert_read_to_format(
            self.format, force_quality_encoding=force_quality_encoding
            )
        read2 = read2.convert_read_to_format(
            self.format, force_quality_encoding=force_quality_encoding
            )
        #--
        t1, t2 = [
            self.id_manager.parse_id(r.identifier) for r in (read1, read2)
            ]
        if self.id_manager.get_read_number(t1) == 2:
            if not self.id_manager.get_read_number(t2) == 1:
                raise RuntimeError("input files are not from mated pairs")
            read1, read2 = read2, read1
            t1, t2 = t2, t1
        #--
        rval = fq.FASTQ_FORMATS[self.format]()
        rval.identifier = read1.identifier
        rval.description = "+"
        if len(read1.description) > 1:
            rval.description += rval.identifier[1:]
        if rval.sequence_space == 'color':
            # convert to nuc space, join, then convert back
            rval.sequence = rval.convert_base_to_color_space(
                read1.convert_color_to_base_space(read1.sequence) +
                read2.convert_color_to_base_space(read2.sequence)
                )
        else:
            rval.sequence = read1.sequence + read2.sequence
        if force_quality_encoding == 'ascii':
            rval.quality = read1.quality + read2.quality
        else:
            rval.quality = "%s %s" % (
                read1.quality.strip(), read2.quality.strip()
                )
        return rval

    def get_paired_identifier(self, read):
        return self.id_manager.get_paired_identifier(read)


def sniff_sep(fastq_fn):
    header = ""
    with open(fastq_fn) as f:
        while header == "":
            try:
                header = f.next().strip()
            except StopIteration:
                raise RuntimeError("%r: empty file" % (fastq_fn,))
    return re.search(r"\s", header).group()


def main():
    input1_filename = sys.argv[1]
    input1_type = sys.argv[2] or 'sanger'
    input2_filename = sys.argv[3]
    input2_type = sys.argv[4] or 'sanger'
    output_filename = sys.argv[5]
    fastq_style = sys.argv[6] or 'old'
    #--
    if input1_type != input2_type:
        print "WARNING: trying to join files of different types: %s and %s" % (
            input1_type, input2_type
            )
    if fastq_style == 'new':
        sep = sniff_sep(input1_filename)
        joiner = FastqJoiner(input1_type, sep=sep)
    else:
        joiner = fq.fastqJoiner(input1_type)
    #--
    input2 = fq.fastqNamedReader(open(input2_filename, 'rb'), input2_type)
    out = fq.fastqWriter(open(output_filename, 'wb'), format=input1_type)
    i = None
    skip_count = 0
    for i, fastq_read in enumerate(fq.fastqReader(
        open(input1_filename, 'rb' ), format=input1_type
        )):
        identifier = joiner.get_paired_identifier(fastq_read)
        fastq_paired = input2.get(identifier)
        if fastq_paired is None:
            skip_count += 1
        else:
            out.write(joiner.join(fastq_read, fastq_paired))
    out.close()
    if i is None:
        print "Your file contains no valid FASTQ reads"
    else:
        print input2.has_data()
        print 'Joined %s of %s read pairs (%.2f%%)' % (
            i - skip_count + 1, i + 1, (i - skip_count + 1) / (i + 1) * 100.0
            )


if __name__ == "__main__":
    main()
