"""
X-ray Photoelectron Spectroscopy (XPS) Datatypes

Datatypes for surface analysis data produced by X-ray photoelectron
spectroscopy (XPS, also known as ESCA). Two related formats are provided:

* :class:`Vamas` - the ISO 14976 VAMAS standard plain-text format, the
  open interchange format for surface analysis data (XPS, AES, ISS, ...).
  See https://www.iso.org/standard/25919.html (ISO 14976).
* :class:`XpsTabular` - a tabular export of an XPS spectrum (binding energy
  vs. intensity, optionally with kinetic energy and counts), as produced by
  many instrument software packages and tools such as CasaXPS or Galaxies
  processing tools when exporting a single region/scan to text.
"""

import logging
from typing import (
    IO,
    Optional,
)

from galaxy.datatypes import data
from galaxy.datatypes.data import Text
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.tabular import Tabular

log = logging.getLogger(__name__)


# Surface analysis techniques defined in ISO 14976 (VAMAS).
# The technique keyword is the line that identifies the type of measurement;
# XPS is the one we are interested in, but a VAMAS file may legitimately
# carry any of these values.
_VAMAS_TECHNIQUES = {
    "AES",
    "AES-DEPTH",
    "EDX",
    "FABMS",
    "FABMS-EM",
    "ISS",
    "MALDI",
    "MAPS",
    "RBS",
    "SIMS",
    "SIMS-DEPTH",
    "SNMS",
    "SNMS-DEPTH",
    "XPS",
    "XPS-DEPTH",
    "XPS-MAPPING",
    "XPS-AREA",
}


@build_sniff_from_prefix
class Vamas(Text):
    """
    ISO 14976 VAMAS surface analysis file (XPS).

    The VAMAS standard is the open, vendor-neutral interchange format for
    surface analysis data. The file is plain text and is organised as a
    sequence of blocks; the first block is the *experiment* header whose
    fifth non-empty line is the technique keyword (``XPS`` for X-ray
    photoelectron spectroscopy).

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.vamas')
    >>> Vamas().sniff(fname)
    True
    >>> fname = get_test_fname('test.xps.tsv')
    >>> Vamas().sniff(fname)
    False
    """

    edam_data = "data_2536"
    file_ext = "vamas"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "VAMAS (ISO 14976) surface analysis data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determine whether the file is a VAMAS (ISO 14976) XPS file.

        The sniffer looks for the characteristic VAMAS header: a first line
        that identifies the format (commonly starting with ``VAMAS`` or a
        specimen comment) followed, within the first handful of header
        lines, by a technique keyword from the ISO 14976 list (``XPS``,
        ``XPS-DEPTH``, ...).
        """
        header_lines: list[str] = []
        for line in file_prefix.line_iterator():
            line = line.strip()
            if not line:
                continue
            header_lines.append(line)
            if len(header_lines) >= 8:
                break
        if len(header_lines) < 5:
            return False
        # The first line is the format/specimen comment; many writers start
        # it with the literal token "VAMAS" but the standard only requires a
        # (possibly empty) comment, so we do not mandate it.
        first = header_lines[0]
        looks_like_vamas = first.startswith("VAMAS") or "VAMAS" in first.upper()
        # The technique keyword is the 5th line of the experiment header
        # per ISO 14976, but real-world files are not always strict. Accept
        # any of the header lines being a known technique keyword.
        technique_found = any(line in _VAMAS_TECHNIQUES for line in header_lines)
        return looks_like_vamas and technique_found


@build_sniff_from_prefix
class XpsTabular(Tabular):
    """
    Tabular export of an XPS spectrum.

    A two- or three-column, tab-separated table of an XPS region scan as
    exported by instrument software or processing tools. The first column is
    the binding energy (in eV, decreasing), followed by intensity (counts or
    counts-per-second). An optional third column may hold kinetic energy.

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.xps.tsv')
    >>> XpsTabular().sniff(fname)
    True
    >>> fname = get_test_fname('test.vamas')
    >>> XpsTabular().sniff(fname)
    False
    """

    edam_data = "data_2536"
    file_ext = "xps.tsv"
    comment_lines = 0

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.column_names = ["Binding Energy (eV)", "Intensity"]

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formatted html of peek."""
        return self.make_html_table(dataset, column_names=self.column_names)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        data_lines = 0
        ncols = 0
        column_names = self.column_names
        if dataset.has_data():
            with open(dataset.get_file_name()) as fh:
                for idx, line in enumerate(fh):
                    line = line.rstrip("\r\n")
                    if not line or line.startswith("#"):
                        continue
                    fields = line.split("\t")
                    if idx == 0 and not _is_float(fields[0]):
                        # treat as header
                        column_names = [c.strip() for c in fields]
                        continue
                    data_lines += 1
                    ncols = max(ncols, len(fields))
        dataset.metadata.data_lines = data_lines
        dataset.metadata.comment_lines = 0
        dataset.metadata.columns = ncols
        dataset.metadata.column_names = column_names
        dataset.metadata.column_types = ["float"] * ncols
        dataset.metadata.delimiter = "\t"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determine whether the file is a tabular XPS spectrum export.

        We require a header row whose first column names a binding-energy
        axis (case-insensitive, recognising common spellings such as
        "Binding Energy", "BE", "BE (eV)") followed by at least one data
        row of two or more numeric columns.
        """
        fh: IO = file_prefix.string_io()
        header = fh.readline()
        if not header:
            return False
        fields = [c.strip().lower() for c in header.rstrip("\r\n").split("\t")]
        if len(fields) < 2:
            return False
        first_col = fields[0]
        if not _is_be_label(first_col):
            return False
        # require at least one numeric data row
        for line in fh:
            line = line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            cells = line.split("\t")
            if len(cells) < 2 or not _is_float(cells[0]) or not _is_float(cells[1]):
                return False
            return True
        return False


def _is_float(value: object) -> bool:
    try:
        float(value)  # type: ignore[arg-type]
        return True
    except (TypeError, ValueError):
        return False


def _is_be_label(label: str) -> bool:
    label = label.strip().lower()
    if not label:
        return False
    # Recognise "binding energy", "be", "be (ev)", "binding energy (ev)" ...
    return label.startswith("binding energy") or label in {"be", "be (ev)", "binding_energy"}
