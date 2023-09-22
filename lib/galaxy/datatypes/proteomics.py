"""
Proteomics Datatypes
"""
import logging
import re
from typing import (
    IO,
    List,
    Optional,
)

from galaxy.datatypes import data
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.data import Text
from galaxy.datatypes.protocols import (
    DatasetProtocol,
    HasExtraFilesAndMetadata,
)
from galaxy.datatypes.sequence import Sequence
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.tabular import (
    Tabular,
    TabularData,
)
from galaxy.datatypes.xml import GenericXml
from galaxy.util import nice_size

log = logging.getLogger(__name__)


class Wiff(Binary):
    """Class for wiff files."""

    edam_data = "data_2536"
    edam_format = "format_3710"
    file_ext = "wiff"
    composite_type = "auto_primary_file"

    def __init__(self, **kwd):
        super().__init__(**kwd)

        self.add_composite_file(
            "wiff",
            description="AB SCIEX files in .wiff format. This can contain all needed information or only metadata.",
            is_binary=True,
        )

        self.add_composite_file(
            "wiff_scan",
            description="AB SCIEX spectra file (wiff.scan), if the corresponding .wiff file only contains metadata.",
            optional="True",
            is_binary=True,
        )

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head><title>Wiff Composite Dataset </title></head><p/>"]
        rval.append("<div>This composite dataset is composed of the following files:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ""
            if composite_file.optional:
                opt_text = " (optional)"
            if composite_file.get("description"):
                rval.append(
                    f"<li><a href=\"{fn}\" type=\"text/plain\">{fn} ({composite_file.get('description')})</a>{opt_text}</li>"
                )
            else:
                rval.append(f'<li><a href="{fn}" type="text/plain">{fn}</a>{opt_text}</li>')
        rval.append("</ul></div></html>")
        return "\n".join(rval)


class Wiff2(Binary):
    """Class for wiff2 files."""

    edam_data = "data_2536"
    edam_format = "format_3710"
    file_ext = "wiff2"
    composite_type = "auto_primary_file"

    def __init__(self, **kwd):
        super().__init__(**kwd)

        self.add_composite_file(
            "wiff2",
            description="AB SCIEX files in .wiff2 format. This can contain all needed information or only metadata.",
            is_binary=True,
        )

        self.add_composite_file(
            "wiff_scan",
            description="AB SCIEX spectra file (wiff.scan), if the corresponding .wiff2 file only contains metadata.",
            optional="True",
            is_binary=True,
        )

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head><title>Wiff2 Composite Dataset </title></head><p/>"]
        rval.append("<div>This composite dataset is composed of the following files:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ""
            if composite_file.optional:
                opt_text = " (optional)"
            if composite_file.get("description"):
                rval.append(
                    f"<li><a href=\"{fn}\" type=\"text/plain\">{fn} ({composite_file.get('description')})</a>{opt_text}</li>"
                )
            else:
                rval.append(f'<li><a href="{fn}" type="text/plain">{fn}</a>{opt_text}</li>')
        rval.append("</ul></div></html>")
        return "\n".join(rval)


@build_sniff_from_prefix
class MzTab(Text):
    """
    exchange format for proteomics and metabolomics results

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.mztab')
    >>> MzTab().sniff(fname)
    True
    >>> fname = get_test_fname('test.mztab2')
    >>> MzTab().sniff(fname)
    False
    """

    edam_data = "data_3681"
    file_ext = "mztab"
    # section names (except MTD)
    _sections = ["PRH", "PRT", "PEH", "PEP", "PSH", "PSM", "SMH", "SML", "COM"]
    # mandatory metadata fields and list of allowed entries (in lower case)
    # (or None if everything is allowed)
    _man_mtd = {
        "mzTab-mode": ["complete", "summary"],
        "mzTab-type": ["quantification", "identification"],
        "description": None,
    }
    _version_re = r"(1)(\.[0-9])?(\.[0-9])?"

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "mzTab Format"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file is the correct type."""
        has_version = False
        found_man_mtd = set()
        contents = file_prefix.string_io()
        for line in contents:
            if re.match(r"^\s*$", line):
                continue
            columns = line.strip("\r\n").split("\t")
            if columns[0] == "MTD":
                if columns[1] == "mzTab-version" and re.match(self._version_re, columns[2]) is not None:
                    has_version = True
                elif columns[1] in self._man_mtd:
                    mandatory_field = self._man_mtd[columns[1]]
                    if mandatory_field is None or columns[2].lower() in mandatory_field:
                        found_man_mtd.add(columns[1])
            elif columns[0] not in self._sections:
                return False
        return has_version and found_man_mtd == set(self._man_mtd.keys())


class MzTab2(MzTab):
    """
    exchange format for proteomics and metabolomics results

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.mztab2')
    >>> MzTab2().sniff(fname)
    True
    >>> fname = get_test_fname('test.mztab')
    >>> MzTab2().sniff(fname)
    False
    """

    file_ext = "mztab2"
    _sections = ["SMH", "SML", "SFH", "SMF", "SEH", "SME", "COM"]
    _version_re = r"(2)(\.[0-9])?(\.[0-9])?-M$"
    _man_mtd = {"mzTab-ID": None}

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "mzTab2 Format"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class Kroenik(Tabular):
    """
    Kroenik (HardKloer sibling) files

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.kroenik')
    >>> Kroenik().sniff(fname)
    True
    >>> fname = get_test_fname('test.peplist')
    >>> Kroenik().sniff(fname)
    False
    """

    file_ext = "kroenik"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.column_names = [
            "File",
            "First Scan",
            "Last Scan",
            "Num of Scans",
            "Charge",
            "Monoisotopic Mass",
            "Base Isotope Peak",
            "Best Intensity",
            "Summed Intensity",
            "First RTime",
            "Last RTime",
            "Best RTime",
            "Best Correlation",
            "Modifications",
        ]

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        fh = file_prefix.string_io()
        line = [_.strip() for _ in fh.readline().split("\t")]
        if line != self.column_names:
            return False
        line = fh.readline().split("\t")
        try:
            [int(_) for _ in line[1:5]]
            [float(_) for _ in line[5:13]]
        except ValueError:
            return False
        return True


@build_sniff_from_prefix
class PepList(Tabular):
    """
    Peplist file as used in OpenMS
    https://github.com/OpenMS/OpenMS/blob/0fc8765670a0ad625c883f328de60f738f7325a4/src/openms/source/FORMAT/FileHandler.cpp#L432

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.peplist')
    >>> PepList().sniff(fname)
    True
    >>> fname = get_test_fname('test.psms')
    >>> PepList().sniff(fname)
    False
    """

    file_ext = "peplist"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.column_names = ["m/z", "rt(min)", "snr", "charge", "intensity"]

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        fh = file_prefix.string_io()
        line = [_.strip() for _ in fh.readline().split("\t")]
        if line == self.column_names:
            return True
        return False


@build_sniff_from_prefix
class PSMS(Tabular):
    """
    Percolator tab-delimited output (PSM level, .psms) as used in OpenMS
    https://github.com/OpenMS/OpenMS/blob/0fc8765670a0ad625c883f328de60f738f7325a4/src/openms/source/FORMAT/FileHandler.cpp#L453
    see also http://www.kojak-ms.org/docs/percresults.html

    Note that the data rows can have more columns than the header line
    since ProteinIds are listed tab-separated.

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.psms')
    >>> PSMS().sniff(fname)
    True
    >>> fname = get_test_fname('test.kroenik')
    >>> PSMS().sniff(fname)
    False
    """

    file_ext = "psms"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.column_names = ["PSMId", "score", "q-value", "posterior_error_prob", "peptide", "proteinIds"]

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        fh = file_prefix.string_io()
        line = [_.strip() for _ in fh.readline().split("\t")]
        if line == self.column_names:
            return True
        return False


@build_sniff_from_prefix
class PEFF(Sequence):
    """
    PSI Extended FASTA Format
    https://github.com/HUPO-PSI/PEFF
    """

    file_ext = "peff"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'test.peff' )
        >>> PEFF().sniff( fname )
        True
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> PEFF().sniff( fname )
        False
        """
        fh = file_prefix.string_io()
        if re.match(r"# PEFF \d+.\d+", fh.readline()):
            return True
        else:
            return False


class PepXmlReport(Tabular):
    """pepxml converted to tabular report"""

    edam_data = "data_2536"
    file_ext = "pepxml.tsv"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.column_names = [
            "Protein",
            "Peptide",
            "Assumed Charge",
            "Neutral Pep Mass (calculated)",
            "Neutral Mass",
            "Retention Time",
            "Start Scan",
            "End Scan",
            "Search Engine",
            "PeptideProphet Probability",
            "Interprophet Probability",
        ]

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)


class ProtXmlReport(Tabular):
    """protxml converted to tabular report"""

    edam_data = "data_2536"
    file_ext = "protxml.tsv"
    comment_lines = 1

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.column_names = [
            "Entry Number",
            "Group Probability",
            "Protein",
            "Protein Link",
            "Protein Probability",
            "Percent Coverage",
            "Number of Unique Peptides",
            "Total Independent Spectra",
            "Percent Share of Spectrum ID's",
            "Description",
            "Protein Molecular Weight",
            "Protein Length",
            "Is Nondegenerate Evidence",
            "Weight",
            "Precursor Ion Charge",
            "Peptide sequence",
            "Peptide Link",
            "NSP Adjusted Probability",
            "Initial Probability",
            "Number of Total Termini",
            "Number of Sibling Peptides Bin",
            "Number of Instances",
            "Peptide Group Designator",
            "Is Evidence?",
        ]

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)


