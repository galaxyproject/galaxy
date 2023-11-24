"""
Created on January. 05, 2018

@authors: Kenzo-Hugo Hillion and Fabien Mareuil, Institut Pasteur, Paris
@contacts: kehillio@pasteur.fr and fabien.mareuil@pasteur.fr
@project: galaxy
@githuborganization: C3BI
Phylip datatype sniffer
"""
from typing import TYPE_CHECKING

from galaxy import util
from galaxy.datatypes.data import (
    get_file_peek,
    Text,
)
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.util import nice_size
from .metadata import MetadataElement

if TYPE_CHECKING:
    from io import StringIO


@build_sniff_from_prefix
class Phylip(Text):
    """Phylip format stores a multiple sequence alignment"""

    edam_data = "data_0863"
    edam_format = "format_1997"
    file_ext = "phylip"

    MetadataElement(
        name="sequences", default=0, desc="Number of sequences", readonly=True, visible=False, optional=True, no_value=0
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of sequences and the number of data lines in dataset.
        """
        dataset.metadata.data_lines = self.count_data_lines(dataset)
        try:
            dataset.metadata.sequences = int(open(dataset.file_name).readline().split()[0])
        except Exception:
            raise Exception("Header does not correspond to PHYLIP header.")

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            if dataset.metadata.sequences:
                dataset.blurb = f"{util.commaify(str(dataset.metadata.sequences))} sequences"
            else:
                dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_strict_interleaved(self, nb_seq: int, seq_length: int, alignment_prefix: "StringIO") -> bool:
        found_seq_length = None
        for _ in range(nb_seq):
            line = alignment_prefix.readline()
            if not line:
                # Not enough lines, either the prefix is too short or this is not PHYLIP
                return False
            line = line.rstrip("\n")
            if len(line) < 11:
                # Sequence characters immediately follow the sequence ID.
                # They must start at the 11th character in the line, as the first 10 characters are reserved for the sequence ID
                return False
            seq = line[10:].replace(" ", "")
            this_seq_length = len(seq)
            if this_seq_length > seq_length:
                return False
            if found_seq_length is None:
                found_seq_length = this_seq_length
            elif this_seq_length != found_seq_length:
                # All sequence parts should have the same length
                return False
            # Fail if sequence is not ascii
            seq.encode("ascii")
            if any(str.isdigit(c) for c in seq):
                # Could tighten up further by requiring IUPAC strings chars
                return False
        # There may be more lines with the remaining parts of the sequences
        return True

    def sniff_strict_sequential(self, nb_seq: int, seq_length: int, alignment_prefix: "StringIO") -> bool:
        raise NotImplementedError

    def sniff_relaxed_interleaved(self, nb_seq: int, seq_length: int, alignment_prefix: "StringIO") -> bool:
        found_seq_length = None
        for _ in range(nb_seq):
            line = alignment_prefix.readline()
            if not line:
                # Not enough lines, either the prefix is too short or this is not PHYLIP
                return False
            line = line.rstrip("\n")
            # In the relaxed format the sequence id can have any length.
            # The id and sequence are separated by some whitespaces.
            seq = line.split(None, 1)[1].replace(" ", "")
            this_seq_length = len(seq)
            if this_seq_length > seq_length:
                return False
            if found_seq_length is None:
                found_seq_length = this_seq_length
            elif this_seq_length != found_seq_length:
                # All sequence parts should have the same length
                return False
            # Fail if sequence is not ascii
            seq.encode("ascii")
            if any(str.isdigit(c) for c in seq):
                # Could tighten up further by requiring IUPAC strings chars
                return False
        line = alignment_prefix.readline()
        if line.strip():
            # There should be a newline separating alignments.
            # If we got more content this is probably not a phylip file
            return False
        # There may be more lines with the remaining parts of the sequences
        return True

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        All Phylip files starts with the number of sequences so we can use this
        to count the following number of sequences in the first 'stack'

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test_strict_interleaved.phylip')
        >>> Phylip().sniff(fname)
        True
        >>> fname = get_test_fname('test_relaxed_interleaved.phylip')
        >>> Phylip().sniff(fname)
        True
        >>> fname = get_test_fname("not_a_phylip_file.tabular")
        >>> Phylip().sniff(fname)
        False
        """
        f = file_prefix.string_io()
        # Get number of sequences and sequence length from first line
        nb_seq, seq_length = (int(n) for n in f.readline().split())
        if nb_seq <= 0 or seq_length <= 0:
            return False
        file_pos = f.tell()
        try:
            if self.sniff_strict_interleaved(nb_seq, seq_length, f):
                return True
        except Exception:
            pass
        f.seek(file_pos)
        try:
            if self.sniff_strict_sequential(nb_seq, seq_length, f):
                return True
        except Exception:
            pass
        f.seek(file_pos)
        try:
            if self.sniff_relaxed_interleaved(nb_seq, seq_length, f):
                return True
        except Exception:
            pass
        return False
