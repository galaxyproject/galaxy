import abc
import logging
import os
from typing import (
    Set,
    Union,
)

from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    iter_headers,
)
from .tabular import Tabular

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class GoldenPath(Tabular):
    """Class describing NCBI's Golden Path assembly format"""

    edam_format = "format_3693"
    file_ext = "agp"

    def set_meta(self, dataset, **kwd):
        # AGPFile reads and validates entire file.
        AGPFile(dataset.file_name)
        super().set_meta(dataset, **kwd)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Checks for and does cursory validation on data that looks like AGP

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('eg1.agp')
        >>> GoldenPath().sniff(fname)
        True
        >>> fname = get_test_fname('eg2.agp')
        >>> GoldenPath().sniff(fname)
        True
        >>> fname = get_test_fname('1.bed')
        >>> GoldenPath().sniff(fname)
        False
        >>> fname = get_test_fname('2.tabular')
        >>> GoldenPath().sniff(fname)
        False
        """
        found_non_comment_lines = False
        try:
            for line in iter_headers(file_prefix, "\t", comment_designator="#"):
                if line:
                    if len(line) != 9:
                        return False
                    assert line[4] in ["A", "D", "F", "G", "O", "P", "W", "N", "U"]
                    ostensible_numbers = line[1:3]
                    if line[4] in ["U", "N"]:
                        ostensible_numbers.append(line[5])
                        assert line[6] in [
                            "scaffold",
                            "contig",
                            "centromere",
                            "short_arm",
                            "heterochromatin",
                            "telomere",
                            "repeat",
                        ]
                        assert line[7] in ["yes", "no"]
                        assert line[8] in [
                            "na",
                            "paired-ends",
                            "align_genus",
                            "align_xgenus",
                            "align_trnscript",
                            "within_clone",
                            "clone_contig",
                            "map",
                            "strobe",
                            "unspecified",
                        ]
                    else:
                        ostensible_numbers.extend([line[6], line[7]])
                        assert line[8] in ["+", "-", "?", "0", "na"]
                    if line[4] == "U":
                        assert int(line[5]) == 100
                    assert all(map(lambda x: str(x).isnumeric() and int(x) > 0, ostensible_numbers))
                    found_non_comment_lines = True
        except Exception:
            return False
        return found_non_comment_lines


class AGPError(Exception):
    """Exception raised for AGP related errors."""

    def __init__(self, fname, line_number, message="Error in AGP file."):
        self.fname = fname
        self.line_number = line_number
        self.message = message

        self.report = f"\n\nFILE: {self.fname}\nLINE: {self.line_number}\nERROR: {self.message}"
        super().__init__(self.report)

    def __repr__(self):
        return "AGPError"


class AGPFile:
    """
    A class storing the contents of an AGP v2.1 file. https://www.ncbi.nlm.nih.gov/assembly/agp/AGP_Specification/

    The class is able to read new AGP lines in order to sequentially build the complete file.

    The class should be capable of checking the validity of the file, as well as writing the AGP contents
    to a file stream.

    Common abbreviations:
      "comp": AGP component
      "obj":  AGP object
      "pid":  AGP part number
    """

    def __init__(self, in_file):

        self._agp_version = "2.1"
        self._fname = os.path.abspath(in_file)

        # Store comment and AGP lines separately.
        self._comment_lines = []
        self._objects = []

        # Store info enabling us to keep track of the state of the AGP file
        self._current_obj = None
        self._seen_objs = set()

        # Read the contents of the AGP file
        self._read_file()

    def _read_file(self):
        """
        Read the agp file associated with this instance of the class. If that file doesn't exist yet,
        proceed without reading anything.

        When reading, check the validity of individual AGP lines.
        """
        if not os.path.isfile(self.fname):
            return

        # The AGP file exists. Initialize everything.
        self._comment_lines = []
        self._objects = []
        self._current_obj = None
        self._seen_objs = set()

        line_number = 0
        in_body = False
        with open(self.fname) as f:
            for line in f:
                line_number += 1
                line = line.rstrip("\n")
                if line.startswith("#"):
                    if not in_body:
                        self._comment_lines.append(line)
                    else:
                        raise AGPError(self.fname, line_number, "illegal comment in AGP body")
                    continue

                # In a valid AGP file, we should no longer see comment lines
                in_body = True
                fields = line.split("\t")

                # There should be exactly 9 tab delimited fields
                if not len(fields) == 9:
                    raise AGPError(self.fname, line_number, "detected more than 9 tab delimited fields")

                # All fields should have a value
                if not all(fields):
                    raise AGPError(self.fname, line_number, "detected an empty field")

                agp_line: Union[AGPGapLine, AGPSeqLine]
                # Instantiate all the AGPLine objects. These will do line-specific validations.
                if fields[4] == "N" or fields[4] == "U":
                    agp_line = AGPGapLine(self.fname, line_number, *fields)
                else:
                    agp_line = AGPSeqLine(self.fname, line_number, *fields)

                self._add_line(agp_line)

    def _add_line(self, agp_line):
        # Perform validity checks if this is a new object
        if agp_line.obj != self._current_obj:

            # Check if we have already seen this object before
            if agp_line.obj in self._seen_objs:
                raise AGPError(self.fname, agp_line.line_number, "object identifier out of order")

            # Add the new object to our master list
            agp_obj = AGPObject(self.fname, agp_line)
            self._objects.append(agp_obj)

            # Initialize all the info for this new object
            self._current_obj = agp_obj.obj
            self._seen_objs.add(agp_obj.obj)

        else:
            self._objects[-1].add_line(agp_line)

    @property
    def agp_version(self):
        return self._agp_version

    @property
    def fname(self):
        return self._fname

    @property
    def num_lines(self):
        """Calculate the number of lines in the current state of the AGP file."""
        return len(self._comment_lines) + sum(obj.num_lines for obj in self._objects)

    def iterate_objs(self):
        """Iterate over the objects of the AGP file."""
        yield from self._objects

    def iterate_lines(self):
        """Iterate over the non-comment lines of AGP file."""
        for obj in self.iterate_objs():
            yield from obj.iterate_lines()


class AGPObject:
    """
    Represents an AGP object. Objects will consist of AGP lines, and have to adhere to
    certain rules. By organizing AGP lines into the objects that they comprise, we can easily calculate stats
    about the assembly (the collection of objects).
    """

    def __init__(self, agp_fname, in_agp_line):
        if not isinstance(in_agp_line, AGPLine):
            raise TypeError("in_agp_line must be an instance of 'AGPLine'")

        # The object is defined by the object identifier and a list of AGP lines
        self.fname = agp_fname
        self._obj = in_agp_line.obj
        self._agp_lines = []

        # Store info enabling us to keep track of the state of the object
        self.previous_pid = 0
        self.obj_intervals = []  # Stores intervals as 0-indexed

        # Perform checks to ensure the object is properly initialized
        if not in_agp_line.obj_beg == 1:
            raise AGPError(self.fname, in_agp_line.line_number, "the first object coordinates should start with '1'")

        if not in_agp_line.pid == 1:
            raise AGPError(self.fname, in_agp_line.line_number, "all objects should start with a 'part_number' of '1'")

        # If we have passed the initialization tests, add this line like any other
        self.add_line(in_agp_line)

    def __str__(self):
        return "\n".join(str(i) for i in self._agp_lines)

    def __repr__(self):
        return f"AGP Object: {self.obj}"

    def __iter__(self):
        for line in self._agp_lines:
            yield dict(line)

    @property
    def obj(self):
        return self._obj

    @property
    def obj_len(self):
        return int(self.obj_intervals[-1][1])

    @property
    def num_lines(self):
        return len(self._agp_lines)

    def add_line(self, agp_line):
        # Perform validity checks if this is a new object
        if agp_line.obj != self.obj:
            raise AGPError(self.fname, agp_line, f"cannot add line from object {agp_line.obj} to object {self.obj}")

        # Check that our PID is sequential
        if agp_line.pid - self.previous_pid != 1:
            raise AGPError(self.fname, agp_line.line_number, "non-sequential part_numbers")

        # Check that the object intervals are sequential
        if self.obj_intervals:
            if self.obj_intervals[-1][1] != agp_line.obj_beg - 1:
                raise AGPError(
                    self.fname,
                    agp_line.line_number,
                    f"some positions in {agp_line.obj} are not accounted for or overlapping",
                )

        self.previous_pid = agp_line.pid
        self.obj_intervals.append((agp_line.obj_beg - 1, agp_line.obj_end))
        self._agp_lines.append(agp_line)

    def iterate_lines(self):
        yield from self._agp_lines


class AGPLine(metaclass=abc.ABCMeta):
    """
    An abstract base class representing a single AGP file line. Inheriting subclasses should
    override or implement new methods to check the validity of a single AFP line. Validity
    checks that involve multiple lines should not be considered.
    """

    allowed_comp_types: Set[str] = set()

    def __init__(self, fname, line_number, obj, obj_beg, obj_end, pid, comp_type):
        self.is_gap = None

        # File info
        self.fname = fname
        self.line_number = line_number
        # Object info
        self.obj = obj
        self.obj_beg = obj_beg
        self.obj_end = obj_end
        self.pid = pid
        self.comp_type = comp_type

        self._validate_numerics()
        self._validate_strings()
        self._validate_obj_coords()
        self._validate_component_type()
        self._validate_line()

    @abc.abstractmethod
    def __str__(self):
        """Return the tab delimited AGP line"""
        pass

    @abc.abstractmethod
    def __iter__(self):
        """Return the AGP line's iterator"""
        pass

    @abc.abstractmethod
    def _validate_numerics(self):
        """Ensure all numeric fields and positive integers."""
        pass

    @abc.abstractmethod
    def _validate_strings(self):
        """Ensure all text fields are strings."""
        pass

    def _validate_obj_coords(self):
        if self.obj_beg > self.obj_end:
            raise AGPError(
                self.fname, self.line_number, f"object_beg ({self.obj_beg}) must be <= object_end ({self.obj_end})"
            )

    def _validate_component_type(self):
        if self.comp_type not in self.allowed_comp_types:
            raise AGPError(self.fname, self.line_number, f"invalid component type: {self.comp_type}")

    @abc.abstractmethod
    def _validate_line(self):
        """Final remaining validations specific to the gap or sequence AGP lines."""
        pass


