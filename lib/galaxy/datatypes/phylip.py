"""
Created on January. 05, 2018

@authors: Kenzo-Hugo Hillion and Fabien Mareuil, Institut Pasteur, Paris
@contacts: kehillio@pasteur.fr and fabien.mareuil@pasteur.fr
@project: galaxy
@githuborganization: C3BI
Phylip datatype sniffer
"""

from galaxy import util
from galaxy.datatypes.data import Text, get_file_peek
from metadata import MetadataElement
import os

class Phylip(Text):
    """Phylip format stores a multiple sequence alignment"""
    edam_data = "data_0863"
    edam_format = "format_1997"
    file_ext = "phylip"

    """Add metadata elements"""
    MetadataElement(name="sequences", default=0, desc="Number of sequences", readonly=True,
                    visible=False, optional=True, no_value=0)

    def set_meta(self, dataset, **kwd):
        """
        Set the number of sequences and the number of data lines in dataset.
        """
        data_lines = 0
        sequences = 0
        for line in open(dataset.file_name):
            line = line.strip()
            if data_lines == 0:
                sequences = line.split()[0]
            data_lines += 1
        dataset.metadata.data_lines = data_lines
        dataset.metadata.sequences = sequences

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name, is_multi_byte=is_multi_byte)
            if dataset.metadata.sequences:
                dataset.blurb = "%s sequences" % util.commaify(str(dataset.metadata.sequences))
            else:
                dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def __init__(self, **kwd):
        """Initialize datatype"""
        Text.__init__(self, **kwd)

    def sniff(self, filename):
        """
        All Phylip files starts with the number of sequences so we can use this
        to count the following number of sequences in the first 'stack'
        """
        with open(filename, "r") as f:
            # Get number of sequence from first line
            nb_seq = int(f.readline().split()[0])
            # counts number of sequence from first stack
            count = 0
            for line in f:
                if not line.split():
                    break
                count += 1

        if count == nb_seq:
            return True
        else:
            return False