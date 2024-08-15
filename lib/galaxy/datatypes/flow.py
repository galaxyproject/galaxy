"""
Flow analysis datatypes.
"""

import logging

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from . import data

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class FCS(Binary):
    """Class describing an FCS binary file"""

    file_ext = "fcs"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "Binary FCS file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return "Binary FCS file"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Checking if the file is in FCS format. Should read FCS2.0, FCS3.0
        and FCS3.1

        Based on flowcore:
        https://github.com/RGLab/flowCore/blob/27141b792ad65ae8bd0aeeef26e757c39cdaefe7/R/IO.R#L667
        """
        content = file_prefix.contents_header_bytes[:42].decode()
        version = content[:6]
        if version not in ["FCS2.0", "FCS3.0", "FCS3.1"]:
            return False
        if content[6:10] != "    ":
            return False
        # we only need to check ioffs 2 to 5
        int(content[10:42].replace(" ", ""))
        return True
