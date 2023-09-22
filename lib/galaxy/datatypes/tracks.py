"""
Datatype classes for tracks/track views within galaxy.
"""
import logging

from galaxy.datatypes.protocols import (
    DatasetProtocol,
    HasExtraFilesAndMetadata,
)
from galaxy.datatypes.text import Html
from . import binary

log = logging.getLogger(__name__)


# GeneTrack is no longer supported but leaving the datatype since
# files of this type may still exist
class GeneTrack(binary.Binary):
    edam_data = "data_3002"
    edam_format = "format_2919"
    file_ext = "genetrack"


class UCSCTrackHub(Html):
    """
    Datatype for UCSC TrackHub
    """

    file_ext = "trackhub"
    composite_type = "auto_primary_file"

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        rval = [
            "<html><head><title>Files for Composite Dataset (%s)</title></head><p/>\
            This composite dataset is composed of the following files:<p/><ul>"
            % (self.file_ext)
        ]
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            opt_text = ""
            if composite_file.optional:
                opt_text = " (optional)"
            rval.append(f'<li><a href="{composite_name}">{composite_name}</a>{opt_text}')
        rval.append("</ul></html>")
        return "\n".join(rval)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "Track Hub structure: Visualization in UCSC Track Hub"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return "Track Hub structure: Visualization in UCSC Track Hub"

    def sniff(self, filename: str) -> bool:
        return False