class Dta(TabularData):
    """dta
    The first line contains the singly protonated peptide mass (MH+) and the
    peptide charge state separated by a space. Subsequent lines contain space
    separated pairs of fragment ion m/z and intensity values.
    """

    file_ext = "dta"
    comment_lines = 0

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        column_types = []
        data_row: List = []
        data_lines = 0
        if dataset.has_data():
            with open(dataset.file_name) as dtafile:
                for _ in dtafile:
                    data_lines += 1

        # Guess column types
        for cell in data_row:
            column_types.append(self.guess_type(cell))

        # Set metadata
        dataset.metadata.data_lines = data_lines
        dataset.metadata.comment_lines = 0
        dataset.metadata.column_types = ["float", "float"]
        dataset.metadata.columns = 2
        dataset.metadata.column_names = ["m/z", "intensity"]
        dataset.metadata.delimiter = " "


@build_sniff_from_prefix
class Dta2d(TabularData):
    """
    dta2d: files with three tab/space-separated columns.
    The default format is: retention time (seconds) , m/z , intensity.
    If the first line starts with '#', a different order is defined by the the
    order of the keywords 'MIN' (retention time in minutes) or 'SEC' (retention
    time in seconds), 'MZ', and 'INT'.
    Example: '#MZ MIN INT'
    The peaks of one retention time have to be in subsequent lines.

    Note: sniffer detects (tab or space separated) dta2d files with correct
    header, wo header seems to generic

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.dta2d')
    >>> Dta2d().sniff(fname)
    True
    >>> fname = get_test_fname('test.edta')
    >>> Dta2d().sniff(fname)
    False
    """

    file_ext = "dta2d"
    comment_lines = 0

    def _parse_header(self, line: List) -> Optional[List]:
        if len(line) != 3 or len(line[0]) < 3 or not line[0].startswith("#"):
            return None
        line[0] = line[0].lstrip("#")
        line = [_.strip() for _ in line]
        if "MZ" not in line or "INT" not in line or ("MIN" not in line and "SEC" not in line):
            return None
        return line

    def _parse_delimiter(self, line: str) -> Optional[str]:
        if len(line.split(" ")) == 3:
            return " "
        elif len(line.split("\t")) == 3:
            return "\t"
        return None

    def _parse_dataline(self, line: List) -> bool:
        try:
            line = [float(_) for _ in line]
        except ValueError:
            return False
        if not all(_ >= 0 for _ in line):
            return False
        return True

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        data_lines = 0
        delim = None
        if dataset.has_data():
            with open(dataset.file_name) as dtafile:
                for line in dtafile:
                    if delim is None:
                        delim = self._parse_delimiter(line)
                        dataset.metadata.column_names = self._parse_header(line.split(delim))
                    data_lines += 1

        # Set metadata
        if delim is not None:
            dataset.metadata.delimiter = delim

        dataset.metadata.data_lines = data_lines
        dataset.metadata.comment_lines = 0
        dataset.metadata.column_types = ["float", "float", "float"]
        dataset.metadata.columns = 3
        if dataset.metadata.column_names is None or dataset.metadata.column_names == []:
            dataset.metadata.comment_lines += 1
            dataset.metadata.data_lines -= 1
            dataset.metadata.column_names = ["SEC", "MZ", "INT"]

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        sep = None
        header = None
        for idx, line in enumerate(file_prefix.line_iterator()):
            line = line.strip()
            if sep is None:
                sep = self._parse_delimiter(line)
                if sep is None:
                    return False
            line = line.split(sep)
            if len(line) != 3:
                return False
            if idx == 0:
                header = self._parse_header(line)
                if (header is None) and not self._parse_dataline(line):
                    return False
            elif not self._parse_dataline(line):
                return False
        if sep is None or header is None:
            return False
        return True


