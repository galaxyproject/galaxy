# This file is now part of the Galaxy Project, but due to historical reasons
# reflecting time developed outside of the Galaxy Project, this file is under
# the MIT license.
#
# The MIT License (MIT)
# Copyright (c) 2012,2013,2014,2015,2016 Peter Cock
# Copyright (c) 2012 Edward Kirton
# Copyright (c) 2013 Nicola Soranzo
# Copyright (c) 2014 Bjoern Gruening
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
"""NCBI BLAST datatypes.

Covers the ``blastxml`` format and the BLAST databases.
"""
import io
import logging
import os
from time import sleep

from galaxy.util import smart_str
from .data import (
    Data,
    get_file_peek,
    Text
)
from .sniff import build_sniff_from_prefix
from .xml import GenericXml

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class BlastXml(GenericXml):
    """NCBI Blast XML Output data"""
    file_ext = "blastxml"
    edam_format = "format_3331"
    edam_data = "data_0857"

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = 'NCBI Blast XML data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff_prefix(self, file_prefix):
        """Determines whether the file is blastxml

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('megablast_xml_parser_test1.blastxml')
        >>> BlastXml().sniff(fname)
        True
        >>> fname = get_test_fname('tblastn_four_human_vs_rhodopsin.blastxml')
        >>> BlastXml().sniff(fname)
        True
        >>> fname = get_test_fname('interval.interval')
        >>> BlastXml().sniff(fname)
        False
        """
        handle = file_prefix.string_io()
        line = handle.readline()
        if line.strip() != '<?xml version="1.0"?>':
            return False
        line = handle.readline()
        if line.strip() not in ['<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "http://www.ncbi.nlm.nih.gov/dtd/NCBI_BlastOutput.dtd">',
                                '<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "NCBI_BlastOutput.dtd">']:
            return False
        line = handle.readline()
        if line.strip() != '<BlastOutput>':
            return False
        return True

    def merge(split_files, output_file):
        """Merging multiple XML files is non-trivial and must be done in subclasses."""
        if len(split_files) == 1:
            # For one file only, use base class method (move/copy)
            return Text.merge(split_files, output_file)
        if not split_files:
            raise ValueError("Given no BLAST XML files, %r, to merge into %s"
                             % (split_files, output_file))
        with open(output_file, "w") as out:
            h = None
            old_header = None
            for f in split_files:
                if not os.path.isfile(f):
                    log.warning("BLAST XML file %s missing, retry in 1s..." % f)
                    sleep(1)
                if not os.path.isfile(f):
                    log.error("BLAST XML file %s missing" % f)
                    raise ValueError("BLAST XML file %s missing" % f)
                h = open(f)
                header = h.readline()
                if not header:
                    h.close()
                    # Retry, could be transient error with networked file system...
                    log.warning("BLAST XML file %s empty, retry in 1s..." % f)
                    sleep(1)
                    h = open(f)
                    header = h.readline()
                    if not header:
                        log.error("BLAST XML file %s was empty" % f)
                        raise ValueError("BLAST XML file %s was empty" % f)
                if header.strip() != '<?xml version="1.0"?>':
                    out.write(header)  # for diagnosis
                    h.close()
                    raise ValueError("%s is not an XML file!" % f)
                line = h.readline()
                header += line
                if line.strip() not in ['<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "http://www.ncbi.nlm.nih.gov/dtd/NCBI_BlastOutput.dtd">',
                                        '<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "NCBI_BlastOutput.dtd">']:
                    out.write(header)  # for diagnosis
                    h.close()
                    raise ValueError("%s is not a BLAST XML file!" % f)
                while True:
                    line = h.readline()
                    if not line:
                        out.write(header)  # for diagnosis
                        h.close()
                        raise ValueError("BLAST XML file %s ended prematurely" % f)
                    header += line
                    if "<Iteration>" in line:
                        break
                    if len(header) > 10000:
                        # Something has gone wrong, don't load too much into memory!
                        # Write what we have to the merged file for diagnostics
                        out.write(header)
                        h.close()
                        raise ValueError("The header in BLAST XML file %s is too long" % f)
                if "<BlastOutput>" not in header:
                    h.close()
                    raise ValueError("%s is not a BLAST XML file:\n%s\n..." % (f, header))
                if f == split_files[0]:
                    out.write(header)
                    old_header = header
                elif old_header is not None and old_header[:300] != header[:300]:
                    # Enough to check <BlastOutput_program> and <BlastOutput_version> match
                    h.close()
                    raise ValueError("BLAST XML headers don't match for %s and %s - have:\n%s\n...\n\nAnd:\n%s\n...\n"
                                     % (split_files[0], f, old_header[:300], header[:300]))
                else:
                    out.write("    <Iteration>\n")
                for line in h:
                    if "</BlastOutput_iterations>" in line:
                        break
                    # TODO - Increment <Iteration_iter-num> and if required automatic query names
                    # like <Iteration_query-ID>Query_3</Iteration_query-ID> to be increasing?
                    out.write(line)
                h.close()
            out.write("  </BlastOutput_iterations>\n")
            out.write("</BlastOutput>\n")
    merge = staticmethod(merge)


