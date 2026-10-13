"""
Metabolomics Datatypes
"""

import logging
import re
from dataclasses import (
    dataclass,
    field,
)
from typing import Optional

from galaxy.datatypes import data
from galaxy.datatypes.data import (
    DatatypeValidation,
    Text,
)
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import (
    DatasetHasHidProtocol,
    DatasetProtocol,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)

log = logging.getLogger(__name__)


@dataclass
class MzTabMHeader:
    version: str | None = None
    id: str | None = None
    profile: str | None = None
    errors: list[str] = field(default_factory=list)


@build_sniff_from_prefix
class MzTabM(Text):
    """
    This is mzTab-M, a lightweight, tab-delimited file format for reporting mass spectrometry-based metabolomics results:
    It is a variant of mzTab, designed specifically for metabolomics data.
    https://github.com/HUPO-PSI/mzTab-M

    This implementation is currently based on the version 2.1.0-M. The specification can be found at:
    https://hupo-psi.github.io/mzTab-M/mztabm/2.1/developers/specification.html

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.mztabm')
    >>> MzTabM().sniff(fname)
    True
    >>> fname = get_test_fname('test.mztab2')
    >>> MzTabM().sniff(fname)
    False
    >>> fname = get_test_fname('test.mztab')
    >>> MzTabM().sniff(fname)
    False
    """

    edam_data = "data_4058"
    file_ext = "mztabm"

    _valid_version_pattern = r"2\.1\.[0-9]+-M"
    _version_re = re.compile(r"MTD\tmzTab-version\t" + _valid_version_pattern)

    MetadataElement(
        name="mztabm_version",
        default=None,
        desc="mzTab-M version",
        readonly=True,
        optional=False,
    )

    MetadataElement(
        name="mztabm_id",
        default=None,
        desc="mzTab-M ID",
        readonly=True,
        optional=False,
    )

    MetadataElement(
        name="mztabm_profile",
        default=None,
        desc="mzTab-M profile",
        readonly=True,
        optional=True,
    )

    _valid_profiles = {
        "M",
        "M+S",
        "M+F",
        "M+F+E",
        "M+S+F",  # this profile is not recommended by the mzTab-M specification, but it is still valid and should be accepted by Galaxy
        "M+S+F+E",
    }

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""

        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "mzTab-M Format"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file is mzTab-M format."""

        for line in file_prefix.line_iterator():
            line = line.rstrip()
            # Skip empty and comment (starting with COM) lines
            if not line.strip() or line.startswith("COM"):
                continue
            return bool(self._version_re.fullmatch(line))
        return False

    def _read_mtd_header(self, lines) -> MzTabMHeader:
        """
        Read and do minimal validation on the first three MTD fields.

        Returns a MzTabMHeader object containing the parsed metadata and any validation errors.
        """
        header = MzTabMHeader()
        mtd_field_index = 0

        for line_number, line in enumerate(lines, start=1):
            if mtd_field_index >= 3:
                break
            line = line.rstrip()
            # Skip empty and comment (starting with COM) lines
            if not line.strip() or line.startswith("COM"):
                continue
            if not line.startswith("MTD\t"):
                break
            mtd_field_index += 1
            columns = line.split("\t", 2)
            if len(columns) < 3:
                header.errors.append(f"Invalid MTD line at line {line_number}: has fewer than three fields.")
                continue
            key, value = columns[1], columns[2]
            match mtd_field_index:
                case 1:
                    if key != "mzTab-version":
                        header.errors.append(
                            f"Invalid MTD line at line {line_number}: the first MTD field must be "
                            f"mzTab-version, found '{key}'."
                        )
                        continue
                    header.version = value
                case 2:
                    if key != "mzTab-ID":
                        header.errors.append(
                            f"Invalid MTD line at line {line_number}: the second MTD field must be "
                            f"mzTab-ID, found '{key}'."
                        )
                        continue
                    header.id = value
                case 3:
                    # mzTab-profile is optional so no error here
                    if key == "mzTab-profile":
                        header.profile = value
                    break
        if header.version is None:
            header.errors.append("mzTab-version metadata field is missing.")
        if header.id is None:
            header.errors.append("mzTab-ID metadata field is missing.")
        return header

    def _infer_profile(self, lines) -> str:
        """Infer the mzTab-M profile from the section headers."""

        profile = "M"
        for line in lines:
            line = line.rstrip()
            # A valid mzTab-M file has only one header line per section.
            if line.startswith("SMH"):
                profile += "+S"
            elif line.startswith("SFH"):
                profile += "+F"
            elif line.startswith("SEH"):
                profile += "+E"
                break
        return profile

    def _validate(self, filename: str) -> MzTabMHeader:
        """Minimal validation of the mzTab-M metadata header and profile."""

        with open(filename, encoding="utf-8-sig") as f:
            header = self._read_mtd_header(f)
            if (
                header.version is not None
                and self._version_re.fullmatch(f"MTD\tmzTab-version\t{header.version}") is None
            ):
                header.errors.append(
                    f"Invalid mzTab-M version: '{header.version}'. Valid pattern is '{self._valid_version_pattern}'."
                )

        if header.profile is None:
            with open(filename, encoding="utf-8-sig") as f:
                header.profile = self._infer_profile(f)
        if header.profile not in self._valid_profiles:
            header.errors.append(f"Invalid mzTab-M profile: '{header.profile}'.")
        return header

    def validate(
        self,
        dataset: DatasetProtocol,
        **kwd,
    ) -> DatatypeValidation:
        header = self._validate(dataset.get_file_name())
        if header.errors:
            return DatatypeValidation.invalid("\n".join(header.errors))
        return DatatypeValidation.validated()

    def set_meta(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set mzTab-M metadata."""

        if dataset.dataset.purged:
            return
        with open(dataset.get_file_name(), encoding="utf-8-sig") as f:
            header = self._read_mtd_header(f)
            if header.errors:
                return
            dataset.metadata.mztabm_version = header.version
            dataset.metadata.mztabm_id = header.id

        if header.profile is None:
            with open(dataset.get_file_name(), encoding="utf-8-sig") as f:
                header.profile = self._infer_profile(f)
        if header.profile in self._valid_profiles:
            dataset.metadata.mztabm_profile = header.profile
        else:
            log.warning("Invalid mzTab-M profile: %s", header.profile)

    def display_data(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        **kwd,
    ):
        # mzTab-M files conventionally use the .mztab extension, but Galaxy
        # already uses "mztab" for the mzTab datatype. Keep "mztabm" as the
        # Galaxy datatype extension and use .mztab extension when exporting.
        if to_ext == self.file_ext:
            to_ext = "mztab"
        return super().display_data(trans, dataset, preview=preview, filename=filename, to_ext=to_ext, **kwd)
