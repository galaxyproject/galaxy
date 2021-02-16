"""
Flow analysis datatypes.
"""

import logging
import math

from galaxy.datatypes.binary import Binary
from . import data

log = logging.getLogger(__name__)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


class FCS(Binary):
    """Class describing an FCS binary file"""
    file_ext = "fcs"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary FCS file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary FCSfile (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """
        Checking if the file is in FCS format. Should read FCS2.0, FCS3.0
        and FCS3.1

        Based on flowcore:
        https://github.com/RGLab/flowCore/blob/27141b792ad65ae8bd0aeeef26e757c39cdaefe7/R/IO.R#L667

        Try to guess if the file is a fcs file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Accuri_C6_A01_H2O.fcs')
        >>> FCS().sniff(fname)
        True
        """
        try:
            with open(filename, 'rb') as f:
                # assume 1 byte = 1 char
                version = f.read(6).decode("utf8", errors="ignore")
                if version not in ["FCS2.0", "FCS3.0", "FCS3.1"]:
                    return False
                version = version.replace("FCS", "")
                tmp = f.read(4).decode("utf8", errors="ignore")
                if tmp != "    ":
                    return False
                coffs = []
                # we only need to check ioffs 2 to 5
                for _i in range(4):
                    coffs.append(f.read(8).decode("utf8", errors="ignore"))

            ioffs = [float(version)] + [int(x) for x in coffs]
            for ioff in ioffs:
                if ioff is None or math.isnan(ioff):
                    return False
        except Exception:
            return False

        return True

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'
