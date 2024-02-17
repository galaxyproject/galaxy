"""Composite datatype for the HDF5SummarizedExperiment R data object.

This datatype was created for use with the iSEE interactive tool.
"""

from typing import Optional

from galaxy.datatypes.data import Data
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import (
    HasExtraFilesAndMetadata,
    HasMetadata,
)


class HDF5SummarizedExperiment(Data):
    """Composite datatype to represent HDF5SummarizedExperiment objects.

    A lightweight shell file `se.rds` is read into memory by R, and provides an
    interface to the much larger `assays.h5` files which contains the
    experiment data.

    Within R, the HDF5SummarizedExperiment object is conventionally referenced
    by the parent directory name of these two files.
    In Galaxy tool commands, the parent directory can be accessed through
    `param_name.extra_files_path`.
    """

    MetadataElement(
        name="base_name",
        desc="SummarisedExperiment object name",
        default="HDF5 SE object",
        readonly=True,
        set_in_upload=True,
    )

    file_ext = "rdata.se"
    composite_type = "auto_primary_file"
    allow_datatype_change = False

    def __init__(self, **kwd):
        """Construct object from input files."""
        Data.__init__(self, **kwd)
        self.add_composite_file(
            "se.rds",
            is_binary=True,
            description="Summarized experiment RDS object",
        )
        self.add_composite_file(
            "assays.h5",
            is_binary=True,
            description="Summarized experiment data array",
        )

    def init_meta(self, dataset: HasMetadata, copy_from: Optional[HasMetadata] = None) -> None:
        """Override parent init metadata."""
        Data.init_meta(self, dataset, copy_from=copy_from)

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        """Generate primary file to represent dataset."""
        return f"""
              <html>
                <head>
                  <title> Files for Composite Dataset ({self.file_ext})</title>
                </head>
                <p/>
                  This composite dataset is composed of the following files:
                </p>
                <ul>
                  <li><a href="se.rds">se.rds</a>
                  <li><a href="array.h5">array.h5</a>
                </ul>
              </html>
              """

    def sniff(self, filename: str) -> bool:
        """
        Returns false and the user must manually set.
        """
        return False

    def get_mime(self) -> str:
        """Return the mime type of the datatype."""
        return "text/html"
