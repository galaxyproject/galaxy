"""
X-ray Photoelectron Spectroscopy (XPS) Datatypes

Datatypes for surface analysis data produced by X-ray photoelectron
spectroscopy (XPS, also known as ESCA). Two related formats are provided:

* :class:`Vamas` - the ISO 14976 VAMAS standard plain-text format, the
  open interchange format for surface analysis data (XPS, AES, ISS, ...).
  See https://www.iso.org/standard/24269.html (ISO 14976).
* :class:`NXxps` - a NeXus HDF5 file conforming to the ``NXxps`` application
  definition (which extends ``NXmpes``), the recommended HDF5-based format
  for XPS data exchange.
  See https://manual.nexusformat.org/classes/applications/NXxps.html
"""

import logging
from typing import Optional

import h5py

from galaxy.datatypes import data
from galaxy.datatypes.binary import H5
from galaxy.datatypes.data import Text
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.util import (
    nice_size,
    unicodify,
)

log = logging.getLogger(__name__)


# Surface analysis techniques defined in ISO 14976 (VAMAS).
# The technique keyword is the line that identifies the type of measurement;
# XPS is the one we are interested in, but a VAMAS file may legitimately
# carry any of these values.
_VAMAS_TECHNIQUES = {
    "AES",
    "AES diff",
    "AES dir",
    "EDX",
    "ELS",
    "FABMS",
    "FABMS energy spec",
    "ISS",
    "SIMS",
    "SIMS energy spec",
    "SNMS",
    "SNMS energy spec",
    "UPS",
    "XPS",
    "XRF",
}


@build_sniff_from_prefix
class Vamas(Text):
    """
    ISO 14976 VAMAS surface analysis file (XPS).

    The VAMAS standard is the open, vendor-neutral interchange format for
    surface analysis data. The file is plain text and is organised as an
    experiment header followed by blocks containing a technique keyword
    (``XPS`` for X-ray photoelectron spectroscopy).

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.vms')
    >>> Vamas().sniff(fname)
    True
    >>> fname = get_test_fname('sequence.fasta')
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

        The sniffer requires the standard format identifier followed by a
        technique keyword from the ISO 14976 list (``XPS``, ``AES``, ...).
        The keyword occurs in each data block and its line number varies
        with the experiment header, so the complete sniff prefix is searched.
        """
        lines = file_prefix.line_iterator()
        try:
            identifier = next(lines).strip()
        except StopIteration:
            return False
        if identifier != "VAMAS Surface Chemical Analysis Standard Data Transfer Format 1988 May 4":
            return False
        return any(line.strip() in _VAMAS_TECHNIQUES for line in lines)


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


def _read_definition(group: h5py.Group) -> Optional[str]:
    """Return the ``definition`` field of *group* as text, or ``None``."""
    if not isinstance(group, h5py.Group):
        return None
    value = group.get("definition")
    if value is None:
        return None
    try:
        raw = value[()]
    except Exception:
        log.debug("Could not read NeXus 'definition' field", exc_info=True)
        return None
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if isinstance(raw, list):
        raw = raw[0] if len(raw) == 1 else None
    if raw is None:
        return None
    return unicodify(raw).strip()


def _nxxps_definition_matches(filename: str, expected: str) -> bool:
    """Return ``True`` if *filename* is a NeXus HDF5 file whose (default)
    ``NXentry`` carries a ``definition`` field equal to *expected*.

    The entry is located, in order of preference, via:

    * the root group ``default`` attribute (the NeXus-recommended way), then
    * a top-level group literally named ``entry``, then
    * any top-level group whose ``NX_class`` attribute is ``NXentry`` and
      whose ``definition`` field matches.
    """
    try:
        with h5py.File(filename, "r", locking=False) as handle:
            # 1. Honour the NeXus ``default`` attribute on the root group.
            default = handle.attrs.get("default")
            if default is not None:
                default = default.decode() if isinstance(default, bytes) else str(default)
                entry = handle.get(default)
                if _read_definition(entry) == expected:
                    return True

            # 2. Common convention: a group literally named "entry".
            entry = handle.get("entry")
            if _read_definition(entry) == expected:
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
        log.debug("Could not inspect NeXus application definition in %s", filename, exc_info=True)
        return False
    return False
