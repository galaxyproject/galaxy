"""
Mothur Metagenomics Datatypes
"""
import logging
import re
import sys

from galaxy.datatypes.data import Text
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    get_headers,
    iter_headers,
)
from galaxy.datatypes.tabular import Tabular
from galaxy.util import unicodify

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class Otu(Text):
    file_ext = "mothur.otu"
    MetadataElement(name="columns", default=0, desc="Number of columns", readonly=True, visible=True, no_value=0)
    MetadataElement(name="labels", default=[], desc="Label Names", readonly=True, visible=True, no_value=[])
    MetadataElement(name="otulabels", default=[], desc="OTU Names", readonly=True, visible=True, no_value=[])

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def set_meta(self, dataset, overwrite=True, **kwd):
        """
        Set metadata for Otu files.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> from galaxy.util.bunch import Bunch
        >>> dataset = Bunch()
        >>> dataset.metadata = Bunch
        >>> otu = Otu()
        >>> dataset.file_name = get_test_fname( 'mothur_datatypetest_true.mothur.otu' )
        >>> dataset.has_data = lambda: True
        >>> otu.set_meta(dataset)
        >>> dataset.metadata.columns
        100
        >>> len(dataset.metadata.labels) == 37
        True
        >>> len(dataset.metadata.otulabels) == 98
        True
        """
        super().set_meta(dataset, overwrite=overwrite, **kwd)

        if dataset.has_data():
            label_names = set()
            otulabel_names = set()
            ncols = 0
            data_lines = 0
            comment_lines = 0

            headers = iter_headers(dataset.file_name, sep="\t", count=-1)
            first_line = get_headers(dataset.file_name, sep="\t", count=1)
            if first_line:
                first_line = first_line[0]
            # set otulabels
            if len(first_line) > 2:
                otulabel_names = first_line[2:]
            # set label names and number of lines
            for line in headers:
                if len(line) >= 2 and not line[0].startswith("@"):
                    data_lines += 1
                    ncols = max(ncols, len(line))
                    label_names.add(line[0])
                else:
                    comment_lines += 1
            # Set the discovered metadata values for the dataset
            dataset.metadata.data_lines = data_lines
            dataset.metadata.columns = ncols
            dataset.metadata.labels = sorted(label_names)
            dataset.metadata.otulabels = sorted(otulabel_names)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is otu (operational taxonomic unit) format

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.otu' )
        >>> Otu().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.otu' )
        >>> Otu().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        count = 0
        for line in headers:
            if not line[0].startswith("@"):
                if len(line) < 2:
                    return False
                if count >= 1:
                    try:
                        check = int(line[1])
                        if check + 2 != len(line):
                            return False
                    except ValueError:
                        return False
                count += 1
        if count > 2:
            return True

        return False


class Sabund(Otu):
    file_ext = "mothur.sabund"

    def __init__(self, **kwd):
        """
        http://www.mothur.org/wiki/Sabund_file
        """
        super().__init__(**kwd)

    def init_meta(self, dataset, copy_from=None):
        super().init_meta(dataset, copy_from=copy_from)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is otu (operational taxonomic unit) format
        label<TAB>count[<TAB>value(1..n)]

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.sabund' )
        >>> Sabund().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.sabund' )
        >>> Sabund().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        count = 0
        for line in headers:
            if not line[0].startswith("@"):
                if len(line) < 2:
                    return False
                try:
                    check = int(line[1])
                    if check + 2 != len(line):
                        return False
                    for i in range(2, len(line)):
                        int(line[i])
                except ValueError:
                    return False
                count += 1
        if count > 0:
            return True

        return False


