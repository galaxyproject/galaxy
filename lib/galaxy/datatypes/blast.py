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
import logging
import os
from time import sleep
from typing import (
    Callable,
    Dict,
    List,
    Optional,
)

from galaxy.datatypes.protocols import (
    DatasetHasHidProtocol,
    DatasetProtocol,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.util import smart_str
from .data import (
    Data,
    get_file_peek,
    Text,
)
from .xml import GenericXml

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class BlastXml(GenericXml):
    """NCBI Blast XML Output data"""

    file_ext = "blastxml"
    edam_format = "format_3331"
    edam_data = "data_0857"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.get_file_name())
            dataset.blurb = "NCBI Blast XML data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
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
        if line.strip() not in [
            '<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "http://www.ncbi.nlm.nih.gov/dtd/NCBI_BlastOutput.dtd">',
            '<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "NCBI_BlastOutput.dtd">',
        ]:
            return False
        line = handle.readline()
        if line.strip() != "<BlastOutput>":
            return False
        return True

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """Merging multiple XML files is non-trivial and must be done in subclasses."""
        if len(split_files) == 1:
            # For one file only, use base class method (move/copy)
            return Text.merge(split_files, output_file)
        if not split_files:
            raise ValueError(f"Given no BLAST XML files, {split_files!r}, to merge into {output_file}")
        with open(output_file, "w") as out:
            h = None
            old_header = None
            for f in split_files:
                if not os.path.isfile(f):
                    log.warning(f"BLAST XML file {f} missing, retry in 1s...")
                    sleep(1)
                if not os.path.isfile(f):
                    log.error(f"BLAST XML file {f} missing")
                    raise ValueError(f"BLAST XML file {f} missing")
                h = open(f)
                header = h.readline()
                if not header:
                    h.close()
                    # Retry, could be transient error with networked file system...
                    log.warning(f"BLAST XML file {f} empty, retry in 1s...")
                    sleep(1)
                    h = open(f)
                    header = h.readline()
                    if not header:
                        log.error(f"BLAST XML file {f} was empty")
                        raise ValueError(f"BLAST XML file {f} was empty")
                if header.strip() != '<?xml version="1.0"?>':
                    out.write(header)  # for diagnosis
                    h.close()
                    raise ValueError(f"{f} is not an XML file!")
                line = h.readline()
                header += line
                if line.strip() not in [
                    '<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "http://www.ncbi.nlm.nih.gov/dtd/NCBI_BlastOutput.dtd">',
                    '<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "NCBI_BlastOutput.dtd">',
                ]:
                    out.write(header)  # for diagnosis
                    h.close()
                    raise ValueError(f"{f} is not a BLAST XML file!")
                while True:
                    line = h.readline()
                    if not line:
                        out.write(header)  # for diagnosis
                        h.close()
                        raise ValueError(f"BLAST XML file {f} ended prematurely")
                    header += line
                    if "<Iteration>" in line:
                        break
                    if len(header) > 10000:
                        # Something has gone wrong, don't load too much into memory!
                        # Write what we have to the merged file for diagnostics
                        out.write(header)
                        h.close()
                        raise ValueError(f"The header in BLAST XML file {f} is too long")
                if "<BlastOutput>" not in header:
                    h.close()
                    raise ValueError(f"{f} is not a BLAST XML file:\n{header}\n...")
                if f == split_files[0]:
                    out.write(header)
                    old_header = header
                elif old_header is not None and old_header[:300] != header[:300]:
                    # Enough to check <BlastOutput_program> and <BlastOutput_version> match
                    h.close()
                    raise ValueError(
                        f"BLAST XML headers don't match for {split_files[0]} and {f} - have:\n{old_header[:300]}\n...\n\nAnd:\n{header[:300]}\n...\n"
                    )
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


