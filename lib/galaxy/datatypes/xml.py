"""
XML format classes
"""

import logging
import re
from typing import List

from galaxy import util
from galaxy.datatypes.dataproviders.dataset import DatasetDataProvider
from galaxy.datatypes.dataproviders.hierarchy import XMLDataProvider
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    disable_parent_class_sniffing,
    FilePrefix,
)
from . import (
    data,
    dataproviders,
)

log = logging.getLogger(__name__)

OWL_MARKER = re.compile(r"\<owl:")
SBML_MARKER = re.compile(r"\<sbml")


@dataproviders.decorators.has_dataproviders
@build_sniff_from_prefix
class GenericXml(data.Text):
    """Base format class for any XML file."""

    edam_format = "format_2332"
    file_ext = "xml"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "XML data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def _has_root_element_in_prefix(self, file_prefix: FilePrefix, root: str) -> bool:
        for line in file_prefix.line_iterator():
            if not line.startswith("<?"):
                break
        # pattern match <root or <ns:root for any ns string
        pattern = rf"^<(\w*:)?{root}"
        return re.match(pattern, line) is not None

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is XML or not

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'megablast_xml_parser_test1.blastxml' )
        >>> GenericXml().sniff( fname )
        True
        >>> fname = get_test_fname( 'interval.interval' )
        >>> GenericXml().sniff( fname )
        False
        """
        return file_prefix.startswith("<?xml ")

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """Merging multiple XML files is non-trivial and must be done in subclasses."""
        if len(split_files) > 1:
            raise NotImplementedError(
                "Merging multiple XML files is non-trivial and must be implemented for each XML type"
            )
        # For one file only, use base class method (move/copy)
        data.Text.merge(split_files, output_file)

    @dataproviders.decorators.dataprovider_factory("xml", XMLDataProvider.settings)
    def xml_dataprovider(self, dataset: DatasetProtocol, **settings) -> XMLDataProvider:
        dataset_source = DatasetDataProvider(dataset)
        return XMLDataProvider(dataset_source, **settings)


@disable_parent_class_sniffing
class MEMEXml(GenericXml):
    """MEME XML Output data"""

    file_ext = "memexml"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "MEME XML data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@disable_parent_class_sniffing
class CisML(GenericXml):
    """CisML XML data"""  # see: http://www.ncbi.nlm.nih.gov/pubmed/15001475

    file_ext = "cisml"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "CisML data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class Dzi(GenericXml):
    """
    Deep zoom image format, see
    https://github.com/openseadragon/openseadragon/wiki/The-DZI-File-Format
    """

    # General elements.
    MetadataElement(
        name="base_name", desc="Base name for this dataset", default="DeepZoomImage", readonly=True, set_in_upload=True
    )
    MetadataElement(name="format", desc="File format of the tiles", default=None, readonly=True, visible=True)
    MetadataElement(name="tile_size", desc="Size of tiles", default=None, readonly=True, visible=True)
    # Collection elements.
    MetadataElement(
        name="max_level", desc="Max pyramid level", default=None, readonly=True, optional=True, visible=True
    )
    MetadataElement(name="quality", desc="Quality", default=None, readonly=True, optional=True, visible=True)
    # Image elements.
    MetadataElement(name="height", desc="Size height", default=None, readonly=True, optional=True, visible=True)
    MetadataElement(
        name="overlap",
        desc="Overlap of all four sides of tiles",
        default=None,
        readonly=True,
        optional=True,
        visible=True,
    )
    MetadataElement(name="width", desc="Size width", default=None, readonly=True, optional=True, visible=True)

    file_ext = "dzi"

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        tree = util.parse_xml(dataset.get_file_name())
        root = tree.getroot()
        dataset.metadata.format = root.get("Format")
        dataset.metadata.tile_size = root.get("TileSize")
        # DeepZoom image files can include
        # xml namespace attributes.
        if root.tag.find("Collection") >= 0:
            dataset.metadata.max_level = root.get("MaxLevel")
            dataset.metadata.quality = root.get("Quality")
        elif root.tag.find("Image") >= 0:
            dataset.metadata.overlap = root.get("Overlap")
        for elem in root:
            if elem.tag.find("Size") >= 0:
                dataset.metadata.width = elem.get("Width")
                dataset.metadata.height = elem.get("Height")

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "Deep Zoom Image"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Checking for keyword - 'Collection' or 'Image' in the first 200 lines.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('1.dzi')
        >>> Dzi().sniff(fname)
        True
        >>> fname = get_test_fname('megablast_xml_parser_test1.blastxml')
        >>> Dzi().sniff(fname)
        False
        """
        for line in file_prefix.line_iterator():
            line = line.lower()
            if line.find("<collection") >= 0 or line.find("<image") >= 0:
                return True
        return False


class Phyloxml(GenericXml):
    """Format for defining phyloxml data http://www.phyloxml.org/"""

    edam_data = "data_0872"
    edam_format = "format_3159"
    file_ext = "phyloxml"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "Phyloxml data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """ "Checking for keyword - 'phyloxml' always in lowercase in the first few lines.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( '1.phyloxml' )
        >>> Phyloxml().sniff( fname )
        True
        >>> fname = get_test_fname( 'interval.interval' )
        >>> Phyloxml().sniff( fname )
        False
        >>> fname = get_test_fname( 'megablast_xml_parser_test1.blastxml' )
        >>> Phyloxml().sniff( fname )
        False
        """
        return self._has_root_element_in_prefix(file_prefix, "phyloxml")


class Owl(GenericXml):
    """
    Web Ontology Language OWL format description
    http://www.w3.org/TR/owl-ref/
    """

    edam_format = "format_3262"
    file_ext = "owl"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "Web Ontology Language OWL"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Checking for keyword - '<owl' in the first 200 lines.
        """
        return file_prefix.search(OWL_MARKER)


class Sbml(GenericXml):
    """
    System Biology Markup Language
    http://sbml.org
    """

    file_ext = "sbml"
    edam_data = "data_2024"
    edam_format = "format_2585"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "System Biology Markup Language SBML"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Checking for keyword - '<sbml' in the first 200 lines.
        """
        return file_prefix.search(SBML_MARKER)