class GroupAbund(Otu):
    file_ext = "mothur.shared"
    MetadataElement(name="groups", default=[], desc="Group Names", readonly=True, visible=True, no_value=[])

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def init_meta(self, dataset, copy_from=None):
        super().init_meta(dataset, copy_from=copy_from)

    def set_meta(self, dataset, overwrite=True, skip=1, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

        # See if file starts with header line
        if dataset.has_data():
            label_names = set()
            group_names = set()
            data_lines = 0
            comment_lines = 0
            ncols = 0

            headers = iter_headers(dataset.file_name, sep="\t", count=-1)
            for line in headers:
                if line[0] == "label" and line[1] == "Group":
                    skip = 1
                    comment_lines += 1
                else:
                    skip = 0
                    data_lines += 1
                    ncols = max(ncols, len(line))
                    label_names.add(line[0])
                    group_names.add(line[1])

            # Set the discovered metadata values for the dataset
            dataset.metadata.data_lines = data_lines
            dataset.metadata.columns = ncols
            dataset.metadata.labels = sorted(label_names)
            dataset.metadata.groups = sorted(group_names)
            dataset.metadata.skip = skip

    def sniff_prefix(self, file_prefix: FilePrefix, vals_are_int=False):
        """
        Determines whether the file is a otu (operational taxonomic unit)
        Shared format
        label<TAB>group<TAB>count[<TAB>value(1..n)]
        The first line is column headings as of Mothur v 1.2

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.shared' )
        >>> GroupAbund().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.shared' )
        >>> GroupAbund().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        count = 0
        for line in headers:
            if not line[0].startswith("@"):
                if len(line) < 3:
                    return False
                if count > 0 or line[0] != "label":
                    try:
                        check = int(line[2])
                        if check + 3 != len(line):
                            return False
                        for i in range(3, len(line)):
                            if vals_are_int:
                                int(line[i])
                            else:
                                float(line[i])
                    except ValueError:
                        return False
                count += 1
        if count > 1:
            return True
        return False


@build_sniff_from_prefix
class SecondaryStructureMap(Tabular):
    file_ext = "mothur.map"

    def __init__(self, **kwd):
        """Initialize secondary structure map datatype"""
        super().__init__(**kwd)
        self.column_names = ["Map"]

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is a secondary structure map format
        A single column with an integer value which indicates the row that this
        row maps to. Check to make sure if structMap[10] = 380 then
        structMap[380] = 10 and vice versa.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.map' )
        >>> SecondaryStructureMap().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.map' )
        >>> SecondaryStructureMap().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        line_num = 0
        rowidxmap = {}
        for line in headers:
            line_num += 1
            if len(line) > 1:
                return False
            try:
                pointer = int(line[0])
                if pointer > line_num:
                    rowidxmap[pointer] = line_num
                elif pointer > 0 or line_num in rowidxmap:
                    if rowidxmap[line_num] != pointer:
                        return False
            except (ValueError, KeyError):
                return False
        if line_num < 3:
            return False
        return True


class AlignCheck(Tabular):
    file_ext = "mothur.align.check"

    def __init__(self, **kwd):
        """Initialize AlignCheck datatype"""
        super().__init__(**kwd)
        self.column_names = ["name", "pound", "dash", "plus", "equal", "loop", "tilde", "total"]
        self.column_types = ["str", "int", "int", "int", "int", "int", "int", "int"]
        self.comment_lines = 1

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

        dataset.metadata.column_names = self.column_names
        dataset.metadata.column_types = self.column_types
        dataset.metadata.comment_lines = self.comment_lines
        if isinstance(dataset.metadata.data_lines, int):
            dataset.metadata.data_lines -= self.comment_lines


class AlignReport(Tabular):
    """
    QueryName	QueryLength	TemplateName	TemplateLength	SearchMethod	SearchScore	AlignmentMethod	QueryStart	QueryEnd	TemplateStart	TemplateEnd	PairwiseAlignmentLength	GapsInQuery	GapsInTemplate	LongestInsert	SimBtwnQuery&Template
    AY457915	501		82283		1525		kmer		89.07		needleman	5		501		1		499		499			2		0		0		97.6
    """

    file_ext = "mothur.align.report"

    def __init__(self, **kwd):
        """Initialize AlignCheck datatype"""
        super().__init__(**kwd)
        self.column_names = [
            "QueryName",
            "QueryLength",
            "TemplateName",
            "TemplateLength",
            "SearchMethod",
            "SearchScore",
            "AlignmentMethod",
            "QueryStart",
            "QueryEnd",
            "TemplateStart",
            "TemplateEnd",
            "PairwiseAlignmentLength",
            "GapsInQuery",
            "GapsInTemplate",
            "LongestInsert",
            "SimBtwnQuery&Template",
        ]


class DistanceMatrix(Text):
    file_ext = "mothur.dist"

    MetadataElement(
        name="sequence_count",
        default=0,
        desc="Number of sequences",
        readonly=True,
        visible=True,
        optional=True,
        no_value="?",
    )

    def init_meta(self, dataset, copy_from=None):
        super().init_meta(dataset, copy_from=copy_from)

    def set_meta(self, dataset, overwrite=True, skip=0, **kwd):
        super().set_meta(dataset, overwrite=overwrite, skip=skip, **kwd)

        headers = iter_headers(dataset.file_name, sep="\t")
        for line in headers:
            if not line[0].startswith("@"):
                try:
                    dataset.metadata.sequence_count = int("".join(line))  # seq count sometimes preceded by tab
                    break
                except Exception as e:
                    if not isinstance(self, PairwiseDistanceMatrix):
                        log.warning(f"DistanceMatrix set_meta {e}")


@build_sniff_from_prefix
class LowerTriangleDistanceMatrix(DistanceMatrix):
    file_ext = "mothur.lower.dist"

    def __init__(self, **kwd):
        """Initialize secondary structure map datatype"""
        super().__init__(**kwd)

    def init_meta(self, dataset, copy_from=None):
        super().init_meta(dataset, copy_from=copy_from)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is a lower-triangle distance matrix (phylip) format
        The first line has the number of sequences in the matrix.
        The remaining lines have the sequence name followed by a list of distances from all preceeding sequences

                5  # possibly but not always preceded by a tab :/
                U68589
                U68590	0.3371
                U68591	0.3609	0.3782
                U68592	0.4155	0.3197	0.4148
                U68593	0.2872	0.1690	0.3361	0.2842

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.lower.dist' )
        >>> LowerTriangleDistanceMatrix().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.lower.dist' )
        >>> LowerTriangleDistanceMatrix().sniff( fname )
        False
        """
        numlines = 300
        headers = iter_headers(file_prefix, sep="\t", count=numlines)
        line_num = 0
        for line in headers:
            if not line[0].startswith("@"):
                # first line should contain the number of sequences in the file
                if line_num == 0:
                    if len(line) > 2:
                        return False
                    else:
                        try:
                            sequence_count = int("".join(line))
                            assert sequence_count > 0
                        except ValueError:
                            return False
                else:
                    # number of fields should equal the line number
                    if len(line) != (line_num):
                        return False
                    try:
                        # Distances should be floats
                        for column in line[2:]:
                            float(column)
                    except ValueError:
                        return False
                line_num += 1

        # check if the number of lines in the file was as expected
        if line_num == sequence_count + 1 or line_num == numlines + 1:
            return True

        return False


@build_sniff_from_prefix
class SquareDistanceMatrix(DistanceMatrix):
    file_ext = "mothur.square.dist"

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def init_meta(self, dataset, copy_from=None):
        super().init_meta(dataset, copy_from=copy_from)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is a square distance matrix (Column-formatted distance matrix) format
        The first line has the number of sequences in the matrix.
        The following lines have the sequence name in the first column plus a column for the distance to each sequence
        in the row order in which they appear in the matrix.

               3
               U68589  0.0000  0.3371  0.3610
               U68590  0.3371  0.0000  0.3783
               U68590  0.3371  0.0000  0.3783

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.square.dist' )
        >>> SquareDistanceMatrix().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.square.dist' )
        >>> SquareDistanceMatrix().sniff( fname )
        False
        """
        numlines = 300
        headers = iter_headers(file_prefix, sep="\t", count=numlines)
        line_num = 0
        for line in headers:
            if not line[0].startswith("@"):
                if line_num == 0:
                    if len(line) > 2:
                        return False
                    else:
                        try:
                            sequence_count = int("".join(line))
                            assert sequence_count > 0
                        except ValueError:
                            return False
                else:
                    # number of fields should equal the number of sequences
                    if len(line) != sequence_count + 1:
                        return False
                    try:
                        # Distances should be floats
                        for column in line[2:]:
                            float(column)
                    except ValueError:
                        return False
                line_num += 1

        # check if the number of lines in the file was as expected
        if line_num == sequence_count + 1 or line_num == numlines + 1:
            return True

        return False


@build_sniff_from_prefix
class PairwiseDistanceMatrix(DistanceMatrix, Tabular):
    file_ext = "mothur.pair.dist"

    def __init__(self, **kwd):
        """Initialize secondary structure map datatype"""
        super().__init__(**kwd)
        self.column_names = ["Sequence", "Sequence", "Distance"]
        self.column_types = ["str", "str", "float"]

    def set_meta(self, dataset, overwrite=True, skip=None, **kwd):
        super().set_meta(dataset, overwrite=overwrite, skip=skip, **kwd)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is a pairwise distance matrix (Column-formatted distance matrix) format
        The first and second columns have the sequence names and the third column is the distance between those sequences.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.pair.dist' )
        >>> PairwiseDistanceMatrix().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.pair.dist' )
        >>> PairwiseDistanceMatrix().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        count = 0
        names = [False, False]
        for line in headers:
            if line[0].startswith("@"):
                continue
            if len(line) != 3:
                return False
            # check if col3 contains distances (floats)
            try:
                float(line[2])
                try:
                    # See if it's also an integer
                    int(line[2])
                except ValueError:
                    # At least one value is not an integer
                    all_ints = False
            except ValueError:
                return False
            count += 1
            # check if col1 and col2 likely contain names
            for c in [0, 1]:
                try:
                    float(line[c])
                except ValueError:
                    names[c] = True

        if not names[0] or not names[1]:
            return False

        if count > 2:
            return not all_ints

        return False


class Names(Tabular):
    file_ext = "mothur.names"

    def __init__(self, **kwd):
        """
        http://www.mothur.org/wiki/Name_file
        Name file shows the relationship between a representative sequence(col 1)  and the sequences(comma-separated) it represents(col 2)
        """
        super().__init__(**kwd)
        self.column_names = ["name", "representatives"]
        self.columns = 2


class Summary(Tabular):
    file_ext = "mothur.summary"

    def __init__(self, **kwd):
        """summarizes the quality of sequences in an unaligned or aligned fasta-formatted sequence file"""
        super().__init__(**kwd)
        self.column_names = ["seqname", "start", "end", "nbases", "ambigs", "polymer"]
        self.columns = 6


class Group(Tabular):
    file_ext = "mothur.groups"
    MetadataElement(name="groups", default=[], desc="Group Names", readonly=True, visible=True, no_value=[])

    def __init__(self, **kwd):
        """
        http://www.mothur.org/wiki/Groups_file
        Group file assigns sequence (col 1)  to a group (col 2)
        """
        super().__init__(**kwd)
        self.column_names = ["name", "group"]
        self.columns = 2

    def set_meta(self, dataset, overwrite=True, skip=None, max_data_lines=None, **kwd):
        super().set_meta(dataset, overwrite, skip, max_data_lines)

        group_names = set()
        headers = iter_headers(dataset.file_name, sep="\t", count=-1)
        for line in headers:
            if len(line) > 1:
                group_names.add(line[1])
        dataset.metadata.groups = list(group_names)


class AccNos(Tabular):
    file_ext = "mothur.accnos"

    def __init__(self, **kwd):
        """A list of names"""
        super().__init__(**kwd)
        self.column_names = ["name"]
        self.columns = 1


@build_sniff_from_prefix
class Oligos(Text):
    file_ext = "mothur.oligos"

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        http://www.mothur.org/wiki/Oligos_File
        Determines whether the file is a otu (operational taxonomic unit) format

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.oligos' )
        >>> Oligos().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.oligos' )
        >>> Oligos().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        count = 0
        for line in headers:
            if not line[0].startswith("@") and not line[0].startswith("#"):
                if len(line) == 2 and line[0] in ["forward", "reverse"]:
                    count += 1
                    continue
                elif len(line) == 3 and line[0] == "barcode":
                    count += 1
                    continue
                else:
                    return False
        if count > 0:
            return True

        return False


@build_sniff_from_prefix
class Frequency(Tabular):
    file_ext = "mothur.freq"

    def __init__(self, **kwd):
        """A list of names"""
        super().__init__(**kwd)
        self.column_names = ["position", "frequency"]
        self.column_types = ["int", "float"]

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is a frequency tabular format for chimera analysis

        .. code-block::

            #1.14.0
            0	0.000
            1	0.000
            ...
            155	0.975

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.freq' )
        >>> Frequency().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.freq' )
        >>> Frequency().sniff( fname )
        False
        >>> # Expression count matrix (EdgeR wrapper)
        >>> fname = get_test_fname( 'mothur_datatypetest_false_2.mothur.freq' )
        >>> Frequency().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        count = 0
        for line in headers:
            if not line[0].startswith("@"):
                # first line should be #<version string>
                if count == 0:
                    if not line[0].startswith("#") or len(line) != 1:
                        return False

                else:
                    # all other lines should be <int> <float>
                    if len(line) != 2:
                        return False
                    try:
                        int(line[0])
                        float(line[1])

                        if line[1].find(".") == -1:
                            return False
                    except Exception:
                        return False
                count += 1

        if count > 1:
            return True

        return False


@build_sniff_from_prefix
class Quantile(Tabular):
    file_ext = "mothur.quan"
    MetadataElement(
        name="filtered",
        default=False,
        no_value=False,
        optional=True,
        desc="Quantiles calculated using a mask",
        readonly=True,
    )
    MetadataElement(
        name="masked",
        default=False,
        no_value=False,
        optional=True,
        desc="Quantiles calculated using a frequency filter",
        readonly=True,
    )

    def __init__(self, **kwd):
        """Quantiles for chimera analysis"""
        super().__init__(**kwd)
        self.column_names = ["num", "ten", "twentyfive", "fifty", "seventyfive", "ninetyfive", "ninetynine"]
        self.column_types = ["int", "float", "float", "float", "float", "float", "float"]

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is a quantiles tabular format for chimera analysis

        .. code-block::

            1	0	0	0	0	0	0
            2       0.309198        0.309198        0.37161 0.37161 0.37161 0.37161
            3       0.510982        0.563213        0.693529        0.858939        1.07442 1.20608
            ...

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.quan' )
        >>> Quantile().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.quan' )
        >>> Quantile().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        count = 0
        for line in headers:
            if not line[0].startswith("@") and not line[0].startswith("#"):
                if len(line) != 7:
                    return False
                try:
                    int(line[0])
                    float(line[1])
                    float(line[2])
                    float(line[3])
                    float(line[4])
                    float(line[5])
                    float(line[6])
                except Exception:
                    return False
                count += 1
        if count > 0:
            return True

        return False


@build_sniff_from_prefix
class LaneMask(Text):
    file_ext = "mothur.filter"

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is a lane mask filter:  1 line consisting of zeros and ones.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.filter' )
        >>> LaneMask().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.filter' )
        >>> LaneMask().sniff( fname )
        False
        """
        headers = get_headers(file_prefix, sep="\t", count=2)
        if len(headers) != 1 or len(headers[0]) != 1:
            return False

        if len(headers[0][0]) < 1000:
            # these filter files should be relatively big
            return False

        if not re.match("^[01]+$", headers[0][0]):
            return False

        return True


class CountTable(Tabular):
    MetadataElement(name="groups", default=[], desc="Group Names", readonly=True, visible=True, no_value=[])
    file_ext = "mothur.count_table"

    def __init__(self, **kwd):
        """
        http://www.mothur.org/wiki/Count_File
        A table with first column names and following columns integer counts
        # Example 1:
        Representative_Sequence total
        U68630  1
        U68595  1
        U68600  1
        # Example 2 (with group columns):
        Representative_Sequence total   forest  pasture
        U68630  1       1       0
        U68595  1       1       0
        U68600  1       1       0
        U68591  1       1       0
        U68647  1       0       1
        """
        super().__init__(**kwd)
        self.column_names = ["name", "total"]

    def set_meta(self, dataset, overwrite=True, skip=1, max_data_lines=None, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

        headers = get_headers(dataset.file_name, sep="\t", count=1)
        colnames = headers[0]
        dataset.metadata.column_types = ["str"] + (["int"] * (len(headers[0]) - 1))
        if len(colnames) > 1:
            dataset.metadata.columns = len(colnames)
        if len(colnames) > 2:
            dataset.metadata.groups = colnames[2:]

        dataset.metadata.comment_lines = 1
        if isinstance(dataset.metadata.data_lines, int):
            dataset.metadata.data_lines -= 1


@build_sniff_from_prefix
class RefTaxonomy(Tabular):
    file_ext = "mothur.ref.taxonomy"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.column_names = ["name", "taxonomy"]

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is a Reference Taxonomy

        http://www.mothur.org/wiki/Taxonomy_outline
        A table with 2 or 3 columns:

        - SequenceName
        - Taxonomy (semicolon-separated taxonomy in descending order)
        - integer ?

        Example: 2-column (http://www.mothur.org/wiki/Taxonomy_outline)

        .. code-block::

            X56533.1        Eukaryota;Alveolata;Ciliophora;Intramacronucleata;Oligohymenophorea;Hymenostomatida;Tetrahymenina;Glaucomidae;Glaucoma;
            X97975.1        Eukaryota;Parabasalidea;Trichomonada;Trichomonadida;unclassified_Trichomonadida;
            AF052717.1      Eukaryota;Parabasalidea;

        Example: 3-column (http://vamps.mbl.edu/resources/databases.php)

        .. code-block::

            v3_AA008	Bacteria;Firmicutes;Bacilli;Lactobacillales;Streptococcaceae;Streptococcus	5
            v3_AA016	Bacteria	120
            v3_AA019	Archaea;Crenarchaeota;Marine_Group_I	1

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.ref.taxonomy' )
        >>> RefTaxonomy().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.ref.taxonomy' )
        >>> RefTaxonomy().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t", count=300)
        count = 0
        pat_prog = re.compile("^([^ \t\n\r\x0c\x0b;]+([(]\\d+[)])?(;[^ \t\n\r\x0c\x0b;]+([(]\\d+[)])?)*(;)?)$")
        found_semicolons = False
        for line in headers:
            if not line[0].startswith("@") and not line[0].startswith("#"):
                if not (2 <= len(line) <= 3):
                    return False
                if not pat_prog.match(line[1]):
                    return False
                if not found_semicolons and line[1].find(";") > -1:
                    found_semicolons = True
                if len(line) == 3:
                    try:
                        int(line[2])
                    except Exception:
                        return False
                count += 1

        if count > 0:
            # Require that at least one entry has semicolons in the 2nd column
            return found_semicolons

        return False


class ConsensusTaxonomy(Tabular):
    file_ext = "mothur.cons.taxonomy"

    def __init__(self, **kwd):
        """A list of names"""
        super().__init__(**kwd)
        self.column_names = ["OTU", "count", "taxonomy"]


class TaxonomySummary(Tabular):
    file_ext = "mothur.tax.summary"

    def __init__(self, **kwd):
        """A Summary of taxon classification"""
        super().__init__(**kwd)
        self.column_names = ["taxlevel", "rankID", "taxon", "daughterlevels", "total"]


@build_sniff_from_prefix
class Axes(Tabular):
    file_ext = "mothur.axes"

    def __init__(self, **kwd):
        """Initialize axes datatype"""
        super().__init__(**kwd)

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        Determines whether the file is an axes format
        The first line may have column headings.
        The following lines have the name in the first column plus float columns for each axis.

        .. code-block::

            group   axis1   axis2
            forest  0.000000        0.145743
            pasture 0.145743        0.000000

        .. code-block::

                    axis1   axis2
            U68589  0.262608        -0.077498
            U68590  0.027118        0.195197
            U68591  0.329854        0.014395

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.axes' )
        >>> Axes().sniff( fname )
        True
        >>> fname = get_test_fname( 'mothur_datatypetest_false.mothur.axes' )
        >>> Axes().sniff( fname )
        False
        """
        headers = iter_headers(file_prefix, sep="\t")
        count = 0
        col_cnt = None
        all_integers = True
        for line in headers:
            if count != 0:
                if col_cnt is None:
                    col_cnt = len(line)
                    if col_cnt < 2:
                        return False
                else:
                    if len(line) != col_cnt:
                        return False
                    try:
                        for i in range(1, col_cnt):
                            check = float(line[i])
                            # Check abs value is <= 1.0
                            if abs(check) > 1.0:
                                return False
                            # Also test for whether value is an integer
                            try:
                                check = int(line[i])
                            except ValueError:
                                all_integers = False
                    except ValueError:
                        return False
            count += 1

        if count > 0:
            return not all_integers

        return False


class SffFlow(Tabular):
    """
    https://mothur.org/wiki/flow_file/
    The first line is the total number of flow values - 800 for Titanium data. For GS FLX it would be 400.
    Following lines contain:

    - SequenceName
    - the number of useable flows as defined by 454's software
    - the flow intensity for each base going in the order of TACG.

    Example:

    .. code-block::

        800
        GQY1XT001CQL4K 85 1.04 0.00 1.00 0.02 0.03 1.02 0.05 ...
        GQY1XT001CQIRF 84 1.02 0.06 0.98 0.06 0.09 1.05 0.07 ...
        GQY1XT001CF5YW 88 1.02 0.02 1.01 0.04 0.06 1.02 0.03 ...

    """

    file_ext = "mothur.sff.flow"

    MetadataElement(
        name="flow_values", default="", no_value="", optional=True, desc="Total number of flow values", readonly=True
    )
    MetadataElement(
        name="flow_order", default="TACG", no_value="TACG", desc="Total number of flow values", readonly=False
    )

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def set_meta(self, dataset, overwrite=True, skip=1, max_data_lines=None, **kwd):
        super().set_meta(dataset, overwrite, 1, max_data_lines)

        headers = get_headers(dataset.file_name, sep="\t", count=1)
        try:
            flow_values = int(headers[0][0])
            dataset.metadata.flow_values = flow_values
        except Exception as e:
            log.warning(f"SffFlow set_meta {e}")

    def make_html_table(self, dataset, skipchars=None):
        """Create HTML table, used for displaying peek"""
        if skipchars is None:
            skipchars = []
        try:
            out = '<table cellspacing="0" cellpadding="3">'

            # Generate column header
            out += "<tr>"
            out += "<th>1. Name</th>"
            out += "<th>2. Flows</th>"
            for i in range(3, dataset.metadata.columns + 1):
                base = dataset.metadata.flow_order[(i + 1) % 4]
                out += "<th>%d. %s</th>" % (i - 2, base)
            out += "</tr>"
            out += self.make_html_peek_rows(dataset, skipchars=skipchars)
            out += "</table>"
        except Exception as exc:
            out = f"Can't create peek: {unicodify(exc)}"
        return out


if __name__ == "__main__":
    import doctest

    doctest.testmod(sys.modules[__name__])
