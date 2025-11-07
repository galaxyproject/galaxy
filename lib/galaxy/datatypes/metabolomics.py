"""
Metabolomics Datatypes
"""

import logging

from typing import Optional

from galaxy.datatypes import data
from galaxy.datatypes.proteomics import MzTab
from galaxy.datatypes.protocols import (
    DatasetProtocol,
    DatasetHasHidProtocol
)

log = logging.getLogger(__name__)


class MzTabM(MzTab):
    """
    mzTab-M is a lightweight, tab-delimited file format for reporting mass spectrometry-based metabolomics results
    https://github.com/HUPO-PSI/mzTab-M

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.metabolomics.mztab')
    >>> MzTabM().sniff(fname)
    True
    >>> fname = get_test_fname('test.mztab')
    >>> MzTabM().sniff(fname)
    False
    """

    edam_data = "data_4058"
    file_ext = "metabolomics.mztab"
    # section names (except MTD)
    _sections = ["SMH", "SML", "SFH", "SMF", "SEH", "SME", "COM"]
    _version_re = r"(2)(\.[0-9]+)?(\.[0-9]+)?-M$"
    # mandatory metadata fields and list of allowed entries (in lower case)
    # (or None if everything is allowed)
    _man_mtd = {"mzTab-ID": None}

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def display_data(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        **kwd
    ):
        if to_ext == self.file_ext:
            to_ext = "mztab"
        return super().display_data(trans, dataset, preview=preview, filename=filename, to_ext=to_ext, **kwd)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "mzTab-M Format"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"
