# -*- coding: utf-8 -*-
######################################################################
#                  Copyright (c) 2016 Northrop Grumman.
#                          All rights reserved.
######################################################################

"""
MetaCyto analysis datatypes.
"""

import logging

from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.data import get_file_peek, Text
from galaxy.datatypes.metadata import MetadataElement
from galaxy.util import nice_size, string_as_bool
from . import data

log = logging.getLogger(__name__)


class mStats(Tabular):
    """Class describing the table of cluster statistics output from MetaCyto"""
    file_ext = "metacyto_stats.txt"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "MetaCyto Cluster Stats file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "MetaCyto Cluster Stats file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file headings"""
        with open(filename, "r") as f:
            #last one == fraction
            headers = f.readline().strip().split("\t")
            if headers[-1] != "fraction":
                return False
            hdrs = ["fcs_files","cluster_id","label","fcs_names"]
            for h in hdrs:
                if h not in headers:
                    return False
            return True

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'


class mClrList(Tabular):
    """Class describing a list of cluster definitions used for MetaCyto analysis"""
    file_ext = "metacyto_clr.txt"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "MetaCyto Cluster Definitions List file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "MetaCyto Cluster Definitions List file (%s)" % (data.nice_size(dataset.get_size()))

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'


class mSummary(Tabular):
    """Class describing the summary table output by MetaCyto after FCS preprocessing"""
    file_ext = "metacyto_summary.txt"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "MetaCyto Preprocessing Summary file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "MetaCyto Preprocessing Summary file (%s)" % (data.nice_size(dataset.get_size()))

    def sniff(self, filename):
        """Quick test on file formatting"""
        with open(filename, "r") as f:
            headings = f.readline().strip().split("\t")
            hdgs = ["study_id", "antibodies", "filenames"]
            for h in hdgs:
                if h not in headings:
                    return False
            return True

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/tab-separated-values'