class AGPSeqLine(AGPLine):

    """
    A subclass of AGPLine specifically for AGP lines that represent sequences.
    """

    allowed_comp_types = {"A", "D", "F", "G", "O", "P", "W"}
    allowed_orientations = {"+", "-", "?", "0", "na"}

    def __init__(
        self, fname, line_number, obj, obj_beg, obj_end, pid, comp_type, comp, comp_beg, comp_end, orientation
    ):
        self.comp = comp
        self.comp_beg = comp_beg
        self.comp_end = comp_end
        self.orientation = orientation

        # Set the object attributes and perform superclass-defined validations
        super().__init__(fname, line_number, obj, obj_beg, obj_end, pid, comp_type)

        self.is_gap = False
        self.seqdict = dict(
            obj=str(self.obj),
            obj_beg=int(self.obj_beg),
            obj_end=int(self.obj_end),
            pid=int(self.pid),
            comp_type=str(self.comp_type),
            comp=str(self.comp),
            comp_beg=int(self.comp_beg),
            comp_end=int(self.comp_end),
            orientation=str(self.orientation),
        )

    def __str__(self):
        return "\t".join(
            [
                self.obj,
                str(self.obj_beg),
                str(self.obj_end),
                str(self.pid),
                self.comp_type,
                self.comp,
                str(self.comp_beg),
                str(self.comp_end),
                self.orientation,
            ]
        )

    def __iter__(self):
        for key in self.seqdict:
            yield str(key), self.seqdict[key]

    def _validate_numerics(self):
        # Convert all numeric types to integers
        try:
            self.line_number = int(self.line_number)
            self.obj_beg = int(self.obj_beg)
            self.obj_end = int(self.obj_end)
            self.pid = int(self.pid)
            self.comp_beg = int(self.comp_beg)
            self.comp_end = int(self.comp_end)
        except TypeError:
            raise AGPError(self.fname, self.line_number, "encountered an invalid non-integer numeric AGP field")

        # Ensure that all numeric values are positive
        if not all([self.obj_beg > 0, self.obj_end > 0, self.pid > 0, self.comp_beg > 0, self.comp_end > 0]):
            raise AGPError(self.fname, self.line_number, "encountered an invalid zero or negative numeric AGP field.")

        # Check the coordinates
        if self.comp_beg > self.comp_end:
            raise AGPError(
                self.fname,
                self.line_number,
                f"component_beg ({self.comp_beg}) must be <= component_end ({self.comp_end})",
            )

        if self.obj_end - (self.obj_beg - 1) != self.comp_end - (self.comp_beg - 1):
            raise AGPError(
                self.fname,
                self.line_number,
                f"object coordinates ({self.obj_beg}, {self.obj_end}) and component coordinates ({self.comp_beg}, {self.comp_end}) do not have the same length",
            )

    def _validate_strings(self):
        try:
            self.obj = str(self.obj)
            self.comp_type = str(self.comp_type)
            self.comp = str(self.comp)
            self.orientation = str(self.orientation)
        except TypeError:
            raise AGPError(self.fname, self.line_number, "encountered an invalid type for an AGP text field")

    def _validate_line(self):
        if self.orientation not in AGPSeqLine.allowed_orientations:
            raise AGPError(self.fname, self.line_number, f"invalid orientation: {self.orientation}")


