"""
X-ray Photoelectron Spectroscopy (XPS) Datatypes

Datatypes for surface analysis data produced by X-ray photoelectron
spectroscopy (XPS, also known as ESCA). Three related formats are provided:

* :class:`Vamas` - the ISO 14976 VAMAS standard plain-text format, the
  open interchange format for surface analysis data (XPS, AES, ISS, ...).
  See https://www.iso.org/standard/25919.html (ISO 14976).
* :class:`XpsTabular` - a tabular export of an XPS spectrum (binding energy
  vs. intensity, optionally with kinetic energy and counts), as produced by
  many instrument software packages and tools such as CasaXPS or Galaxies
  processing tools when exporting a single region/scan to text.
* :class:`NXxps` - a NeXus HDF5 file conforming to the ``NXxps`` application
  definition (which extends ``NXmpes``), the recommended HDF5-based format
  for XPS data exchange.
  See https://manual.nexusformat.org/classes/applications/NXxps.html
"""

import logging
from typing import (
    IO,
    Optional,
)

from galaxy.datatypes import data
from galaxy.datatypes.binary import H5
from galaxy.datatypes.data import Text
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.tabular import Tabular
from galaxy.util import nice_size

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
                    if idx == 0 and not self.is_float(fields[0]):
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
            if len(cells) < 2 or not self.is_float(cells[0]) or not self.is_float(cells[1]):
                return False
            return True
        return False


def _is_be_label(label: str) -> bool:
    label = label.strip().lower()
    if not label:
        return False
    # Recognise "binding energy", "be", "be (ev)", "binding energy (ev)" ...
    return label.startswith("binding energy") or label in {"be", "be (ev)", "binding_energy"}


class NXxps(H5):
    """
    NeXus file conforming to the ``NXxps`` application definition.

    ``NXxps`` (which extends ``NXmpes``) is the NeXus application definition
    for X-ray photoelectron spectroscopy. It is an HDF5 file containing an
    ``NXentry`` group whose ``definition`` field is set to ``"NXxps"``.

    See https://manual.nexusformat.org/classes/applications/NXxps.html

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.nxs.xps')
    >>> NXxps().sniff(fname)
    True
    >>> fname = get_test_fname('test.mz5')
    >>> NXxps().sniff(fname)
    False
    """

    file_ext = "nxxps"
    edam_format = "format_3590"

    def sniff(self, filename: str) -> bool:
        if not super().sniff(filename):
            return False
        return _nxxps_definition_matches(filename, expected="NXxps")

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "NeXus NXxps XPS data"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return f"NeXus NXxps XPS data ({nice_size(dataset.get_size())})"


def _nxxps_definition_matches(filename: str, expected: str) -> bool:
    """Return ``True`` if *filename* is a NeXus HDF5 file whose (default)
    ``NXentry`` carries a ``definition`` field equal to *expected*.

    The entry is located, in order of preference, via:

    * the root group ``default`` attribute (the NeXus-recommended way), then
    * a top-level group literally named ``entry``, then
    * any top-level group whose ``NX_class`` attribute is ``NXentry`` and
      whose ``definition`` field matches.
    """
    import h5py

    try:
        with h5py.File(filename, "r", locking=False) as handle:
            def _read_definition(group) -> Optional[str]:
                value = group.get("definition")
                if value is None:
                    return None
                try:
                    raw = value[()]
                except Exception:
                    return None
                if isinstance(raw, bytes):
                    raw = raw.decode()
                if hasattr(raw, "tolist"):
                    raw = raw.tolist()
                return str(raw).strip() if raw is not None else None

            # 1. Honour the NeXus ``default`` attribute on the root group.
            default = handle.attrs.get("default")
            if default is not None:
                default = default.decode() if isinstance(default, bytes) else str(default)
                entry = handle.get(default)
                if entry is not None and _read_definition(entry) == expected:
                    return True

            # 2. Common convention: a group literally named "entry".
            entry = handle.get("entry")
            if entry is not None and _read_definition(entry) == expected:
                return True

            # 3. Scan top-level groups for an NXentry with a matching definition.
            for name in handle.keys():
                group = handle.get(name)
                if not isinstance(group, h5py.Group):
                    continue
                nx_class = group.attrs.get("NX_class")
                if nx_class is not None:
                    nx_class = nx_class.decode() if isinstance(nx_class, bytes) else str(nx_class)
                if nx_class == "NXentry" and _read_definition(group) == expected:
                    return True
    except Exception:
        return False
    return False
