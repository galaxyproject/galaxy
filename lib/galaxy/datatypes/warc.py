"""
Datatypes for the Web ARChive (WARC) format.

The WARC format stores archived web content together with the metadata that
describes how it was captured. See the format specification at
https://iipc.github.io/warc-specifications/ for details.

WARC files are frequently distributed gzip-compressed (``.warc.gz``), where
each record is written as a separate gzip member. Such files are kept
compressed on upload: decompressing them would change the per-record byte
offsets that tools such as ``warcio index`` report, and the records carry
exact ``Content-Length`` byte counts that must not be altered by line-ending
normalisation.
"""

from galaxy.datatypes.data import Text
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)


@build_sniff_from_prefix
class Warc(Text):
    """
    Uncompressed Web ARChive (WARC) file.

    Every WARC record begins with the version signature ``WARC/`` followed by
    the version number (for example ``WARC/1.0``).
    """

    file_ext = "warc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Every WARC record starts with the version signature ``WARC/``.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> Warc().sniff(get_test_fname('example.warc'))
        True
        >>> Warc().sniff(get_test_fname('Si.cif'))
        False
        """
        return file_prefix.startswith("WARC/")


@build_sniff_from_prefix
class WarcGz(Warc):
    """
    gzip-compressed Web ARChive (WARC) file.

    The datatype is kept compressed on upload (``compressed = True``) so that
    record byte offsets and ``Content-Length`` values remain valid. The
    inherited sniffer matches against the decompressed content.

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> WarcGz().sniff(get_test_fname('example.warc.gz'))
    True
    """

    file_ext = "warc.gz"
    compressed = True
    compressed_format = "gzip"