@build_sniff_from_prefix
class Edta(TabularData):
    """
    Input text file containing tab, space or comma separated columns.
    The separator between columns is checked in the first line in this order.

    It supports three variants of this format.

    1. Columns are: RT, MZ, Intensity A header is optional.
    2. Columns are: RT, MZ, Intensity, Charge, <Meta-Data> columns{0,} A header is mandatory.
    3. Columns are: (RT, MZ, Intensity, Charge){1,}, <Meta-Data> columns{0,}
       Header is mandatory. First quadruplet is the consensus. All following
       quadruplets describe the sub-features. This variant is discerned from
       variant #2 by the name of the fifth column, which is required to be RT1
       (or rt1). All other column names for sub-features are faithfully ignored.

    Note the sniffer only detects files with header.

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.edta')
    >>> Edta().sniff(fname)
    True
    >>> fname = get_test_fname('test.dta2d')
    >>> Edta().sniff(fname)
    False
    """

    file_ext = "edta"
    comment_lines = 0

    def _parse_delimiter(self, line: str) -> Optional[str]:
        if len(line.split(" ")) >= 3:
            return " "
        elif len(line.split("\t")) >= 3:
            return "\t"
        elif len(line.split(",")) >= 3:
            return "\t"
        return None

    def _parse_type(self, line: List) -> Optional[int]:
        """
        parse the type from the header line
        types 1-3 as in the class docs, 0: type 1 wo/wrong header
        """
        if len(line) < 3:
            return None
        line = [_.lower().replace("/", "") for _ in line]
        if len(line) == 3:
            if line[0] == "rt" and line[1] == "mz" and (line[2] == "int" or line[2] == "intensity"):
                return 1
            else:
                return None
        if line[0] != "rt" or line[1] != "mz" or (line[2] != "int" and line[2] != "intensity") or line[3] != "charge":
            return None
        if not line[4].startswith("rt"):
            return 2
        else:
            return 3

    def _parse_dataline(self, line: List, tpe: Optional[int]) -> bool:
        if tpe == 2 or tpe == 3:
            idx = 4
        else:
            idx = 3
        try:
            line = [float(_) for _ in line[:idx]]
        except ValueError:
            return False
        if not all(_ >= 0 for _ in line[:idx]):
            return False
        return True

    def _clean_header(self, line: List) -> List:
        for idx, el in enumerate(line):
            el = el.lower()
            if el.startswith("rt"):
                line[idx] = "RT"
            elif el.startswith("int"):
                line[idx] = "intensity"
            elif el.startswith("mz"):
                line[idx] = "m/z"
            elif el.startswith("charge"):
                line[idx] = "charge"
            else:
                break
            if idx // 4 > 0:
                line[idx] += str(idx // 4)
        return line

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        data_lines = 0
        delim = None
        tpe = None
        if dataset.has_data():
            with open(dataset.file_name) as dtafile:
                for idx, line in enumerate(dtafile):
                    if idx == 0:
                        delim = self._parse_delimiter(line)
                        tpe = self._parse_type(line.split(delim))
                        if tpe == 0:
                            dataset.metadata.column_names = ["RT", "m/z", "intensity"]
                        else:
                            dataset.metadata.column_names = self._clean_header(line.split(delim))
                    data_lines += 1

        # Set metadata
        if delim is not None:
            dataset.metadata.delimiter = delim
        for c in dataset.metadata.column_names:
            if any(c.startswith(_) for _ in ["RT", "m/z", "intensity", "charge"]):
                dataset.metadata.column_types.append("float")
            else:
                dataset.metadata.column_types.append("str")

        dataset.metadata.data_lines = data_lines
        dataset.metadata.comment_lines = 0
        dataset.metadata.columns = len(dataset.metadata.column_names)
        if tpe is not None and tpe > 0:
            dataset.metadata.comment_lines += 1
            dataset.metadata.data_lines -= 1

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        sep = None
        tpe = None
        for idx, line in enumerate(file_prefix.line_iterator()):
            line = line.strip("\r\n")
            if sep is None:
                sep = self._parse_delimiter(line)
                if sep is None:
                    return False
            line = line.split(sep)

            if idx == 0:
                tpe = self._parse_type(line)
                if tpe is None:
                    return False
                elif tpe == 0 and not self._parse_dataline(line, tpe):
                    return False
            elif not self._parse_dataline(line, tpe):
                return False
        if tpe is None:
            return False
        return True


class ProteomicsXml(GenericXml):
    """An enhanced XML datatype used to reuse code across several
    proteomic/mass-spec datatypes."""

    edam_data = "data_2536"
    edam_format = "format_2032"
    root: str

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file is the correct XML type."""
        for line in file_prefix.line_iterator():
            line = line.strip()
            if not line.startswith("<?"):
                break
        # pattern match <root or <ns:root for any ns string
        pattern = r"<(\w*:)?%s" % self.root
        return re.search(pattern, line) is not None

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "ProteomicsXML data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class ParamXml(ProteomicsXml):
    """store Parameters in XML formal"""

    file_ext = "paramxml"
    blurb = "parameters in xmls"
    root = "parameters|PARAMETERS"


class PepXml(ProteomicsXml):
    """pepXML data"""

    edam_format = "format_3655"
    file_ext = "pepxml"
    blurb = "pepXML data"
    root = "msms_pipeline_analysis"


class MascotXML(ProteomicsXml):
    """mzXML data"""

    file_ext = "mascotxml"
    blurb = "mascot Mass Spectrometry data"
    root = "mascot_search_results"


class MzML(ProteomicsXml):
    """mzML data"""

    edam_format = "format_3244"
    file_ext = "mzml"
    blurb = "mzML Mass Spectrometry data"
    root = "(mzML|indexedmzML)"


class NmrML(ProteomicsXml):
    """nmrML data"""

    # No edam format number yet.
    file_ext = "nmrml"
    blurb = "nmrML NMR data"
    root = "nmrML"


class ProtXML(ProteomicsXml):
    """protXML data"""

    file_ext = "protxml"
    blurb = "prot XML Search Results"
    root = "protein_summary"


class MzXML(ProteomicsXml):
    """mzXML data"""

    edam_format = "format_3654"
    file_ext = "mzxml"
    blurb = "mzXML Mass Spectrometry data"
    root = "mzXML"


class MzData(ProteomicsXml):
    """mzData data"""

    edam_format = "format_3245"
    file_ext = "mzdata"
    blurb = "mzData Mass Spectrometry data"
    root = "mzData"


class MzIdentML(ProteomicsXml):
    edam_format = "format_3247"
    file_ext = "mzid"
    blurb = "XML identified peptides and proteins."
    root = "MzIdentML"


class TraML(ProteomicsXml):
    edam_format = "format_3246"
    file_ext = "traml"
    blurb = "TraML transition list"
    root = "TraML"


class TrafoXML(ProteomicsXml):
    file_ext = "trafoxml"
    blurb = "RT alignment tranformation"
    root = "TrafoXML"


class MzQuantML(ProteomicsXml):
    edam_format = "format_3248"
    file_ext = "mzq"
    blurb = "XML quantification data"
    root = "MzQuantML"


class ConsensusXML(ProteomicsXml):
    file_ext = "consensusxml"
    blurb = "OpenMS multiple LC-MS map alignment file"
    root = "consensusXML"


class FeatureXML(ProteomicsXml):
    file_ext = "featurexml"
    blurb = "OpenMS feature file"
    root = "featureMap"


class IdXML(ProteomicsXml):
    file_ext = "idxml"
    blurb = "OpenMS identification file"
    root = "IdXML"


class TandemXML(ProteomicsXml):
    edam_format = "format_3711"
    file_ext = "tandem"
    blurb = "X!Tandem search results file"
    root = "bioml"


class UniProtXML(ProteomicsXml):
    file_ext = "uniprotxml"
    blurb = "UniProt Proteome file"
    root = "uniprot"


class XquestXML(ProteomicsXml):
    file_ext = "xquest.xml"
    blurb = "XQuest XML file"
    root = "xquest_results"


class XquestSpecXML(ProteomicsXml):
    """spec.xml"""

    file_ext = "spec.xml"
    blurb = "xquest_spectra"
    root = "xquest_spectra"


class QCML(ProteomicsXml):
    """qcml
    https://github.com/OpenMS/OpenMS/blob/113c49d01677f7f03343ce7cd542d83c99b351ee/share/OpenMS/SCHEMAS/mzQCML_0_0_5.xsd
    https://github.com/OpenMS/OpenMS/blob/3cfc57ad1788e7ab2bd6dd9862818b2855234c3f/share/OpenMS/SCHEMAS/qcML_0.0.7.xsd
    """

    file_ext = "qcml"
    blurb = "QualityAssessments to runs"
    root = "qcML|MzQualityML)"


class Mgf(Text):
    """Mascot Generic Format data"""

    edam_data = "data_2536"
    edam_format = "format_3651"
    file_ext = "mgf"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "mgf Mascot Generic Format"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff(self, filename: str) -> bool:
        mgf_begin_ions = "BEGIN IONS"
        max_lines = 100

        with open(filename) as handle:
            for i, line in enumerate(handle):
                line = line.rstrip()
                if line == mgf_begin_ions:
                    return True
                if i > max_lines:
                    return False
        return False


class MascotDat(Text):
    """Mascot search results"""

    edam_data = "data_2536"
    edam_format = "format_3713"
    file_ext = "mascotdat"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "mascotdat Mascot Search Results"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff(self, filename: str) -> bool:
        mime_version = "MIME-Version: 1.0 (Generated by Mascot version 1.0)"
        max_lines = 10

        with open(filename) as handle:
            for i, line in enumerate(handle):
                line = line.rstrip()
                if line == mime_version:
                    return True
                if i > max_lines:
                    return False
        return False


class ThermoRAW(Binary):
    """Class describing a Thermo Finnigan binary RAW file"""

    edam_data = "data_2536"
    edam_format = "format_3712"
    file_ext = "thermo.raw"

    def sniff(self, filename: str) -> bool:
        # Thermo Finnigan RAW format is proprietary and hence not well documented.
        # Files start with 2 bytes that seem to differ followed by F\0i\0n\0n\0i\0g\0a\0n
        # This combination represents 17 bytes, but to play safe we read 20 bytes from
        # the start of the file.
        try:
            header = open(filename, "rb").read(20)
            finnigan = b"F\0i\0n\0n\0i\0g\0a\0n"
            if header.find(finnigan) != -1:
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "Thermo Finnigan RAW file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return f"Thermo Finnigan RAW file ({nice_size(dataset.get_size())})"


@build_sniff_from_prefix
class Msp(Text):
    """Output of NIST MS Search Program chemdata.nist.gov/mass-spc/ftp/mass-spc/PepLib.pdf"""

    file_ext = "msp"

    @staticmethod
    def next_line_starts_with(contents: IO, prefix: str) -> bool:
        next_line = contents.readline()
        return next_line is not None and next_line.startswith(prefix)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file is a NIST MSP output file."""
        begin_contents = file_prefix.contents_header
        if "\n" not in begin_contents:
            return False
        lines = begin_contents.splitlines()
        if len(lines) < 2:
            return False
        return lines[0].startswith("Name:") and lines[1].startswith("MW:")


class SPLibNoIndex(Text):
    """SPlib without index file"""

    file_ext = "splib_noindex"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "Spectral Library without index files"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class SPLib(Msp):
    """SpectraST Spectral Library. Closely related to msp format"""

    file_ext = "splib"
    composite_type = "auto_primary_file"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "library.splib", description="Spectral Library. Contains actual library spectra", is_binary=False
        )
        self.add_composite_file("library.spidx", description="Spectrum index", is_binary=False)
        self.add_composite_file("library.pepidx", description="Peptide index", is_binary=False)

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head><title>Spectral Library Composite Dataset </title></head><p/>"]
        rval.append("<div>This composite dataset is composed of the following files:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ""
            if composite_file.optional:
                opt_text = " (optional)"
            if composite_file.get("description"):
                rval.append(
                    f"<li><a href=\"{fn}\" type=\"text/plain\">{fn} ({composite_file.get('description')})</a>{opt_text}</li>"
                )
            else:
                rval.append(f'<li><a href="{fn}" type="text/plain">{fn}</a>{opt_text}</li>')
        rval.append("</ul></div></html>")
        return "\n".join(rval)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = "splib Spectral Library Format"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file is a SpectraST generated file."""
        contents = file_prefix.string_io()
        return Msp.next_line_starts_with(contents, "Name:") and Msp.next_line_starts_with(contents, "LibID:")


@build_sniff_from_prefix
class Ms2(Text):
    file_ext = "ms2"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file is a valid ms2 file."""
        header_lines = []
        for line in file_prefix.line_iterator():
            if line.strip() == "":
                continue
            elif line.startswith("H\t"):
                header_lines.append(line)
            else:
                break

        for header_field in ["CreationDate", "Extractor", "ExtractorVersion", "ExtractorOptions"]:
            found_header = False
            for header_line in header_lines:
                if header_line.startswith(f"H\t{header_field}"):
                    found_header = True
                    break
            if not found_header:
                return False

        return True


# unsniffable binary format, should do something about this
class XHunterAslFormat(Binary):
    """Annotated Spectra in the HLF format http://www.thegpm.org/HUNTER/format_2006_09_15.html"""

    file_ext = "hlf"


class Sf3(Binary):
    """Class describing a Scaffold SF3 files"""

    file_ext = "sf3"


class ImzML(Binary):
    """
    Class for imzML files.
    http://www.imzml.org
    """

    edam_format = "format_3682"
    file_ext = "imzml"
    composite_type = "auto_primary_file"

    def __init__(self, **kwd):
        super().__init__(**kwd)

        self.add_composite_file("imzml", description="The imzML metadata component.", is_binary=False)

        self.add_composite_file("ibd", description="The mass spectral data component.", is_binary=True)

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head><title>imzML Composite Dataset </title></head><p/>"]
        rval.append("<div>This composite dataset is composed of the following files:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ""
            if composite_file.get("description"):
                rval.append(
                    f"<li><a href=\"{fn}\" type=\"text/plain\">{fn} ({composite_file.get('description')})</a>{opt_text}</li>"
                )
            else:
                rval.append(f'<li><a href="{fn}" type="text/plain">{fn}</a>{opt_text}</li>')
        rval.append("</ul></div></html>")
        return "\n".join(rval)