class _BlastDb(Data):
    """Base class for BLAST database datatype."""

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "BLAST database (multiple files)"
            dataset.blurb = "BLAST database (multiple files)"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "BLAST database (multiple files)"

    def display_data(self, trans, data, preview=False, filename=None,
                     to_ext=None, size=None, offset=None, **kwd):
        """
        If preview is `True` allows us to format the data shown in the central pane via the "eye" icon.
        If preview is `False` triggers download.
        """
        if not preview:
            return super(_BlastDb, self).display_data(trans,
                                                      data=data,
                                                      preview=preview,
                                                      filename=filename,
                                                      to_ext=to_ext,
                                                      size=size,
                                                      offset=offset,
                                                      **kwd)
        if self.file_ext == "blastdbn":
            title = "This is a nucleotide BLAST database"
        elif self.file_ext == "blastdbp":
            title = "This is a protein BLAST database"
        elif self.file_ext == "blastdbd":
            title = "This is a domain BLAST database"
        else:
            # Error?
            title = "This is a BLAST database."
        msg = ""
        try:
            # Try to use any text recorded in the dummy index file:
            with io.open(data.file_name, "rU", encoding='utf-8') as handle:
                msg = handle.read().strip()
        except Exception:
            pass
        if not msg:
            msg = title
        # Galaxy assumes HTML for the display of composite datatypes,
        return smart_str("<html><head><title>%s</title></head><body><pre>%s</pre></body></html>" % (title, msg))

    def merge(split_files, output_file):
        """Merge BLAST databases (not implemented for now)."""
        raise NotImplementedError("Merging BLAST databases is non-trivial (do this via makeblastdb?)")

    def split(cls, input_datasets, subdir_generator_function, split_params):
        """Split a BLAST database (not implemented for now)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split BLAST databases")


class BlastNucDb(_BlastDb, Data):
    """Class for nucleotide BLAST database files."""
    file_ext = 'blastdbn'
    allow_datatype_change = False
    composite_type = 'basic'

    def __init__(self, **kwd):
        Data.__init__(self, **kwd)
        self.add_composite_file('blastdb.nhr', is_binary=True)  # sequence headers
        self.add_composite_file('blastdb.nin', is_binary=True)  # index file
        self.add_composite_file('blastdb.nsq', is_binary=True)  # nucleotide sequences
        self.add_composite_file('blastdb.nal', is_binary=False, optional=True)  # alias ( -gi_mask option of makeblastdb)
        self.add_composite_file('blastdb.nhd', is_binary=True, optional=True)  # sorted sequence hash values ( -hash_index option of makeblastdb)
        self.add_composite_file('blastdb.nhi', is_binary=True, optional=True)  # index of sequence hash values ( -hash_index option of makeblastdb)
        self.add_composite_file('blastdb.nnd', is_binary=True, optional=True)  # sorted GI values ( -parse_seqids option of makeblastdb and gi present in the description lines)
        self.add_composite_file('blastdb.nni', is_binary=True, optional=True)  # index of GI values ( -parse_seqids option of makeblastdb and gi present in the description lines)
        self.add_composite_file('blastdb.nog', is_binary=True, optional=True)  # OID->GI lookup file ( -hash_index or -parse_seqids option of makeblastdb)
        self.add_composite_file('blastdb.nsd', is_binary=True, optional=True)  # sorted sequence accession values ( -hash_index or -parse_seqids option of makeblastdb)
        self.add_composite_file('blastdb.nsi', is_binary=True, optional=True)  # index of sequence accession values ( -hash_index or -parse_seqids option of makeblastdb)
#        self.add_composite_file('blastdb.00.idx', is_binary=True, optional=True)  # first volume of the MegaBLAST index generated by makembindex
# The previous line should be repeated for each index volume, with filename extensions like '.01.idx', '.02.idx', etc.
        self.add_composite_file('blastdb.shd', is_binary=True, optional=True)  # MegaBLAST index superheader (-old_style_index false option of makembindex)
#        self.add_composite_file('blastdb.naa', is_binary=True, optional=True)  # index of a WriteDB column for e.g. mask data
#        self.add_composite_file('blastdb.nab', is_binary=True, optional=True)  # data of a WriteDB column
#        self.add_composite_file('blastdb.nac', is_binary=True, optional=True)  # multiple byte order for a WriteDB column
# The previous 3 lines should be repeated for each WriteDB column, with filename extensions like ('.nba', '.nbb', '.nbc'), ('.nca', '.ncb', '.ncc'), etc.


class BlastProtDb(_BlastDb, Data):
    """Class for protein BLAST database files."""
    file_ext = 'blastdbp'
    allow_datatype_change = False
    composite_type = 'basic'

    def __init__(self, **kwd):
        Data.__init__(self, **kwd)
# Component file comments are as in BlastNucDb except where noted
        self.add_composite_file('blastdb.phr', is_binary=True)
        self.add_composite_file('blastdb.pin', is_binary=True)
        self.add_composite_file('blastdb.psq', is_binary=True)  # protein sequences
        self.add_composite_file('blastdb.phd', is_binary=True, optional=True)
        self.add_composite_file('blastdb.phi', is_binary=True, optional=True)
        self.add_composite_file('blastdb.pnd', is_binary=True, optional=True)
        self.add_composite_file('blastdb.pni', is_binary=True, optional=True)
        self.add_composite_file('blastdb.pog', is_binary=True, optional=True)
        self.add_composite_file('blastdb.psd', is_binary=True, optional=True)
        self.add_composite_file('blastdb.psi', is_binary=True, optional=True)
#        self.add_composite_file('blastdb.paa', is_binary=True, optional=True)
#        self.add_composite_file('blastdb.pab', is_binary=True, optional=True)
#        self.add_composite_file('blastdb.pac', is_binary=True, optional=True)
# The last 3 lines should be repeated for each WriteDB column, with filename extensions like ('.pba', '.pbb', '.pbc'), ('.pca', '.pcb', '.pcc'), etc.


class BlastDomainDb(_BlastDb, Data):
    """Class for domain BLAST database files."""
    file_ext = 'blastdbd'
    allow_datatype_change = False
    composite_type = 'basic'

    def __init__(self, **kwd):
        Data.__init__(self, **kwd)
        self.add_composite_file('blastdb.phr', is_binary=True)
        self.add_composite_file('blastdb.pin', is_binary=True)
        self.add_composite_file('blastdb.psq', is_binary=True)
        self.add_composite_file('blastdb.freq', is_binary=True, optional=True)
        self.add_composite_file('blastdb.loo', is_binary=True, optional=True)
        self.add_composite_file('blastdb.psd', is_binary=True, optional=True)
        self.add_composite_file('blastdb.psi', is_binary=True, optional=True)
        self.add_composite_file('blastdb.rps', is_binary=True, optional=True)
        self.add_composite_file('blastdb.aux', is_binary=True, optional=True)
