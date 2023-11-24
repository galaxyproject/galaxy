"""
Triple format classes
"""
import logging
import re

from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from . import (
    binary,
    data,
    text,
    xml,
)

log = logging.getLogger(__name__)

TURTLE_PREFIX_PATTERN = re.compile(r"@prefix\s+[^:]*:\s+<[^>]*>\s\.")
TURTLE_BASE_PATTERN = re.compile(r"@base\s+<[^>]*>\s\.")


class Triples(data.Data):
    """
    The abstract base class for the file format that can contain triples
    """

    edam_data = "data_0582"
    edam_format = "format_2376"
    file_ext = "triples"

    def sniff(self, filename: str) -> bool:
        """
        Returns false and the user must manually set.
        """
        return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "Triple data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class NTriples(data.Text, Triples):
    """
    The N-Triples triple data format
    """

    edam_format = "format_3256"
    file_ext = "nt"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        # <http://example.org/dir/relfile> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/type> .
        if re.compile(r"<[^>]*>\s<[^>]*>\s<[^>]*>\s\.").search(file_prefix.contents_header):
            return True
        return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "N-Triples triple data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class N3(data.Text, Triples):
    """
    The N3 triple data format
    """

    edam_format = "format_3257"
    file_ext = "n3"

    def sniff(self, filename: str) -> bool:
        """
        Returns false and the user must manually set.
        """
        return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "Notation-3 Triple data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class Turtle(data.Text, Triples):
    """
    The Turtle triple data format
    """

    edam_format = "format_3255"
    file_ext = "ttl"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        # @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        if file_prefix.search(TURTLE_PREFIX_PATTERN):
            return True

        if file_prefix.search(TURTLE_BASE_PATTERN):
            return True
        return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "Turtle triple data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


# TODO: we might want to look at rdflib or a similar, larger lib/egg
@build_sniff_from_prefix
class Rdf(xml.GenericXml, Triples):
    """
    Resource Description Framework format (http://www.w3.org/RDF/).
    """

    edam_format = "format_3261"
    file_ext = "rdf"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        # <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" ...
        match = re.compile(r'xmlns:([^=]*)="http://www.w3.org/1999/02/22-rdf-syntax-ns#"').search(
            file_prefix.contents_header
        )
        if match and (f"{match.group(1)}:RDF") in file_prefix.contents_header:
            return True
        return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "RDF/XML triple data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class Jsonld(text.Json, Triples):
    """
    The JSON-LD data format
    """

    # format not defined in edam so we use the json format number
    edam_format = "format_3464"
    file_ext = "jsonld"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        if self._looks_like_json(file_prefix):
            if '"@id"' in file_prefix.contents_header or '"@context"' in file_prefix.contents_header:
                return True
        return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "JSON-LD triple data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class HDT(binary.Binary, Triples):
    """
    The HDT triple data format
    """

    edam_format = "format_2376"
    file_ext = "hdt"

    def sniff(self, filename: str) -> bool:
        with open(filename, "rb") as f:
            if f.read(4) == b"$HDT":
                return True
        return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "HDT triple data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"
