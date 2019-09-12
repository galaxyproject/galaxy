#!/usr/bin/python
'''This software extracts the seq, qual and ancillary information from an sff
file, like the ones used by the 454 sequencer.

Optionally, it can also split paired-end reads if given the linker sequence.
The splitting is done with maximum match, i.e., every occurence of the linker
sequence will be removed, even if occuring multiple times.'''

# copyright Jose Blanca and Bastien Chevreux
# COMAV institute, Universidad Politecnica de Valencia (UPV)
# Valencia, Spain

# additions to handle paired end reads by Bastien Chevreux
# bugfixes for linker specific lengths: Lionel Guy

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import os
import struct
import subprocess
import sys
import tempfile

__author__ = 'Jose Blanca and Bastien Chevreux'
__copyright__ = 'Copyright 2008, Jose Blanca, COMAV, and Bastien Chevreux'
__license__ = 'GPLv3 or later'
__version__ = '0.2.10'
__email__ = 'jblanca@btc.upv.es'
__status__ = 'beta'

fake_sff_name = 'fake_sff_name'

# readname as key: lines with matches from SSAHA, one best match
ssahapematches = {}
# linker readname as key: length of linker sequence
linkerlengths = {}

# set to true if something really fishy is going on with the sequences
stern_warning = True


def read_bin_fragment(struct_def, fileh, offset=0, data=None, byte_padding=None):
    '''It reads a chunk of a binary file.

    You have to provide the struct, a file object, the offset (where to start
    reading).
    Also you can provide an optional dict that will be populated with the
    extracted data.
    If a byte_padding is given the number of bytes read will be a multiple of
    that number, adding the required pad at the end.
    It returns the number of bytes reads and the data dict.
    '''
    if data is None:
        data = {}

    # we read each item
    bytes_read = 0
    for item in struct_def:
        # we go to the place and read
        fileh.seek(offset + bytes_read)
        n_bytes = struct.calcsize(item[1])
        buffer = fileh.read(n_bytes)
        read = struct.unpack('>' + item[1], buffer)
        if len(read) == 1:
            read = read[0]
        data[item[0]] = read
        bytes_read += n_bytes

    # if there is byte_padding the bytes_to_read should be a multiple of the
    # byte_padding
    if byte_padding is not None:
        pad = byte_padding
        bytes_read = ((bytes_read + pad - 1) // pad) * pad

    return (bytes_read, data)


def check_magic(magic):
    '''It checks that the magic number of the file matches the sff magic.'''
    if magic != 779314790:
        raise RuntimeError('This file does not seems to be an sff file.')


def check_version(version):
    '''It checks that the version is supported, otherwise it raises an error.'''
    supported = ('\x00', '\x00', '\x00', '\x01')
    i = 0
    for item in version:
        if version[i] != supported[i]:
            raise RuntimeError('SFF version not supported. Please contact the author of the software.')
        i += 1


def read_header(fileh):
    '''It reads the header from the sff file and returns a dict with the
    information'''
    # first we read the first part of the header
    head_struct = [
        ('magic_number', 'I'),
        ('version', 'cccc'),
        ('index_offset', 'Q'),
        ('index_length', 'I'),
        ('number_of_reads', 'I'),
        ('header_length', 'H'),
        ('key_length', 'H'),
        ('number_of_flows_per_read', 'H'),
        ('flowgram_format_code', 'B'),
    ]
    data = {}
    first_bytes, data = read_bin_fragment(struct_def=head_struct, fileh=fileh,
                                          offset=0, data=data)
    check_magic(data['magic_number'])
    check_version(data['version'])
    # now that we know the number_of_flows_per_read and the key_length
    # we can read the second part of the header
    struct2 = [
        ('flow_chars', str(data['number_of_flows_per_read']) + 'c'),
        ('key_sequence', str(data['key_length']) + 'c')
    ]
    read_bin_fragment(struct_def=struct2, fileh=fileh, offset=first_bytes, data=data)
    return data


def read_sequence(header, fileh, fposition):
    '''It reads one read from the sff file located at the fposition and
    returns a dict with the information.'''
    # the sequence struct
    read_header_1 = [
        ('read_header_length', 'H'),
        ('name_length', 'H'),
        ('number_of_bases', 'I'),
        ('clip_qual_left', 'H'),
        ('clip_qual_right', 'H'),
        ('clip_adapter_left', 'H'),
        ('clip_adapter_right', 'H'),
    ]

    def read_header_2(name_length):
        '''It returns the struct definition for the second part of the header'''
        return [('name', str(name_length) + 'c')]

    def read_data(number_of_bases):
        '''It returns the struct definition for the read data section.'''
        if header['flowgram_format_code'] == 1:
            flow_type = 'H'
        else:
            raise Exception('file version not supported')
        number_of_bases = str(number_of_bases)
        return [
            ('flowgram_values', str(header['number_of_flows_per_read']) + flow_type),
            ('flow_index_per_base', number_of_bases + 'B'),
            ('bases', number_of_bases + 'c'),
            ('quality_scores', number_of_bases + 'B'),
        ]

    data = {}
    # we read the first part of the header
    bytes_read, data = read_bin_fragment(struct_def=read_header_1,
                                    fileh=fileh, offset=fposition, data=data)

    read_bin_fragment(struct_def=read_header_2(data['name_length']),
                      fileh=fileh, offset=fposition + bytes_read, data=data)
    # we join the letters of the name
    data['name'] = ''.join(data['name'])
    offset = data['read_header_length']
    # we read the sequence and the quality
    read_data_st = read_data(data['number_of_bases'])
    bytes_read, data = read_bin_fragment(struct_def=read_data_st,
                                    fileh=fileh, offset=fposition + offset,
                                    data=data, byte_padding=8)
    # we join the bases
    data['bases'] = ''.join(data['bases'])

    # correct for the case the right clip is <= than the left clip
    # in this case, left clip is 0 are set to 0 (right clip == 0 means
    # "whole sequence")
    if data['clip_qual_right'] <= data['clip_qual_left']:
        data['clip_qual_right'] = 0
        data['clip_qual_left'] = 0
    if data['clip_adapter_right'] <= data['clip_adapter_left']:
        data['clip_adapter_right'] = 0
        data['clip_adapter_left'] = 0

    # the clipping section follows the NCBI's guidelines Trace Archive RFC
    # http://www.ncbi.nlm.nih.gov/Traces/trace.cgi?cmd=show&f=rfc&m=doc&s=rfc
    # if there's no adapter clip: qual -> vector
    # else:  qual-> qual
    #       adapter -> vector

    if not data['clip_adapter_left']:
        data['clip_adapter_left'], data['clip_qual_left'] = data['clip_qual_left'], data['clip_adapter_left']
    if not data['clip_adapter_right']:
        data['clip_adapter_right'], data['clip_qual_right'] = data['clip_qual_right'], data['clip_adapter_right']

    # see whether we have to override the minimum left clips
    if config['min_leftclip'] > 0:
        if data['clip_adapter_left'] > 0 and data['clip_adapter_left'] < config['min_leftclip']:
            data['clip_adapter_left'] = config['min_leftclip']
        if data['clip_qual_left'] > 0 and data['clip_qual_left'] < config['min_leftclip']:
            data['clip_qual_left'] = config['min_leftclip']

    # for handling the -c (clip) option gently, we already clip here
    #  and set all clip points to the sequence end points
    if config['clip']:
        data['bases'], data['quality_scores'] = clip_read(data)

        data['number_of_bases'] = len(data['bases'])
        data['clip_qual_right'] = data['number_of_bases']
        data['clip_adapter_right'] = data['number_of_bases']
        data['clip_qual_left'] = 0
        data['clip_adapter_left'] = 0

    return data['read_header_length'] + bytes_read, data


def sequences(fileh, header):
    '''It returns a generator with the data for each read.'''
    # now we can read all the sequences
    fposition = header['header_length']  # position in the file
    reads_read = 0
    while True:
        if fposition == header['index_offset']:
            # we have to skip the index section
            fposition += header['index_length']
            continue
        else:
            bytes_read, seq_data = read_sequence(header=header, fileh=fileh,
                                                 fposition=fposition)
            yield seq_data
            fposition += bytes_read
            reads_read += 1
            if reads_read >= header['number_of_reads']:
                break


def remove_last_xmltag_in_file(fname, tag=None):
    '''Given an xml file name and a tag, it removes the last tag of the
    file if it matches the given tag. Tag removal is performed via file
    truncation.

    It the given tag is not the last in the file, a RunTimeError will be
    raised.

    The resulting xml file will be not xml valid. This function is a hack
    that allows to append records to xml files in a quick and dirty way.
    '''

    fh = open(fname, 'r+')
    # we have to read from the end to the start of the file and keep the
    # string enclosed by </ >
    i = -1
    last_tag = []  # the chars that form the last tag
    while True:
        fh.seek(i, 2)
        char = fh.read(1)
        if not char.isspace():
            last_tag.append(char)
        if char == '<':
            break
        i -= 1

    # we have read the last tag backwards
    last_tag = ''.join(last_tag[::-1])
    # we remove the </ and >
    last_tag = last_tag.rstrip('>').lstrip('</')

    # we check that we're removing the asked tag
    if tag is not None and tag != last_tag:
        etxt = 'The given xml tag (%s) was not the last one in the file' % tag
        raise RuntimeError(etxt)

    # while we are at it: also remove all white spaces in that line :-)
    i -= 1
    while True:
        fh.seek(i, 2)
        char = fh.read(1)
        if not char == ' ' and not char == '\t':
            break
        if fh.tell() == 1:
            break
        i -= 1

    fh.truncate()

    fh.close()
    return last_tag


def create_basic_xml_info(readname, fname):
    '''Formats a number of read specific infos into XML format.
    Currently formated: name and the tags set from command line
    '''
    to_print = ['    <trace>\n']
    to_print.append('        <trace_name>')
    to_print.append(readname)
    to_print.append('</trace_name>\n')

    # extra information
    # do we have extra info for this file?
    info = None
    if config['xml_info']:
        # with this name?
        if fname in config['xml_info']:
            info = config['xml_info'][fname]
        else:
            # with no name?
            try:
                info = config['xml_info'][fake_sff_name]
            except KeyError:
                pass
    # we print the info that we have
    if info:
        for key in info:
            to_print.append('        <' + key + '>' + info[key] +
                            '</' + key + '>\n')

    return ''.join(to_print)


def create_clip_xml_info(readlen, adapl, adapr, quall, qualr):
    '''Takes the clip values of the read and formats them into XML
    Corrects "wrong" values that might have resulted through
    simplified calculations earlier in the process of conversion
    (especially during splitting of paired-end reads)
    '''

    to_print = [""]

    # if right borders are >= to read length, they don't need
    # to be printed
    if adapr >= readlen:
        adapr = 0
    if qualr >= readlen:
        qualr = 0

    # BaCh
    # when called via split_paired_end(), some values may be < 0
    #  (when clip values were 0 previously)
    # instead of putting tons of if clauses for different calculations there,
    #  I centralise corrective measure here
    # set all values <0 to 0

    if adapr < 0:
        adapr = 0
    if qualr < 0:
        qualr = 0
    if adapl < 0:
        adapl = 0
    if quall < 0:
        quall = 0

    if quall:
        to_print.append('        <clip_quality_left>')
        to_print.append(str(quall))
        to_print.append('</clip_quality_left>\n')
    if qualr:
        to_print.append('        <clip_quality_right>')
        to_print.append(str(qualr))
        to_print.append('</clip_quality_right>\n')
    if adapl:
        to_print.append('        <clip_vector_left>')
        to_print.append(str(adapl))
        to_print.append('</clip_vector_left>\n')
    if adapr:
        to_print.append('        <clip_vector_right>')
        to_print.append(str(adapr))
        to_print.append('</clip_vector_right>\n')
    return ''.join(to_print)


def create_xml_for_unpaired_read(data, fname):
    '''Given the data for one read it returns an str with the xml ancillary
    data.'''
    to_print = [create_basic_xml_info(data['name'], fname)]
    # clippings in the XML only if we do not hard clip
    if not config['clip']:
        to_print.append(create_clip_xml_info(data['number_of_bases'], data['clip_adapter_left'], data['clip_adapter_right'], data['clip_qual_left'], data['clip_qual_right']))
    to_print.append('    </trace>\n')
    return ''.join(to_print)


def format_as_fasta(name, seq, qual):
    name_line = ''.join(('>', name, '\n'))
    seqstring = ''.join((name_line, seq, '\n'))
    qual_line = ' '.join([str(q) for q in qual])
    qualstring = ''.join((name_line, qual_line, '\n'))
    return seqstring, qualstring


def format_as_fastq(name, seq, qual):
    qual_line = ''.join([chr(q + 33) for q in qual])
    seqstring = ''.join(('@', name, '\n', seq, '\n+\n', qual_line, '\n'))
    return seqstring


def get_read_data(data):
    '''Given the data for one read it returns 2 strs with the fasta seq
    and fasta qual.'''
    # seq and qual
    if config['mix_case']:
        seq = sequence_case(data)
        qual = data['quality_scores']
    else:
        seq = data['bases']
        qual = data['quality_scores']

    return seq, qual


def extract_read_info(data, fname):
    '''Given the data for one read it returns 3 strs with the fasta seq, fasta
    qual and xml ancillary data.'''
    seq, qual = get_read_data(data)
    seqstring, qualstring = format_as_fasta(data['name'], seq, qual)
    xmlstring = create_xml_for_unpaired_read(data, fname)
    return seqstring, qualstring, xmlstring


def write_sequence(name, seq, qual, seq_fh, qual_fh):
    '''Write sequence and quality FASTA and FASTA qual filehandles
    (or into FASTQ and XML)
    if sequence length is 0, don't write'''
    if len(seq) == 0:
        return

    if qual_fh is None:
        seq_fh.write(format_as_fastq(name, seq, qual))
    else:
        seqstring, qualstring = format_as_fasta(name, seq, qual)
        seq_fh.write(seqstring)
        qual_fh.write(qualstring)
    return


def write_unpaired_read(data, sff_fh, seq_fh, qual_fh, xml_fh):
    '''Writes an unpaired read into FASTA, FASTA qual and XML filehandles
    (or into FASTQ and XML)
    if sequence length is 0, don't write'''
    seq, qual = get_read_data(data)
    if len(seq) == 0:
        return

    write_sequence(data['name'], seq, qual, seq_fh, qual_fh)

    anci = create_xml_for_unpaired_read(data, sff_fh.name)
    if anci is not None:
        xml_fh.write(anci)
    return


def reverse_complement(seq):
    '''Returns the reverse complement of a DNA sequence as string'''
    compdict = {
        'a': 't',
        'c': 'g',
        'g': 'c',
        't': 'a',
        'u': 't',
        'm': 'k',
        'r': 'y',
        'w': 'w',
        's': 's',
        'y': 'r',
        'k': 'm',
        'v': 'b',
        'h': 'd',
        'd': 'h',
        'b': 'v',
        'x': 'x',
        'n': 'n',
        'A': 'T',
        'C': 'G',
        'G': 'C',
        'T': 'A',
        'U': 'T',
        'M': 'K',
        'R': 'Y',
        'W': 'W',
        'S': 'S',
        'Y': 'R',
        'K': 'M',
        'V': 'B',
        'H': 'D',
        'D': 'H',
        'B': 'V',
        'X': 'X',
        'N': 'N',
        '*': '*'}

    complseq = ''.join([compdict[base] for base in seq])
    # python hack to reverse a list/string/etc
    complseq = complseq[::-1]
    return complseq


def mask_sequence(seq, maskchar, fpos, tpos):
    '''Given a sequence, mask it with maskchar starting at fpos (including) and
    ending at tpos (excluding)
    '''
    if len(maskchar) > 1:
        raise RuntimeError("Internal error: more than one character given to mask_sequence")
    if fpos < 0:
        fpos = 0
    if tpos > len(seq):
        tpos = len(seq)

    newseq = ''.join((seq[:fpos], maskchar * (tpos - fpos), seq[tpos:]))

    return newseq


def fragment_sequences(sequence, qualities, splitchar):
    '''Works like split() on strings, except it does this on a sequence
    and the corresponding list with quality values.
    Returns a tuple for each fragment, each sublist has the fragment
    sequence as first and the fragment qualities as second elemnt'''
    # this is slow (due to zip and list appends... use an iterator over
    #  the sequence find find variations and splices on seq and qual

    if len(sequence) != len(qualities):
        print(sequence, qualities)
        raise RuntimeError("Internal error: length of sequence and qualities don't match???")

    retlist = ([])
    if len(sequence) == 0:
        return retlist

    actseq = ([])
    actqual = ([])
    if sequence[0] != splitchar:
        inseq = True
    else:
        inseq = False
    for char, qual in zip(sequence, qualities):
        if inseq:
            if char != splitchar:
                actseq.append(char)
                actqual.append(qual)
            else:
                retlist.append((''.join(actseq), actqual))
                actseq = ([])
                actqual = ([])
                inseq = False
        else:
            if char != splitchar:
                inseq = True
                actseq.append(char)
                actqual.append(qual)

    if inseq and len(actseq):
        retlist.append((''.join(actseq), actqual))

    return retlist


def calc_subseq_boundaries(maskedseq, maskchar):
    '''E.g.:
       ........xxxxxxxx..........xxxxxxxxxxxxxxxxxxxxx.........
       to
         (0,8),(8,16),(16,26),(26,47),(47,56)
    '''
    blist = ([])
    if len(maskedseq) == 0:
        return blist

    inmask = True
    if maskedseq[0] != maskchar:
        inmask = False

    start = 0
    for spos in range(len(maskedseq)):
        if inmask and maskedseq[spos] != maskchar:
            blist.append(([start, spos]))
            start = spos
            inmask = False
        elif not inmask and maskedseq[spos] == maskchar:
            blist.append(([start, spos]))
            start = spos
            inmask = True

    blist.append(([start, spos + 1]))

    return blist


def correct_for_smallhits(maskedseq, maskchar, linkername):
    '''If partial hits were found, take preventive measure: grow
        the masked areas by 20 bases in each direction
       Returns either unchanged "maskedseq" or a new sequence
        with some more characters masked.
    '''
    global linkerlengths

    if len(maskedseq) == 0:
        return maskedseq

    growl = 40
    growl2 = growl / 2

    boundaries = calc_subseq_boundaries(maskedseq, maskchar)

    foundpartial = False
    for bounds in boundaries:
        left, right = bounds
        if left != 0 and right != len(maskedseq):
            if maskedseq[left] == maskchar:
                # allow 10% discrepancy
                #    -linkerlengths[linkername]/10
                # that's a kind of safety net if there are slight sequencing
                #  errors in the linker itself
                if right - left < linkerlengths[linkername] - linkerlengths[linkername] / 10:
                    foundpartial = True

    if not foundpartial:
        return maskedseq

    # grow
    newseq = ""
    for bounds in boundaries:
        left, right = bounds
        if maskedseq[left] == maskchar:
            newseq += maskedseq[left:right]
        else:
            clearstart = 0
            if left > 0:
                clearstart = left + growl2
            clearstop = len(maskedseq)
            if right < len(maskedseq):
                clearstop = right - growl2

            if clearstop <= clearstart:
                newseq += maskchar * (right - left)
            else:
                if clearstart != left:
                    newseq += maskchar * growl2
                newseq += maskedseq[clearstart:clearstop]
                if clearstop != right:
                    newseq += maskchar * growl2

    return newseq


def split_paired_end(data, sff_fh, seq_fh, qual_fh, xml_fh):
    '''Splits a paired end read and writes sequences into FASTA, FASTA qual
    and XML traceinfo file. Returns the number of sequences created.

    As the linker sequence may be anywhere in the read, including the ends
    and overlapping with bad quality sequence, we need to perform some
    computing and eventually set new clip points.

    If the resulting split yields only one sequence (because linker
    was not present or overlapping with left or right clip), only one
    sequence will be written with ".fn" appended to the name.

    If the read can be split, two reads will be written. The side left of
    the linker will be named ".r" and will be written in reverse complement
    into the file to conform with what approximately all assemblers expect
    when reading paired-end data: reads in forward direction in file. The side
    right of the linker will be named ".f"

    If SSAHA found partial linker (linker sequences < length of linker),
    the sequences will get a "_pl" furthermore be cut back thoroughly.

    If SSAHA found multiple occurences of the linker, the names will get an
    additional "_mlc" within the name to show that there was "multiple
    linker contamination".

    For multiple or partial linker, the "good" parts of the reads are
    stored with a ".part<number>" name, additionally they will not get
    template information in the XML
    '''
    global ssahapematches

    maskchar = "#"

    numseqs = 0
    readname = data['name']
    readlen = data['number_of_bases']

    leftclip, rightclip = return_merged_clips(data)
    seq, qual = get_read_data(data)

    maskedseq = seq
    if leftclip > 0:
        maskedseq = mask_sequence(maskedseq, maskchar, 0, leftclip - 1)
    if rightclip < len(maskedseq):
        maskedseq = mask_sequence(maskedseq, maskchar, rightclip, len(maskedseq))

    leftclip, rightclip = return_merged_clips(data)
    readlen = data['number_of_bases']

    for match in ssahapematches[data['name']]:
        int(match[0])
        linkername = match[2]
        leftreadhit = int(match[3])
        rightreadhit = int(match[4])

        maskedseq = mask_sequence(maskedseq, maskchar, leftreadhit - 1, rightreadhit)

    correctedseq = correct_for_smallhits(maskedseq, maskchar, linkername)

    if len(maskedseq) != len(correctedseq):
        raise RuntimeError("Internal error: maskedseq != correctedseq")

    partialhits = False
    if correctedseq != maskedseq:
        partialhits = True
        readname += "_pl"
        maskedseq = correctedseq

    fragments = fragment_sequences(maskedseq, qual, maskchar)

    mlcflag = False

    if len(fragments) > 2:
        mlcflag = True
        readname += "_mlc"

    # print fragments
    if mlcflag or partialhits:
        fragcounter = 1
        readname += ".part"
        for frag in fragments:
            actseq = frag[0]
            if len(actseq) >= 20:
                actqual = frag[1]
                oname = readname + str(fragcounter)
                write_sequence(oname, actseq, actqual, seq_fh, qual_fh)
                to_print = [create_basic_xml_info(oname, sff_fh.name)]
                # No clipping in XML ... the multiple and partial fragments
                #  are clipped "hard"
                # No template ID and trace_end: we don't know the
                #  orientation of the frahments. Even if it were
                #  only two, the fact we had multiple linkers
                #  says something went wrong, so simply do not
                #  write any paired-end information for all these fragments
                to_print.append('    </trace>\n')
                xml_fh.write(''.join(to_print))
                numseqs += 1
                fragcounter += 1
    else:
        if len(fragments) > 2:
            raise RuntimeError("Unexpected: more than two fragments detected in " + readname + ". please contact the authors.")
        # nothing will happen for 0 fragments
        if len(fragments) == 1:
            boundaries = calc_subseq_boundaries(maskedseq, maskchar)
            if len(boundaries) < 1 or len(boundaries) > 3:
                raise RuntimeError("Unexpected case: ", str(len(boundaries)), "boundaries for 1 fragment of ", readname)
            if len(boundaries) == 3:
                # case: mask char on both sides of sequence
                data['clip_adapter_left'] = boundaries[0][1]
                data['clip_adapter_right'] = boundaries[2][0]
            elif len(boundaries) == 2:
                # case: mask char left or right of sequence
                if maskedseq[0] == maskchar:
                    # case: mask char left
                    data['clip_adapter_left'] = boundaries[0][1]
                else:
                    # case: mask char right
                    data['clip_adapter_right'] = boundaries[1][0]
            data['name'] = data['name'] + ".fn"
            write_unpaired_read(data, sff_fh, seq_fh, qual_fh, xml_fh)
            numseqs = 1
        elif len(fragments) == 2:
            oname = readname + ".r"
            seq, qual = get_read_data(data)

            startsearch = False
            for spos in range(len(maskedseq)):
                if maskedseq[spos] != maskchar:
                    startsearch = True
                else:
                    if startsearch:
                        break

            lseq = seq[:spos]
            actseq = reverse_complement(lseq)
            lreadlen = len(actseq)
            lqual = qual[:spos]
            # python hack to reverse a list/string/etc
            lqual = lqual[::-1]

            write_sequence(oname, actseq, lqual, seq_fh, qual_fh)

            to_print = [create_basic_xml_info(oname, sff_fh.name)]
            to_print.append(create_clip_xml_info(lreadlen, 0, lreadlen + 1 - data['clip_adapter_left'], 0, lreadlen + 1 - data['clip_qual_left']))
            to_print.append('        <template_id>')
            to_print.append(readname)
            to_print.append('</template_id>\n')
            to_print.append('        <trace_end>r</trace_end>\n')
            to_print.append('    </trace>\n')
            xml_fh.write(''.join(to_print))

            oname = readname + ".f"
            startsearch = False
            for spos in range(len(maskedseq) - 1, -1, -1):
                if maskedseq[spos] != maskchar:
                    startsearch = True
                else:
                    if startsearch:
                        break

            actseq = seq[spos + 1:]
            actqual = qual[spos + 1:]

            write_sequence(oname, actseq, actqual, seq_fh, qual_fh)

            rreadlen = len(actseq)
            to_print = [create_basic_xml_info(oname, sff_fh.name)]
            to_print.append(create_clip_xml_info(rreadlen, 0, rreadlen - (readlen - data['clip_adapter_right']), 0, rreadlen - (readlen - data['clip_qual_right'])))
            to_print.append('        <template_id>')
            to_print.append(readname)
            to_print.append('</template_id>\n')
            to_print.append('        <trace_end>f</trace_end>\n')
            to_print.append('    </trace>\n')
            xml_fh.write(''.join(to_print))
            numseqs = 2

    return numseqs


def extract_reads_from_sff(config, sff_files):
    '''Given the configuration and the list of sff_files it writes the seqs,
    qualities and ancillary data into the output file(s).

    If file for paired-end linker was given, first extracts all sequences
    of an SFF and searches these against the linker(s) with SSAHA2 to
    create needed information to split reads.
    '''
    global ssahapematches

    if len(sff_files) == 0:
        raise RuntimeError("No SFF file given?")

    # we go through all input files
    for sff_file in sff_files:
        if not os.path.getsize(sff_file):
            raise RuntimeError('Empty file? : ' + sff_file)
        fh = open(sff_file, 'r')
        fh.close()

    openmode = 'w'
    if config['append']:
        openmode = 'a'

    seq_fh = open(config['seq_fname'], openmode)
    xml_fh = open(config['xml_fname'], openmode)
    if config['want_fastq']:
        qual_fh = None
        try:
            os.remove(config['qual_fname'])
        except Exception:
            pass
    else:
        qual_fh = open(config['qual_fname'], openmode)

    if not config['append']:
        xml_fh.write('<?xml version="1.0"?>\n<trace_volume>\n')
    else:
        remove_last_xmltag_in_file(config['xml_fname'], "trace_volume")

    # we go through all input files
    for sff_file in sff_files:
        ssahapematches.clear()

        seqcheckstore = ([])

        debug = 0

        if not debug and config['pelinker_fname']:
            sys.stdout.flush()

            if 0:
                # for debugging
                pid = os.getpid()
                tmpfasta_fname = 'sffe.tmp.' + str(pid) + '.fasta'
                tmpfasta_fh = open(tmpfasta_fname, 'w')
            else:
                tmpfasta_fh = tempfile.NamedTemporaryFile(prefix='sffeseqs_',
                                                          suffix='.fasta')

            sff_fh = open(sff_file, 'rb')
            header_data = read_header(fileh=sff_fh)
            for seq_data in sequences(fileh=sff_fh, header=header_data):
                seq, qual = get_read_data(seq_data)
                seqstring, qualstring = format_as_fasta(seq_data['name'], seq, qual)
                tmpfasta_fh.write(seqstring)
            tmpfasta_fh.seek(0)

            if 0:
                # for debugging
                tmpssaha_fname = 'sffe.tmp.' + str(pid) + '.ssaha2'
                tmpssaha_fh = open(tmpssaha_fname, 'w+')
            else:
                tmpssaha_fh = tempfile.NamedTemporaryFile(prefix='sffealig_',
                                                          suffix='.ssaha2')

            launch_ssaha(config['pelinker_fname'], tmpfasta_fh.name, tmpssaha_fh)
            tmpfasta_fh.close()

            tmpssaha_fh.seek(0)
            read_ssaha_data(tmpssaha_fh)
            tmpssaha_fh.close()

        if debug:
            tmpssaha_fh = open("sffe.tmp.10634.ssaha2", 'r')
            read_ssaha_data(tmpssaha_fh)

        sys.stdout.flush()
        sff_fh = open(sff_file, 'rb')
        header_data = read_header(fileh=sff_fh)

        # now convert all reads
        nseqs_sff = 0
        nseqs_out = 0
        for seq_data in sequences(fileh=sff_fh, header=header_data):
            nseqs_sff += 1

            seq, qual = clip_read(seq_data)
            seqcheckstore.append(seq[0:50])

            if seq_data['name'] in ssahapematches:
                nseqs_out += split_paired_end(seq_data, sff_fh, seq_fh, qual_fh, xml_fh)
            else:
                if config['pelinker_fname']:
                    seq_data['name'] = seq_data['name'] + ".fn"
                write_unpaired_read(seq_data, sff_fh, seq_fh, qual_fh, xml_fh)
                nseqs_out += 1
        sff_fh.close()

        check_for_dubious_startseq(seqcheckstore, sff_file, seq_data)
        seqcheckstore = ([])

    xml_fh.write('</trace_volume>\n')

    xml_fh.close()
    seq_fh.close()
    if qual_fh is not None:
        qual_fh.close()

    return


def check_for_dubious_startseq(seqcheckstore, sffname, seqdata):
    global stern_warning

    foundproblem = ""
    for checklen in range(1, len(seqcheckstore[0])):
        foundinloop = False
        seqdict = {}
        for seq in seqcheckstore:
            shortseq = seq[0:checklen]
            if shortseq in seqdict:
                seqdict[shortseq] += 1
            else:
                seqdict[shortseq] = 1

        for shortseq, count in seqdict.items():
            if float(count) / len(seqcheckstore) >= 0.5:
                foundinloop = True
                stern_warning
                foundproblem = "\n" + "*" * 80
                foundproblem += "\nWARNING: "
                foundproblem += "weird sequences in file " + sffname + "\n\n"
                foundproblem += "After applying left clips, " + str(count) + " sequences (="
                foundproblem += '%.0f' % (100.0 * float(count) / len(seqcheckstore))
                foundproblem += "%) start with these bases:\n" + shortseq
                foundproblem += "\n\nThis does not look sane.\n\n"
                foundproblem += "Countermeasures you *probably* must take:\n"
                foundproblem += "1) Make your sequence provider aware of that problem and ask whether this can be\n    corrected in the SFF.\n"
                foundproblem += "2) If you decide that this is not normal and your sequence provider does not\n    react, use the --min_left_clip of sff_extract.\n"
                left, right = return_merged_clips(seqdata)
                foundproblem += "    (Probably '--min_left_clip=" + str(left + len(shortseq)) + "' but you should cross-check that)\n"
                foundproblem += "*" * 80 + "\n"
        if not foundinloop:
            break
    if len(foundproblem):
        print(foundproblem)


def parse_extra_info(info):
    '''It parses the information that will go in the xml file.

    There are two formats accepted for the extra information:
    key1:value1, key2:value2
    or:
    file1.sff{key1:value1, key2:value2};file2.sff{key3:value3}
    '''
    if not info:
        return info
    finfos = info.split(';')  # information for each file
    data_for_files = {}
    for finfo in finfos:
        # we split the file name from the rest
        items = finfo.split('{')
        if len(items) == 1:
            fname = fake_sff_name
            info = items[0]
        else:
            fname = items[0]
            info = items[1]
        # now we get each key,value pair in the info
        info = info.replace('}', '')
        data = {}
        for item in info.split(','):
            key, value = item.strip().split(':')
            key = key.strip()
            value = value.strip()
            data[key] = value
        data_for_files[fname] = data
    return data_for_files


def return_merged_clips(data):
    '''It returns the left and right positions to clip.'''
    def max(a, b):
        '''It returns the max of the two given numbers.

        It won't take into account the zero values.
        '''
        if not a and not b:
            return None
        if not a:
            return b
        if not b:
            return a
        if a >= b:
            return a
        else:
            return b

    def min(a, b):
        '''It returns the min of the two given numbers.

        It won't take into account the zero values.
        '''
        if not a and not b:
            return None
        if not a:
            return b
        if not b:
            return a
        if a <= b:
            return a
        else:
            return b
    left = max(data['clip_adapter_left'], data['clip_qual_left'])
    right = min(data['clip_adapter_right'], data['clip_qual_right'])
    # maybe both clips where zero
    if left is None:
        left = 1
    if right is None:
        right = data['number_of_bases']
    return left, right


def sequence_case(data):
    '''Given the data for one read it returns the seq with mixed case.

    The regions to be clipped will be lower case and the rest upper case.
    '''
    left, right = return_merged_clips(data)
    seq = data['bases']
    if left >= right:
        new_seq = seq.lower()
    else:
        new_seq = ''.join((seq[:left - 1].lower(), seq[left - 1:right], seq[right:].lower()))

    return new_seq


def clip_read(data):
    '''Given the data for one read it returns clipped seq and qual.'''
    qual = data['quality_scores']
    left, right = return_merged_clips(data)
    seq = data['bases']
    qual = data['quality_scores']
    new_seq = seq[left - 1:right]
    new_qual = qual[left - 1:right]

    return new_seq, new_qual


def tests_for_ssaha():
    '''Tests whether SSAHA2 can be successfully called.'''
    try:
        print("Testing whether SSAHA2 is installed and can be launched ... ", end=' ')
        sys.stdout.flush()
        fh = open('/dev/null', 'w')
        subprocess.call(["ssaha2"], stdout=fh)
        fh.close()
        print("ok.")
    except Exception:
        print("nope? Uh oh ...\n\n")
        raise RuntimeError('Could not launch ssaha2. Have you installed it? Is it in your path?')


def load_linker_sequences(linker_fname):
    '''Loads all linker sequences into memory, storing only the length
    of each linker.'''
    global linkerlengths

    if not os.path.getsize(linker_fname):
        raise RuntimeError("File empty? '" + linker_fname + "'")
    fh = open(linker_fname, 'r')
    linkerseqs = read_fasta(fh)
    if len(linkerseqs) == 0:
        raise RuntimeError(linker_fname + ": no sequence found?")
    for i in linkerseqs:
        if i.name in linkerlengths:
            raise RuntimeError(linker_fname + ": sequence '" + i.name + "' present multiple times. Aborting.")
        linkerlengths[i.name] = len(i.sequence)
    fh.close()


def launch_ssaha(linker_fname, query_fname, output_fh):
    '''Launches SSAHA2 on the linker and query file, string SSAHA2 output
    into the output filehandle'''
    tests_for_ssaha()

    try:
        print("Searching linker sequences with SSAHA2 (this may take a while) ... ", end=' ')
        sys.stdout.flush()
        retcode = subprocess.call(["ssaha2", "-output", "ssaha2", "-solexa", "-kmer", "4", "-skip", "1", linker_fname, query_fname], stdout=output_fh)
        if retcode:
            raise RuntimeError('Ups.')
        else:
            print("ok.")
    except Exception:
        print("\n")
        raise RuntimeError('An error occurred during the SSAHA2 execution, aborting.')


def read_ssaha_data(ssahadata_fh):
    '''Given file handle, reads file generated with SSAHA2 (with default
    output format) and stores all matches as list ssahapematches
    (ssaha paired-end matches) dictionary'''
    global ssahapematches

    print("Parsing SSAHA2 result file ... ", end=' ')
    sys.stdout.flush()

    for line in ssahadata_fh:
        if line.startswith('ALIGNMENT'):
            ml = line.split()
            if len(ml) != 12:
                print("\n", line, end=' ')
                raise RuntimeError('Expected 12 elements in the SSAHA2 line with ALIGMENT keyword, but found ' + str(len(ml)))
            if ml[2] not in ssahapematches:
                ssahapematches[ml[2]] = ([])
            if ml[8] == 'F':
                # store everything except the first element (output
                #  format name (ALIGNMENT)) and the last element
                #  (length)
                ssahapematches[ml[2]].append(ml[1:-1])
            else:
                ml[4], ml[5] = ml[5], ml[4]
                ssahapematches[ml[2]].append(ml[1:-1])

    print("done.")


##########################################################################
#
# BaCh: This block was shamelessly copied from
#  http://python.genedrift.org/2007/07/04/reading-fasta-files-conclusion/
# and then subsequently modified to read fasta correctly
# It's still not fool proof, but should be good enough
#
##########################################################################

class Fasta(object):
    def __init__(self, name, sequence):
        self.name = name
        self.sequence = sequence


def read_fasta(file):
    items = []
    aninstance = Fasta('', '')
    linenum = 0
    for line in file:
        linenum += 1
        if line.startswith(">"):
            if len(aninstance.sequence):
                items.append(aninstance)
                aninstance = Fasta('', '')
            # name == all characters until the first whitespace
            #  (split()[0]) but without the starting ">" ([1:])
            aninstance.name = line.split()[0][1:]
            aninstance.sequence = ''
            if len(aninstance.name) == 0:
                raise RuntimeError(file.name + ': no name in line ' + str(linenum) + '?')

        else:
            if len(aninstance.name) == 0:
                raise RuntimeError(file.name + ': no sequence header at line ' + str(linenum) + '?')
            aninstance.sequence += line.strip()

    if len(aninstance.name) and len(aninstance.sequence):
        items.append(aninstance)

    return items
##########################################################################


def version_string():
    return "sff_extract " + __version__


def read_config():
    '''It reads the configuration options from the command line arguments and
    it returns a dict with them.'''
    from optparse import OptionParser, OptionGroup
    usage = "usage: %prog [options] sff1 sff2 ..."
    desc = "Extract sequences from 454 SFF files into FASTA, FASTA quality"\
           " and XML traceinfo format. When a paired-end linker sequence"\
           " is given (-l), use SSAHA2 to scan the sequences for the linker,"\
           " then split the sequences, removing the linker."
    parser = OptionParser(usage=usage, version=version_string(), description=desc)
    parser.add_option('-a', '--append', action="store_true", dest='append',
            help='append output to existing files', default=False)
    parser.add_option('-i', '--xml_info', dest='xml_info',
            help='extra info to write in the xml file')
    parser.add_option("-l", "--linker_file", dest="pelinker_fname",
            help="FASTA file with paired-end linker sequences", metavar="FILE")

    group = OptionGroup(parser, "File name options", "")
    group.add_option('-c', '--clip', action="store_true", dest='clip',
                     help='clip (completely remove) ends with low qual and/or adaptor sequence', default=False)
    group.add_option('-u', '--upper_case', action="store_false", dest='mix_case',
                     help='all bases in upper case, including clipped ends', default=True)
    group.add_option('', '--min_left_clip', dest='min_leftclip',
                     metavar="INTEGER", type="int",
                     help='if the left clip coming from the SFF is smaller than this value, override it', default=0)
    group.add_option('-Q', '--fastq', action="store_true", dest='want_fastq',
                     help='store as FASTQ file instead of FASTA + FASTA quality file', default=False)
    parser.add_option_group(group)

    group = OptionGroup(parser, "File name options", "")
    group.add_option("-o", "--out_basename", dest="basename",
                     help="base name for all output files")
    group.add_option("-s", "--seq_file", dest="seq_fname",
                     help="output sequence file name", metavar="FILE")
    group.add_option("-q", "--qual_file", dest="qual_fname",
                     help="output quality file name", metavar="FILE")
    group.add_option("-x", "--xml_file", dest="xml_fname",
                     help="output ancillary xml file name", metavar="FILE")
    parser.add_option_group(group)

    # default fnames
    # is there an sff file?
    basename = 'reads'
    if sys.argv[-1][-4:].lower() == '.sff':
        basename = sys.argv[-1][:-4]
    def_seq_fname = basename + '.fasta'
    def_qual_fname = basename + '.fasta.qual'
    def_xml_fname = basename + '.xml'
    def_pelinker_fname = ''
    parser.set_defaults(seq_fname=def_seq_fname)
    parser.set_defaults(qual_fname=def_qual_fname)
    parser.set_defaults(xml_fname=def_xml_fname)
    parser.set_defaults(pelinker_fname=def_pelinker_fname)

    # we parse the cmd line
    (options, args) = parser.parse_args()

    # we put the result in a dict
    global config
    config = {}
    for property in dir(options):
        if property[0] == '_' or property in ('ensure_value', 'read_file', 'read_module'):
            continue
        config[property] = getattr(options, property)

    if config['basename'] is None:
        config['basename'] = basename

    # if we have not set a file name with -s, -q or -x we set the basename
    # based file name
    if config['want_fastq']:
        config['qual_fname'] = ''
        if config['seq_fname'] == def_seq_fname:
            config['seq_fname'] = config['basename'] + '.fastq'
    else:
        if config['seq_fname'] == def_seq_fname:
            config['seq_fname'] = config['basename'] + '.fasta'
        if config['qual_fname'] == def_qual_fname:
            config['qual_fname'] = config['basename'] + '.fasta.qual'

    if config['xml_fname'] == def_xml_fname:
        config['xml_fname'] = config['basename'] + '.xml'

    # we parse the extra info for the xml file
    config['xml_info'] = parse_extra_info(config['xml_info'])
    return config, args


def testsome():
    sys.exit()
    return


def main():
    argv = sys.argv
    if len(argv) == 1:
        sys.argv.append('-h')
        read_config()
        sys.exit()
    try:
        config, args = read_config()

        if config['pelinker_fname']:
            load_linker_sequences(config['pelinker_fname'])
        if len(args) == 0:
            raise RuntimeError("No SFF file given?")
        extract_reads_from_sff(config, args)
    except (OSError, IOError, RuntimeError) as errval:
        print(errval)
        return 1

    if stern_warning:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