class _BlastDb(Data):
    """Base class for BLAST database datatype."""

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "BLAST database (multiple files)"
            dataset.blurb = "BLAST database (multiple files)"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "BLAST database (multiple files)"

    def display_data(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        offset: Optional[int] = None,
        ck_size: Optional[int] = None,
        **kwd,
    ):
        """
        If preview is `True` allows us to format the data shown in the central pane via the "eye" icon.
        If preview is `False` triggers download.
        """
        headers = kwd.get("headers", {})
        if not preview:
            return super().display_data(
                trans,
                dataset=dataset,
                preview=preview,
                filename=filename,
                to_ext=to_ext,
                offset=offset,
                ck_size=ck_size,
                **kwd,
            )
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
            with open(dataset.get_file_name(), encoding="utf-8") as handle:
                msg = handle.read().strip()
        except Exception:
            pass
        if not msg:
            msg = title
        # Galaxy assumes HTML for the display of composite datatypes,
        return smart_str(f"<html><head><title>{title}</title></head><body><pre>{msg}</pre></body></html>"), headers

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """Merge BLAST databases (not implemented for now)."""
        raise NotImplementedError("Merging BLAST databases is non-trivial (do this via makeblastdb?)")

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Optional[Dict]) -> None:
        """Split a BLAST database (not implemented for now)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split BLAST databases")


class BlastNucDb(_BlastDb):
    """Class for nucleotide BLAST database files."""

    file_ext = "blastdbn"
    composite_type = "basic"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("blastdb.nhr", is_binary=True)  # sequence headers
        self.add_composite_file("blastdb.nin", is_binary=True)  # index file
        self.add_composite_file("blastdb.nsq", is_binary=True)  # nucleotide sequences
        self.add_composite_file(
            "blastdb.nal", is_binary=False, optional=True
        )  # alias ( -gi_mask option of makeblastdb)
        self.add_composite_file(
            "blastdb.nhd", is_binary=True, optional=True
        )  # sorted sequence hash values ( -hash_index option of makeblastdb)
        self.add_composite_file(
            "blastdb.nhi", is_binary=True, optional=True
        )  # index of sequence hash values ( -hash_index option of makeblastdb)
        self.add_composite_file(
            "blastdb.nnd", is_binary=True, optional=True
        )  # sorted GI values ( -parse_seqids option of makeblastdb and gi present in the description lines)
        self.add_composite_file(
            "blastdb.nni", is_binary=True, optional=True
        )  # index of GI values ( -parse_seqids option of makeblastdb and gi present in the description lines)
        self.add_composite_file(
            "blastdb.nog", is_binary=True, optional=True
        )  # OID->GI lookup file ( -hash_index or -parse_seqids option of makeblastdb)
        self.add_composite_file(
            "blastdb.nsd", is_binary=True, optional=True
        )  # sorted sequence accession values ( -hash_index or -parse_seqids option of makeblastdb)
        self.add_composite_file(
            "blastdb.nsi", is_binary=True, optional=True
        )  # index of sequence accession values ( -hash_index or -parse_seqids option of makeblastdb)
        #        self.add_composite_file('blastdb.00.idx', is_binary=True, optional=True)  # first volume of the MegaBLAST index generated by makembindex
        # The previous line should be repeated for each index volume, with filename extensions like '.01.idx', '.02.idx', etc.
        self.add_composite_file(
            "blastdb.shd", is_binary=True, optional=True
        )  # MegaBLAST index superheader (-old_style_index false option of makembindex)


#        self.add_composite_file('blastdb.naa', is_binary=True, optional=True)  # index of a WriteDB column for e.g. mask data
#        self.add_composite_file('blastdb.nab', is_binary=True, optional=True)  # data of a WriteDB column
#        self.add_composite_file('blastdb.nac', is_binary=True, optional=True)  # multiple byte order for a WriteDB column
# The previous 3 lines should be repeated for each WriteDB column, with filename extensions like ('.nba', '.nbb', '.nbc'), ('.nca', '.ncb', '.ncc'), etc.


class BlastProtDb(_BlastDb):
    """Class for protein BLAST database files."""

    file_ext = "blastdbp"
    composite_type = "basic"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        # Component file comments are as in BlastNucDb except where noted
        self.add_composite_file("blastdb.phr", is_binary=True)
        self.add_composite_file("blastdb.pin", is_binary=True)
        self.add_composite_file("blastdb.psq", is_binary=True)  # protein sequences
        self.add_composite_file("blastdb.phd", is_binary=True, optional=True)
        self.add_composite_file("blastdb.phi", is_binary=True, optional=True)
        self.add_composite_file("blastdb.pnd", is_binary=True, optional=True)
        self.add_composite_file("blastdb.pni", is_binary=True, optional=True)
        self.add_composite_file("blastdb.pog", is_binary=True, optional=True)
        self.add_composite_file("blastdb.psd", is_binary=True, optional=True)
        self.add_composite_file("blastdb.psi", is_binary=True, optional=True)


#        self.add_composite_file('blastdb.paa', is_binary=True, optional=True)
#        self.add_composite_file('blastdb.pab', is_binary=True, optional=True)
#        self.add_composite_file('blastdb.pac', is_binary=True, optional=True)
# The last 3 lines should be repeated for each WriteDB column, with filename extensions like ('.pba', '.pbb', '.pbc'), ('.pca', '.pcb', '.pcc'), etc.


class BlastDomainDb(_BlastDb):
    """Class for domain BLAST database files."""

    file_ext = "blastdbd"
    composite_type = "basic"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("blastdb.phr", is_binary=True)
        self.add_composite_file("blastdb.pin", is_binary=True)
        self.add_composite_file("blastdb.psq", is_binary=True)
        self.add_composite_file("blastdb.freq", is_binary=True, optional=True)
        self.add_composite_file("blastdb.loo", is_binary=True, optional=True)
        self.add_composite_file("blastdb.psd", is_binary=True, optional=True)
        self.add_composite_file("blastdb.psi", is_binary=True, optional=True)
        self.add_composite_file("blastdb.rps", is_binary=True, optional=True)
        self.add_composite_file("blastdb.aux", is_binary=True, optional=True)


class LastDb(Data):
    """Class for LAST database files."""

    file_ext = "lastdb"
    composite_type = "basic"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "LAST database (multiple files)"
            dataset.blurb = "LAST database (multiple files)"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "LAST database (multiple files)"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("lastdb.bck", is_binary=True)
        self.add_composite_file("lastdb.des", description="Description file", is_binary=False)
        self.add_composite_file("lastdb.prj", description="Project resume file", is_binary=False)
        self.add_composite_file("lastdb.sds", is_binary=True)
        self.add_composite_file("lastdb.ssp", is_binary=True)
        self.add_composite_file("lastdb.suf", is_binary=True)
        self.add_composite_file("lastdb.tis", is_binary=True)


class BlastNucDb5(_BlastDb):
    """Class for nucleotide BLAST database files."""

    file_ext = "blastdbn5"
    composite_type = "basic"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("blastdb.nhr", is_binary=True)  # sequence headers
        self.add_composite_file("blastdb.nin", is_binary=True)  # index file
        self.add_composite_file("blastdb.nsq", is_binary=True)  # nucleotide sequences
        self.add_composite_file(
            "blastdb.nal", is_binary=False, optional=True
        )  # alias ( -gi_mask option of makeblastdb)
        self.add_composite_file(
            "blastdb.nhd", is_binary=True, optional=True
        )  # sorted sequence hash values ( -hash_index option of makeblastdb)
        self.add_composite_file(
            "blastdb.nhi", is_binary=True, optional=True
        )  # index of sequence hash values ( -hash_index option of makeblastdb)
        self.add_composite_file(
            "blastdb.nnd", is_binary=True, optional=True
        )  # sorted GI values ( -parse_seqids option of makeblastdb and gi present in the description lines)
        self.add_composite_file(
            "blastdb.nni", is_binary=True, optional=True
        )  # index of GI values ( -parse_seqids option of makeblastdb and gi present in the description lines)
        self.add_composite_file(
            "blastdb.nog", is_binary=True, optional=True
        )  # OID->GI lookup file ( -hash_index or -parse_seqids option of makeblastdb)
        self.add_composite_file(
            "blastdb.nsd", is_binary=True, optional=True
        )  # sorted sequence accession values ( -hash_index or -parse_seqids option of makeblastdb)
        self.add_composite_file(
            "blastdb.nsi", is_binary=True, optional=True
        )  # index of sequence accession values ( -hash_index or -parse_seqids option of makeblastdb)
        #        self.add_composite_file('blastdb.00.idx', is_binary=True, optional=True)  # first volume of the MegaBLAST index generated by makembindex
        # The previous line should be repeated for each index volume, with filename extensions like '.01.idx', '.02.idx', etc.
        self.add_composite_file(
            "blastdb.shd", is_binary=True, optional=True
        )  # MegaBLAST index superheader (-old_style_index false option of makembindex)


#        self.add_composite_file('blastdb.naa', is_binary=True, optional=True)  # index of a WriteDB column for e.g. mask data
#        self.add_composite_file('blastdb.nab', is_binary=True, optional=True)  # data of a WriteDB column
#        self.add_composite_file('blastdb.nac', is_binary=True, optional=True)  # multiple byte order for a WriteDB column
# The previous 3 lines should be repeated for each WriteDB column, with filename extensions like ('.nba', '.nbb', '.nbc'), ('.nca', '.ncb', '.ncc'), etc.


class BlastProtDb5(_BlastDb):
    """Class for protein BLAST database files."""

    file_ext = "blastdbp5"
    composite_type = "basic"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        # Component file comments are as in BlastNucDb except where noted
        self.add_composite_file("blastdb.phr", is_binary=True)
        self.add_composite_file("blastdb.pin", is_binary=True)
        self.add_composite_file("blastdb.psq", is_binary=True)  # protein sequences
        self.add_composite_file("blastdb.phd", is_binary=True, optional=True)
        self.add_composite_file("blastdb.phi", is_binary=True, optional=True)
        self.add_composite_file("blastdb.pnd", is_binary=True, optional=True)
        self.add_composite_file("blastdb.pni", is_binary=True, optional=True)
        self.add_composite_file("blastdb.pog", is_binary=True, optional=True)
        self.add_composite_file("blastdb.psd", is_binary=True, optional=True)
        self.add_composite_file("blastdb.psi", is_binary=True, optional=True)


#        self.add_composite_file('blastdb.paa', is_binary=True, optional=True)
#        self.add_composite_file('blastdb.pab', is_binary=True, optional=True)
#        self.add_composite_file('blastdb.pac', is_binary=True, optional=True)
# The last 3 lines should be repeated for each WriteDB column, with filename extensions like ('.pba', '.pbb', '.pbc'), ('.pca', '.pcb', '.pcc'), etc.


class BlastDomainDb5(_BlastDb):
    """Class for domain BLAST database files."""

    file_ext = "blastdbd5"
    composite_type = "basic"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("blastdb.phr", is_binary=True)
        self.add_composite_file("blastdb.pin", is_binary=True)
        self.add_composite_file("blastdb.psq", is_binary=True)
        self.add_composite_file("blastdb.freq", is_binary=True, optional=True)
        self.add_composite_file("blastdb.loo", is_binary=True, optional=True)
        self.add_composite_file("blastdb.psd", is_binary=True, optional=True)
        self.add_composite_file("blastdb.psi", is_binary=True, optional=True)
        self.add_composite_file("blastdb.rps", is_binary=True, optional=True)
        self.add_composite_file("blastdb.aux", is_binary=True, optional=True)
