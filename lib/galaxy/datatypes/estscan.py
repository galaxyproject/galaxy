import logging
import re

from galaxy.datatypes.data import get_file_peek, Text
from galaxy.util import nice_size

log = logging.getLogger(__name__)

MAX_LINE_LEN = 500
MAX_LINES = 10000


class Smat(Text):
    file_ext = "smat"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "ESTScan scores matrices (%s)" % (nice_size(dataset.get_size()))

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name, is_multi_byte=is_multi_byte)
            dataset.blurb = "ESTScan scores matrices"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff(self, filename):
        """
        The use of ESTScan implies the creation of scores matrices which
        reflect the codons preferences in the studied organisms.  The
        ESTScan package includes scripts for generating these files.  The
        output of these scripts consists of the matrices, one for each
        isochor, and which look like this:

        FORMAT: hse_4is.conf CODING REGION 6 3 1 s C+G: 0 44
        -1 0 2 -2
        2 1 -8 0

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test_space.txt')
        >>> Smat().sniff(fname)
        False
        >>> fname = get_test_fname('test_tab.bed')
        >>> Smat().sniff(fname)
        False
        >>> fname = get_test_fname('1.smat')
        >>> Smat().sniff(fname)
        True
        """
        line_no = 0
        with open(filename, "r") as fh:
            line_no += 1
            if line_no > MAX_LINES:
                return rval(True, fh)
            line = fh.readline(MAX_LINE_LEN)
            if line_no == 1 and not line.startswith('FORMAT'):
                # The first line is always the start of a format section.
                return rval(False, fh)
            if not line.startswith('FORMAT'):
                if line.find('\t') >= 0:
                    # Smat files are not tabular.
                    return rval(False, fh)
                items = line.split()
                if len(items) != 4:
                    return rval(False, fh)
                for item in items:
                    # Make sure each item is an integer.
                    if re.match(r"[-+]?\d+$", item) is None:
                        return rval(False, fh)
        return rval(True, fh)


def rval(rval, fh):
    fh.close()
    return rval
