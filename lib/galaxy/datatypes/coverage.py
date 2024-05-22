"""
Coverage datatypes

"""

import logging

from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.tabular import Tabular

log = logging.getLogger(__name__)


class LastzCoverage(Tabular):
    file_ext = "coverage"

    MetadataElement(name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter)
    MetadataElement(name="positionCol", default=2, desc="Position column", param=metadata.ColumnParameter)
    MetadataElement(
        name="forwardCol", default=3, desc="Forward or aggregate read column", param=metadata.ColumnParameter
    )
    MetadataElement(
        name="reverseCol",
        desc="Optional reverse read column",
        param=metadata.ColumnParameter,
        optional=True,
        no_value=0,
    )
    MetadataElement(name="columns", default=3, desc="Number of columns", readonly=True, visible=False)
