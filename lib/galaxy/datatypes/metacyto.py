"""
MetaCyto analysis datatypes.
"""

import logging

from galaxy.datatypes.sniff import FilePrefix
from galaxy.datatypes.tabular import Tabular

log = logging.getLogger(__name__)


class mStats(Tabular):
    """Class describing the table of cluster statistics output from MetaCyto"""

    file_ext = "metacyto_stats.txt"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Quick test on file headings"""
        if file_prefix.startswith("fcs_files\tcluster_id\tlabel\tfcs_names"):
            header_line = file_prefix.string_io().readline()
            if header_line.strip().split("\t")[-1] == "fraction":
                return True
            elif file_prefix.truncated and file_prefix.string_io().read() == header_line:
                return True
        return False


class mSummary(Tabular):
    """Class describing the summary table output by MetaCyto after FCS preprocessing"""

    file_ext = "metacyto_summary.txt"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        return file_prefix.startswith("study_id\tantibodies\tfilenames")
