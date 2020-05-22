# -*- coding: utf-8 -*-
######################################################################
#                  Copyright (c) 2016 Northrop Grumman.
#                          All rights reserved.
######################################################################

"""
Flow analysis datatypes.
"""

import gzip
import json
import logging
import os
import sys
import re
import subprocess
import tempfile

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.data import get_file_peek, Text
from galaxy.datatypes.metadata import MetadataElement
from galaxy.util import nice_size, string_as_bool
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
        except:
            return "Binary FCSfile (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """
        Checking if the file is in FCS format. Should read FCS2.0, FCS3.0
        and FCS3.1

        For this to work, need to have install checkFCS.R via bioconda
        conda install ig-checkflowtypes
        """
        try:
            rscript = 'checkFCS.R'
            fcs_check = subprocess.check_output([rscript, filename])
            if re.search('TRUE', str(fcs_check)):
                return True
            else:
                return False
        except:
            False

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'


Binary.register_sniffable_binary_format("fcs", "fcs", FCS)


class FlowFrame( Binary ):
    """R Object containing flowFrame saved with saveRDS"""
    file_ext = 'flowframe'

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary RDS flowFrame file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Binary RDS flowFrame (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """
        Checking if the file is a flowFrame R object.

        For this to work, need to have install checkFlowframe.R via bioconda
        conda install ig-checkflowtypes
        """
        try:
            rscript = 'checkFlowframe.R'
            ff_check = subprocess.check_output([rscript, filename])
            if re.search('TRUE', str(ff_check)):
                return True
            else:
                return False
        except:
            False

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'


Binary.register_sniffable_binary_format('flowframe', 'flowframe', FlowFrame)


class FlowSOM( Binary ):
    """R Object containing fSOM saved with saveRDS"""
    file_ext = 'fsom'

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary RDS fsom file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Binary RDS fsom (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """
        Checking if the file is a FlowSOM R object.

        For this to work, need to have install checkFlowSOM.R via bioconda
        conda install ig-checkflowtypes
        """
        try:
            rscript = 'checkFlowSOM.R'
            fcs_check = subprocess.check_output([rscript, filename])
            if re.search('TRUE', str(fcs_check)):
                return True
            else:
                return False
        except:
            False

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'


Binary.register_sniffable_binary_format('fsom', 'fsom', FlowSOM)


class FlowSet( Binary ):
    """R Object containing flowSet saved with saveRDS"""
    file_ext = 'flowset'

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary RDS flowSet file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Binary RDS flowSet (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """
        Checking if the file is a flowSet R object.

        For this to work, need to have install checkFlowSet.R via bioconda
        conda install ig-checkflowtypes
        """
        try:
            rscript = 'checkFlowSet.R'
            fcs_check = subprocess.check_output([rscript, filename])
            if re.search('TRUE', str(fcs_check)):
                return True
            else:
                return False
        except:
            False

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'


Binary.register_sniffable_binary_format('flowset', 'flowset', FlowSet)


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
        except:
            return "Text Flow file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values"""
        with open(filename, "r") as f:
            f.readline()
            values = f.readline().strip().split("\t")
            for vals in values:
                if not is_number(vals):
                    return False
            return True

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'


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
        except:
            return "Flow Text Clustered file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on headers and values"""
        with open(filename, "r") as f:
            population = f.readline().strip().split("\t")[-1]
            if population != "Population":
                return False
            values = f.readline().strip().split("\t")
            for vals in values:
                if not is_number(vals):
                    return False
            return True

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'


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
        except:
            return "MFI Flow file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values"""
        with open(filename, "r") as f:
            population = f.readline().strip().split("\t")[0]
            if population != "Population":
                return False
            values = f.readline().strip().split("\t")
            for vals in values:
                if not is_number(vals):
                    return False
            return True

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'


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
        except:
            return "Flow Stats1 file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values"""
        with open(filename, "r") as f:
            first_header = f.readline().strip().split("\t")[0]
            if first_header != "FileID":
                return False
            return True

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'


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
        except:
            return "Flow Stats2 file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting and values"""
        with open(filename, "r") as f:
            smp_name = f.readline().strip().split("\t")[-1]
            if smp_name != "SampleName":
                return False
            return True

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'


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
        except:
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

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'


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
        except:
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

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'
