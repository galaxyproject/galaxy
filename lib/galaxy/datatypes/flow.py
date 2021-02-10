"""
Flow analysis datatypes.
"""

import logging
import math

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.tabular import Tabular
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
                for _i in range(6):
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


class FlowText(Tabular):
    """Class describing an Flow Text file"""
    file_ext = "flowtext"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Text Flow file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Text Flow file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values
        Try to guess if the file is a fcs file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('flowtext_scatterplot_input.flowtext')
        >>> FlowText().sniff(fname)
        True
        """
        with open(filename, "r") as f:
            f.readline()
            values = f.readline().strip().split("\t")
            for vals in values:
                if not is_number(vals):
                    return False
            return True


class FlowClustered(Tabular):
    """Class describing a Flow Text that has been clustered through FLOCK"""
    file_ext = "flowclr"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Text Flow Clustered file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Flow Text Clustered file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on headers and values
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('flowclr_sample_input2.flowclr')
        >>> FlowClustered().sniff(fname)
        True
        """
        with open(filename, "r") as f:
            population = f.readline().strip().split("\t")[-1]
            if population != "Population":
                return False
            values = f.readline().strip().split("\t")
            for vals in values:
                if not is_number(vals):
                    return False
            return True


class FlowMFI(Tabular):
    """Class describing a Flow MFI file"""
    file_ext = "flowmfi"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "MFI Flow file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "MFI Flow file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('generate_mfi.flowmfi')
        >>> FlowMFI().sniff(fname)
        True
        """
        with open(filename, "r") as f:
            population = f.readline().strip().split("\t")[0]
            if population != "Population":
                return False
            values = f.readline().strip().split("\t")
            for vals in values:
                if not is_number(vals):
                    return False
            return True


class FlowStats1(Tabular):
    """Class describing a Flow Stats file"""
    file_ext = "flowstat1"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Flow Stats1 file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Flow Stats1 file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values"""
        with open(filename, "r") as f:
            first_header = f.readline().strip().split("\t")[0]
            if first_header != "FileID":
                return False
            return True


class FlowStats2(Tabular):
    """Class describing a Flow Stats file"""
    file_ext = "flowstat2"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Flow Stats2 file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Flow Stats2 file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values"""
        with open(filename, "r") as f:
            smp_name = f.readline().strip().split("\t")[-1]
            if smp_name != "SampleName":
                return False
            return True


class FlowStats3(Tabular):
    """Class describing a Flow Stats file"""
    file_ext = "flowstat3"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Flow Stats3 file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Flow Stats3 file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values"""
        with open(filename, "r") as f:
            last_col = f.readline().strip().split("\t")[-1]
            if last_col != "Percentage_stdev":
                return False
            values = f.readline().strip().split("\t")
            for vals in values:
                if not is_number(vals):
                    return False
            return True


class FlowScore(Tabular):
    """Class describing a Flow Score file"""
    file_ext = "flowscore"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Flow Score file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Flow Score file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values"""
        with open(filename, "r") as f:
            population = f.readline().strip().split("\t")[0]
            if population != "Population_ID":
                return False
            values = f.readline().strip().split("\t")
            for vals in values:
                if not is_number(vals):
                    return False
            return True