class AGPGapLine(AGPLine):

    """
    A subclass of AGPLine specifically for AGP lines that represent sequence gaps.
    """

    allowed_comp_types = {"N", "U"}
    allowed_linkage_types = {"yes", "no"}
    allowed_gap_types = {
        "scaffold",
        "contig",
        "centromere",
        "short_arm",
        "heterochromatin",
        "telomere",
        "repeat",
        "contamination",
    }
    allowed_evidence_types = {
        "na",
        "paired-ends",
        "align_genus",
        "align_xgenus",
        "align_trnscpt",
        "within_clone",
        "clone_contig",
        "map",
        "pcr",
        "proximity_ligation",
        "strobe",
        "unspecified",
    }

    def __init__(
        self, fname, line_number, obj, obj_beg, obj_end, pid, comp_type, gap_len, gap_type, linkage, linkage_evidence
    ):
        self.gap_len = gap_len
        self.gap_type = gap_type
        self.linkage = linkage
        self.linkage_evidence = linkage_evidence

        # Set the object attributes and perform superclass-defined validations
        super().__init__(fname, line_number, obj, obj_beg, obj_end, pid, comp_type)

        self.is_gap = True
        self.gapdict = dict(
            obj=str(self.obj),
            obj_beg=int(self.obj_beg),
            obj_end=int(self.obj_end),
            pid=int(self.pid),
            comp_type=str(self.comp_type),
            gap_len=int(self.gap_len),
            gap_type=str(self.gap_type),
            linkage=str(self.linkage),
            linkage_evidence=str(self.linkage_evidence),
        )

    def __str__(self):
        return "\t".join(
            [
                self.obj,
                str(self.obj_beg),
                str(self.obj_end),
                str(self.pid),
                self.comp_type,
                str(self.gap_len),
                self.gap_type,
                self.linkage,
                self.linkage_evidence,
            ]
        )

    def __iter__(self):
        for key in self.gapdict:
            yield str(key), self.gapdict[key]

    def _validate_numerics(self):
        # Convert all numeric types to integers
        try:
            self.line_number = int(self.line_number)
            self.obj_beg = int(self.obj_beg)
            self.obj_end = int(self.obj_end)
            self.pid = int(self.pid)
            self.gap_len = int(self.gap_len)
        except TypeError:
            raise AGPError(self.fname, self.line_number, "encountered an invalid non-integer numeric AGP field")

        # Ensure that all numeric values are positive
        if not all([self.obj_beg > 0, self.obj_end > 0, self.pid > 0, self.gap_len > 0]):
            raise AGPError(self.fname, self.line_number, "encountered an invalid negative numeric AGP field")

        # Make sure the coordinates match
        if self.obj_end - (self.obj_beg - 1) != self.gap_len:
            raise AGPError(
                self.fname,
                self.line_number,
                f"object coordinates ({self.obj_beg}, {self.obj_end}) and gap length ({self.gap_len}) are not the same length",
            )

    def _validate_strings(self):
        try:
            self.obj = str(self.obj)
            self.comp_type = str(self.comp_type)
            self.gap_type = str(self.gap_type)
            self.linkage = str(self.linkage)
            self.linkage_evidence = str(self.linkage_evidence)
        except TypeError:
            raise AGPError(self.fname, self.line_number, "encountered an invalid type for an AGP text field")

    def _validate_line(self):
        """Validation specific to AGP gap lines."""
        if self.comp_type == "U" and self.gap_len != 100:
            raise AGPError(
                self.fname,
                self.line_number,
                f"invalid gap length for component type 'U': {self.gap_len} (should be 100)",
            )

        if self.gap_type not in AGPGapLine.allowed_gap_types:
            raise AGPError(self.fname, self.line_number, f"invalid gap type: {self.gap_type}")

        if self.linkage not in AGPGapLine.allowed_linkage_types:
            raise AGPError(self.fname, self.line_number, f"invalid linkage field: {self.linkage}")

        all_evidence = self.linkage_evidence.split(";")
        for e in all_evidence:
            if e not in AGPGapLine.allowed_evidence_types:
                raise AGPError(self.fname, self.line_number, f"invalid linkage evidence: {e}")

        if self.linkage == "no":
            if self.gap_type == "scaffold":
                raise AGPError(self.fname, self.line_number, "invalid 'scaffold' gap without linkage evidence")

            if self.linkage_evidence != "na":
                raise AGPError(
                    self.fname,
                    self.line_number,
                    f"linkage evidence must be 'na' when not asserting linkage. Got {self.linkage_evidence}",
                )
        else:
            if "na" in all_evidence:
                log.warning(
                    AGPError(self.fname, self.line_number, "'na' is invalid linkage evidence when asserting linkage")
                )
