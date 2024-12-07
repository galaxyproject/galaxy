"""
Tabular datatype
"""

import abc
import binascii
import csv
import logging
import os
import re
import shutil
import subprocess
import tempfile
from json import dumps
from typing import (
    cast,
    Dict,
    List,
    Optional,
    Union,
)

import pysam
from markupsafe import escape

from galaxy import util
from galaxy.datatypes import (
    binary,
    data,
    metadata,
)
from galaxy.datatypes.binary import _BamOrSam
from galaxy.datatypes.data import (
    DatatypeValidation,
    Text,
)
from galaxy.datatypes.dataproviders.column import (
    ColumnarDataProvider,
    DictDataProvider,
)
from galaxy.datatypes.dataproviders.dataset import (
    DatasetColumnarDataProvider,
    DatasetDataProvider,
    DatasetDictDataProvider,
    GenomicRegionDataProvider,
)
from galaxy.datatypes.dataproviders.line import (
    FilteredLineDataProvider,
    RegexLineDataProvider,
)
from galaxy.datatypes.metadata import (
    MetadataElement,
    MetadataParameter,
)
from galaxy.datatypes.protocols import (
    DatasetHasHidProtocol,
    DatasetProtocol,
    HasFileName,
    HasMetadata,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    get_headers,
    iter_headers,
    validate_tabular,
)
from galaxy.exceptions import InvalidFileFormatError
from galaxy.util import compression_utils
from galaxy.util.compression_utils import (
    FileObjType,
    FileObjTypeStr,
)
from galaxy.util.markdown import (
    indicate_data_truncated,
    pre_formatted_contents,
)
from . import dataproviders

log = logging.getLogger(__name__)

MAX_DATA_LINES = 100000


@dataproviders.decorators.has_dataproviders
class TabularData(Text):
    """Generic tabular data"""

    edam_format = "format_3475"
    # All tabular data is chunkable.
    CHUNKABLE = True
    data_line_offset = 0
    max_peek_columns = 50

    MetadataElement(
        name="comment_lines", default=0, desc="Number of comment lines", readonly=False, optional=True, no_value=0
    )
    MetadataElement(
        name="data_lines",
        default=0,
        desc="Number of data lines",
        readonly=True,
        visible=False,
        optional=True,
        no_value=0,
    )
    MetadataElement(name="columns", default=0, desc="Number of columns", readonly=True, visible=False, no_value=0)
    MetadataElement(
        name="column_types",
        default=[],
        desc="Column types",
        param=metadata.ColumnTypesParameter,
        readonly=True,
        visible=False,
        no_value=[],
    )
    MetadataElement(
        name="column_names", default=[], desc="Column names", readonly=True, visible=False, optional=True, no_value=[]
    )
    MetadataElement(
        name="delimiter", default="\t", desc="Data delimiter", readonly=True, visible=False, optional=True, no_value=[]
    )

    @abc.abstractmethod
    def set_meta(self, dataset: DatasetProtocol, *, overwrite: bool = True, **kwd) -> None:
        raise NotImplementedError

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        kwd.setdefault("line_wrap", False)
        super().set_peek(dataset, **kwd)
        dataset.blurb = f"{dataset.blurb} {dataset.metadata.columns} columns"
        if dataset.metadata.comment_lines:
            dataset.blurb = f"{dataset.blurb}, {util.commaify(str(dataset.metadata.comment_lines))} comments"

    def displayable(self, dataset: DatasetProtocol) -> bool:
        try:
            return (
                not dataset.deleted
                and not dataset.dataset.purged
                and dataset.has_data()
                and dataset.state == dataset.states.OK
                and dataset.metadata.columns > 0
                and dataset.metadata.data_lines != 0
            )
        except Exception:
            return False

    def get_chunk(self, trans, dataset: HasFileName, offset: int = 0, ck_size: Optional[int] = None) -> str:
        ck_data, last_read = self._read_chunk(trans, dataset, offset, ck_size)
        return dumps(
            {
                "ck_data": util.unicodify(ck_data),
                "offset": last_read,
                "data_line_offset": self.data_line_offset,
            }
        )

    def _read_chunk(self, trans, dataset: HasFileName, offset: int, ck_size: Optional[int] = None):
        with compression_utils.get_fileobj(dataset.get_file_name()) as f:
            f.seek(offset)
            try:
                ck_data = f.read(ck_size or trans.app.config.display_chunk_size)
                if ck_data and ck_data[-1] != "\n":
                    cursor = f.read(1)
                    while cursor and cursor != "\n":
                        ck_data += cursor
                        cursor = f.read(1)
            except UnicodeDecodeError:
                raise InvalidFileFormatError("Dataset appears to contain binary data, cannot display.")
            last_read = f.tell()
        return ck_data, last_read

    def display_data(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        offset: Optional[int] = None,
        ck_size: Optional[int] = None,
        **kwd,
    ):
        headers = kwd.pop("headers", {})
        preview = util.string_as_bool(preview)
        if offset is not None:
            return self.get_chunk(trans, dataset, offset, ck_size), headers
        elif to_ext or not preview:
            to_ext = to_ext or dataset.extension
            return self._serve_raw(dataset, to_ext, headers, **kwd)
        elif dataset.metadata.columns > 100:
            # Fancy tabular display is only suitable for datasets without an incredibly large number of columns.
            # We should add a new datatype 'matrix', with its own draw method, suitable for this kind of data.
            # For now, default to the old behavior, ugly as it is.  Remove this after adding 'matrix'.
            max_peek_size = 1000000  # 1 MB
            if os.stat(dataset.get_file_name()).st_size < max_peek_size:
                self._clean_and_set_mime_type(trans, dataset.get_mime(), headers)
                return open(dataset.get_file_name(), mode="rb"), headers
            else:
                headers["content-type"] = "text/html"
                with compression_utils.get_fileobj(dataset.get_file_name(), "rb") as fh:
                    return (
                        trans.fill_template_mako(
                            "/dataset/large_file.mako",
                            truncated_data=fh.read(max_peek_size),
                            data=dataset,
                        ),
                        headers,
                    )
        else:
            column_names = "null"
            if dataset.metadata.column_names:
                column_names = dataset.metadata.column_names
            elif hasattr(dataset.datatype, "column_names"):
                column_names = dataset.datatype.column_names
            column_types = dataset.metadata.column_types
            if not column_types:
                column_types = []
            column_number = dataset.metadata.columns
            if column_number is None:
                column_number = "null"
            return (
                trans.fill_template(
                    "/dataset/tabular_chunked.mako",
                    dataset=dataset,
                    chunk=self.get_chunk(trans, dataset, 0),
                    column_number=column_number,
                    column_names=column_names,
                    column_types=column_types,
                ),
                headers,
            )

    def display_as_markdown(self, dataset_instance: DatasetProtocol) -> str:
        with open(dataset_instance.get_file_name()) as f:
            contents = f.read(data.DEFAULT_MAX_PEEK_SIZE)
        markdown = self.make_html_table(dataset_instance, peek=contents)
        if len(contents) == data.DEFAULT_MAX_PEEK_SIZE:
            markdown += indicate_data_truncated()
        return pre_formatted_contents(markdown)

    def make_html_table(self, dataset: DatasetProtocol, **kwargs) -> str:
        """Create HTML table, used for displaying peek"""
        try:
            out = ['<table cellspacing="0" cellpadding="3">']
            out.append(self.make_html_peek_header(dataset, **kwargs))
            out.append(self.make_html_peek_rows(dataset, **kwargs))
            out.append("</table>")
            return "".join(out)
        except Exception as exc:
            return f"Can't create peek: {util.unicodify(exc)}"

    def make_html_peek_header(
        self,
        dataset: DatasetProtocol,
        skipchars: Optional[List] = None,
        column_names: Optional[List] = None,
        column_number_format: str = "%s",
        column_parameter_alias: Optional[Dict] = None,
        **kwargs,
    ) -> str:
        if skipchars is None:
            skipchars = []
        if column_names is None:
            column_names = []
        if column_parameter_alias is None:
            column_parameter_alias = {}
        out = []
        try:
            if not column_names and dataset.metadata.column_names:
                column_names = dataset.metadata.column_names

            columns = dataset.metadata.columns
            if columns is None:
                columns = dataset.metadata.spec.columns.no_value
            columns = min(columns, self.max_peek_columns)
            column_headers = [None] * columns

            # fill in empty headers with data from column_names
            assert column_names is not None
            for i in range(min(columns, len(column_names))):
                if column_headers[i] is None and column_names[i] is not None:
                    column_headers[i] = column_names[i]

            # fill in empty headers from ColumnParameters set in the metadata
            for name, spec in dataset.metadata.spec.items():
                if isinstance(spec.param, metadata.ColumnParameter):
                    try:
                        i = int(getattr(dataset.metadata, name)) - 1
                    except Exception:
                        i = -1
                    if 0 <= i < columns and column_headers[i] is None:
                        column_headers[i] = column_parameter_alias.get(name, name)

            out.append("<tr>")
            for i, header in enumerate(column_headers):
                out.append("<th>")
                if header is None:
                    out.append(column_number_format % str(i + 1))
                else:
                    out.append(f"{str(i + 1)}.{escape(header)}")
                out.append("</th>")
            out.append("</tr>")
        except Exception as exc:
            log.exception("make_html_peek_header failed on HDA %s", dataset.id)
            raise Exception(f"Can't create peek header: {util.unicodify(exc)}")
        return "".join(out)

    def make_html_peek_rows(self, dataset: DatasetProtocol, skipchars: Optional[List] = None, **kwargs) -> str:
        if skipchars is None:
            skipchars = []
        out = []
        try:
            peek = kwargs.get("peek")
            if peek is None:
                if not dataset.peek:
                    dataset.set_peek()
                peek = dataset.peek
            columns = dataset.metadata.columns
            if columns is None:
                columns = dataset.metadata.spec.columns.no_value
            columns = min(columns, self.max_peek_columns)
            for i, line in enumerate(peek.splitlines()):
                if i >= self.data_line_offset:
                    if line.startswith(tuple(skipchars)):
                        out.append(f'<tr><td colspan="100%">{escape(line)}</td></tr>')
                    elif line:
                        elems = line.split(dataset.metadata.delimiter)
                        elems = elems[: min(len(elems), self.max_peek_columns)]
                        # pad shortened elems, since lines could have been truncated by width
                        if len(elems) < columns:
                            elems.extend([""] * (columns - len(elems)))
                        # we may have an invalid comment line or invalid data
                        if len(elems) != columns:
                            out.append(f'<tr><td colspan="100%">{escape(line)}</td></tr>')
                        else:
                            out.append("<tr>")
                            for elem in elems:
                                out.append(f"<td>{escape(elem)}</td>")
                            out.append("</tr>")
        except Exception as exc:
            log.exception("make_html_peek_rows failed on HDA %s", dataset.id)
            raise Exception(f"Can't create peek rows: {util.unicodify(exc)}")
        return "".join(out)

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formatted html of peek"""
        return self.make_html_table(dataset)

    def is_int(self, column_text: str) -> bool:
        # Don't allow underscores in numeric literals (PEP 515)
        if "_" in column_text:
            return False
        try:
            int(column_text)
            return True
        except ValueError:
            return False

    def is_float(self, column_text: str) -> bool:
        # Don't allow underscores in numeric literals (PEP 515)
        if "_" in column_text:
            return False
        try:
            float(column_text)
            return True
        except ValueError:
            if column_text.strip().lower() == "na":
                return True  # na is special cased to be a float
            return False

    def guess_type(self, text: str) -> str:
        if self.is_int(text):
            return "int"
        if self.is_float(text):
            return "float"
        else:
            return "str"

    # ------------- Dataproviders
    @dataproviders.decorators.dataprovider_factory("column", ColumnarDataProvider.settings)
    def column_dataprovider(self, dataset: DatasetProtocol, **settings) -> ColumnarDataProvider:
        """Uses column settings that are passed in"""
        dataset_source = DatasetDataProvider(dataset)
        delimiter = dataset.metadata.delimiter
        return ColumnarDataProvider(dataset_source, deliminator=delimiter, **settings)

    @dataproviders.decorators.dataprovider_factory("dataset-column", ColumnarDataProvider.settings)
    def dataset_column_dataprovider(self, dataset: DatasetProtocol, **settings) -> DatasetColumnarDataProvider:
        """Attempts to get column settings from dataset.metadata"""
        delimiter = dataset.metadata.delimiter
        return DatasetColumnarDataProvider(dataset, deliminator=delimiter, **settings)

    @dataproviders.decorators.dataprovider_factory("dict", DictDataProvider.settings)
    def dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> DictDataProvider:
        """Uses column settings that are passed in"""
        dataset_source = DatasetDataProvider(dataset)
        delimiter = dataset.metadata.delimiter
        return DictDataProvider(dataset_source, deliminator=delimiter, **settings)

    @dataproviders.decorators.dataprovider_factory("dataset-dict", DictDataProvider.settings)
    def dataset_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> DatasetDictDataProvider:
        """Attempts to get column settings from dataset.metadata"""
        delimiter = dataset.metadata.delimiter
        return DatasetDictDataProvider(dataset, deliminator=delimiter, **settings)


@dataproviders.decorators.has_dataproviders
class Tabular(TabularData):
    """Tab delimited data"""

    file_ext = "tabular"

    def get_column_names(self, first_line: str) -> Optional[List[str]]:
        return None

    def set_meta(
        self,
        dataset: DatasetProtocol,
        *,
        overwrite: bool = True,
        skip: Optional[int] = None,
        max_data_lines: Optional[int] = MAX_DATA_LINES,
        max_guess_type_data_lines: Optional[int] = None,
        **kwd,
    ) -> None:
        """
        Tries to determine the number of columns as well as those columns that
        contain numerical values in the dataset.  A skip parameter is used
        because various tabular data types reuse this function, and their data
        type classes are responsible to determine how many invalid comment
        lines should be skipped. Using None for skip will cause skip to be
        zero, but the first line will be processed as a header. A
        max_data_lines parameter is used because various tabular data types
        reuse this function, and their data type classes are responsible to
        determine how many data lines should be processed to ensure that the
        non-optional metadata parameters are properly set; if used, optional
        metadata parameters will be set to None, unless the entire file has
        already been read. Using None for max_data_lines will process all data
        lines.

        Items of interest:

        1. We treat 'overwrite' as always True (we always want to set tabular metadata when called).
        2. If a tabular file has no data, it will have one column of type 'str'.
        3. We used to check only the first 100 lines when setting metadata and this class's
           set_peek() method read the entire file to determine the number of lines in the file.
           Since metadata can now be processed on cluster nodes, we've merged the line count portion
           of the set_peek() processing here, and we now check the entire contents of the file.
        """
        # Store original skip value to check with later
        requested_skip = skip
        if skip is None:
            skip = 0
        column_type_set_order = ["int", "float", "list", "str"]  # Order to set column types in
        default_column_type = column_type_set_order[-1]  # Default column type is lowest in list
        column_type_compare_order = list(column_type_set_order)  # Order to compare column types
        column_type_compare_order.reverse()

        def type_overrules_type(new_column_type, old_column_type):
            if new_column_type is None or new_column_type == old_column_type:
                return False
            if old_column_type is None:
                return True
            for column_type in column_type_compare_order:
                if new_column_type == column_type:
                    return True
                if old_column_type == column_type:
                    return False
            # neither column type was found in our ordered list, this cannot happen
            raise ValueError(f"Tried to compare unknown column types: {new_column_type} and {old_column_type}")

        def is_int(column_text):
            # Don't allow underscores in numeric literals (PEP 515)
            if "_" in column_text:
                return False
            try:
                int(column_text)
                return True
            except ValueError:
                return False

        def is_float(column_text):
            # Don't allow underscores in numeric literals (PEP 515)
            if "_" in column_text:
                return False
            try:
                float(column_text)
                return True
            except ValueError:
                if column_text.strip().lower() == "na":
                    return True  # na is special cased to be a float
                return False

        def is_list(column_text):
            return "," in column_text

        def is_str(column_text):
            # anything, except an empty string, is True
            if column_text == "":
                return False
            return True

        is_column_type = {}  # Dict to store column type string to checking function
        for column_type in column_type_set_order:
            is_column_type[column_type] = locals()[f"is_{column_type}"]

        def guess_column_type(column_text):
            for column_type in column_type_set_order:
                if is_column_type[column_type](column_text):
                    return column_type
            return None

        data_lines = 0
        comment_lines = 0
        column_names = None
        column_types: List = []
        first_line_column_types = []
        if dataset.has_data():
            # NOTE: if skip > num_check_lines, we won't detect any metadata, and will use default
            with compression_utils.get_fileobj(dataset.get_file_name()) as dataset_fh:
                i = 0
                for line in iter(dataset_fh.readline, ""):
                    line = line.rstrip("\r\n")
                    if i == 0:
                        column_names = self.get_column_names(first_line=line)
                    if i < skip or not line or line.startswith("#"):
                        # We'll call blank lines comments
                        comment_lines += 1
                    else:
                        data_lines += 1
                        if max_guess_type_data_lines is None or data_lines <= max_guess_type_data_lines:
                            fields = line.split("\t")
                            for field_count, field in enumerate(fields):
                                if field_count >= len(
                                    column_types
                                ):  # found a previously unknown column, we append None
                                    column_types.append(None)
                                column_type = guess_column_type(field)
                                if type_overrules_type(column_type, column_types[field_count]):
                                    column_types[field_count] = column_type
                        if i == 0 and requested_skip is None:
                            # This is our first line, people seem to like to upload files that have a header line, but do not
                            # start with '#' (i.e. all column types would then most likely be detected as str).  We will assume
                            # that the first line is always a header (this was previous behavior - it was always skipped).  When
                            # the requested skip is None, we only use the data from the first line if we have no other data for
                            # a column.  This is far from perfect, as
                            # 1,2,3	1.1	2.2	qwerty
                            # 0	0		1,2,3
                            # will be detected as
                            # "column_types": ["int", "int", "float", "list"]
                            # instead of
                            # "column_types": ["list", "float", "float", "str"]  *** would seem to be the 'Truth' by manual
                            # observation that the first line should be included as data.  The old method would have detected as
                            # "column_types": ["int", "int", "str", "list"]
                            first_line_column_types = column_types
                            column_types = [None for col in first_line_column_types]
                    if max_data_lines is not None and data_lines >= max_data_lines:
                        if dataset_fh.tell() != dataset.get_size():
                            # Clear optional data_lines metadata value
                            data_lines = None  # type: ignore [assignment]
                            # Clear optional comment_lines metadata value; additional comment lines could appear below this point
                            comment_lines = None  # type: ignore [assignment]
                        break
                    i += 1

        # we error on the larger number of columns
        # first we pad our column_types by using data from first line
        if len(first_line_column_types) > len(column_types):
            for column_type in first_line_column_types[len(column_types) :]:
                column_types.append(column_type)
        # Now we fill any unknown (None) column_types with data from first line
        for i in range(len(column_types)):
            if column_types[i] is None:
                if len(first_line_column_types) <= i or first_line_column_types[i] is None:
                    column_types[i] = default_column_type
                else:
                    column_types[i] = first_line_column_types[i]
        # Set the discovered metadata values for the dataset
        dataset.metadata.data_lines = data_lines
        dataset.metadata.comment_lines = comment_lines
        dataset.metadata.column_types = column_types
        dataset.metadata.columns = len(column_types)
        dataset.metadata.delimiter = "\t"
        if column_names is not None:
            dataset.metadata.column_names = column_names

    def as_gbrowse_display_file(self, dataset: HasFileName, **kwd) -> Union[FileObjType, str]:
        return open(dataset.get_file_name(), "rb")

    def as_ucsc_display_file(self, dataset: DatasetProtocol, **kwd) -> Union[FileObjType, str]:
        return open(dataset.get_file_name(), "rb")


class SraManifest(Tabular):
    """A manifest received from the sra_source tool."""

    file_ext = "sra_manifest.tabular"
    data_line_offset = 1

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        dataset.metadata.comment_lines = 1

    def get_column_names(self, first_line: str) -> Optional[List[str]]:
        return first_line.strip().split("\t")


class Taxonomy(Tabular):
    file_ext = "taxonomy"

    def __init__(self, **kwd):
        """Initialize taxonomy datatype"""
        super().__init__(**kwd)
        self.column_names = [
            "Name",
            "TaxId",
            "Root",
            "Superkingdom",
            "Kingdom",
            "Subkingdom",
            "Superphylum",
            "Phylum",
            "Subphylum",
            "Superclass",
            "Class",
            "Subclass",
            "Superorder",
            "Order",
            "Suborder",
            "Superfamily",
            "Family",
            "Subfamily",
            "Tribe",
            "Subtribe",
            "Genus",
            "Subgenus",
            "Species",
            "Subspecies",
        ]

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)


@dataproviders.decorators.has_dataproviders
@build_sniff_from_prefix
class Sam(Tabular, _BamOrSam):
    edam_format = "format_2573"
    edam_data = "data_0863"
    file_ext = "sam"
    track_type = "ReadTrack"
    data_sources = {"data": "bam", "index": "bigwig"}

    MetadataElement(
        name="bam_version",
        default=None,
        desc="BAM Version",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
    )
    MetadataElement(
        name="sort_order",
        default=None,
        desc="Sort Order",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
    )
    MetadataElement(
        name="read_groups",
        default=[],
        desc="Read Groups",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="reference_names",
        default=[],
        desc="Chromosome Names",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="reference_lengths",
        default=[],
        desc="Chromosome Lengths",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="bam_header",
        default={},
        desc="Dictionary of BAM Headers",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value={},
    )

    def __init__(self, **kwd):
        """Initialize sam datatype"""
        super().__init__(**kwd)
        self.column_names = [
            "QNAME",
            "FLAG",
            "RNAME",
            "POS",
            "MAPQ",
            "CIGAR",
            "MRNM",
            "MPOS",
            "ISIZE",
            "SEQ",
            "QUAL",
            "OPT",
        ]

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in SAM format

        A file in SAM format consists of lines of tab-separated data.
        The following header line may be the first line::

          @QNAME  FLAG    RNAME   POS     MAPQ    CIGAR   MRNM    MPOS    ISIZE   SEQ     QUAL
          or
          @QNAME  FLAG    RNAME   POS     MAPQ    CIGAR   MRNM    MPOS    ISIZE   SEQ     QUAL    OPT

        Data in the OPT column is optional and can consist of tab-separated data

        For complete details see http://samtools.sourceforge.net/SAM1.pdf

        Rules for sniffing as True::

            There must be 11 or more columns of data on each line
            Columns 2 (FLAG), 4(POS), 5 (MAPQ), 8 (MPOS), and 9 (ISIZE) must be numbers (9 can be negative)
            We will only check that up to the first 5 alignments are correctly formatted.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Sam().sniff( fname )
        False
        >>> fname = get_test_fname( '1.sam' )
        >>> Sam().sniff( fname )
        True
        """
        count = 0
        for line in file_prefix.line_iterator():
            line = line.strip()
            if line:
                if line[0] != "@":
                    line_pieces = line.split("\t")
                    if len(line_pieces) < 11:
                        return False
                    try:
                        int(line_pieces[1])
                        int(line_pieces[3])
                        int(line_pieces[4])
                        int(line_pieces[7])
                        int(line_pieces[8])
                    except ValueError:
                        return False
                    count += 1
                    if count == 5:
                        return True
        if count < 5 and count > 0:
            return True
        return False

    def set_meta(
        self,
        dataset: DatasetProtocol,
        overwrite: bool = True,
        skip: Optional[int] = None,
        max_data_lines: Optional[int] = 5,
        **kwd,
    ) -> None:
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
        >>> from galaxy.model import Dataset, set_datatypes_registry
        >>> from galaxy.model import History, HistoryDatasetAssociation
        >>> from galaxy.model.mapping import init
        >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
        >>> hist = History()
        >>> with sa_session.begin():
        ...     sa_session.add(hist)
        >>> set_datatypes_registry(example_datatype_registry_for_sample())
        >>> fname = get_test_fname( 'sam_with_header.sam' )
        >>> samds = Dataset(external_filename=fname)
        >>> hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='sam', create_dataset=True, sa_session=sa_session, dataset=samds))
        >>> Sam().set_meta(hda)
        >>> hda.metadata.comment_lines
        2
        >>> hda.metadata.reference_names
        ['ref', 'ref2']
        """
        if dataset.has_data():
            with open(dataset.get_file_name()) as dataset_fh:
                comment_lines = 0
                if (
                    self.max_optional_metadata_filesize >= 0
                    and dataset.get_size() > self.max_optional_metadata_filesize
                ):
                    # If the dataset is larger than optional_metadata, just count comment lines.
                    for line in dataset_fh:
                        if line.startswith("@"):
                            comment_lines += 1
                        else:
                            # No more comments, and the file is too big to look at the whole thing. Give up.
                            dataset.metadata.data_lines = None
                            break
                else:
                    # Otherwise, read the whole thing and set num data lines.
                    for i, line in enumerate(dataset_fh):  # noqa: B007
                        if line.startswith("@"):
                            comment_lines += 1
                    dataset.metadata.data_lines = i + 1 - comment_lines
            dataset.metadata.comment_lines = comment_lines
            dataset.metadata.columns = 12
            dataset.metadata.column_types = [
                "str",
                "int",
                "str",
                "int",
                "int",
                "str",
                "str",
                "int",
                "int",
                "str",
                "str",
                "str",
            ]

            _BamOrSam().set_meta(dataset, overwrite=overwrite, **kwd)

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """
        Multiple SAM files may each have headers. Since the headers should all be the same, remove
        the headers from files 1-n, keeping them in the first file only
        """
        shutil.move(split_files[0], output_file)

        if len(split_files) > 1:
            cmd = ["egrep", "-v", "-h", "^@"] + split_files[1:] + [">>", output_file]
            subprocess.check_call(cmd, shell=True)

    # Dataproviders
    # sam does not use '#' to indicate comments/headers - we need to strip out those headers from the std. providers
    # TODO:?? seems like there should be an easier way to do this - metadata.comment_char?
    @dataproviders.decorators.dataprovider_factory("line", FilteredLineDataProvider.settings)
    def line_dataprovider(self, dataset: DatasetProtocol, **settings) -> FilteredLineDataProvider:
        settings["comment_char"] = "@"
        return super().line_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("regex-line", RegexLineDataProvider.settings)
    def regex_line_dataprovider(self, dataset: DatasetProtocol, **settings) -> RegexLineDataProvider:
        settings["comment_char"] = "@"
        return super().regex_line_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("column", ColumnarDataProvider.settings)
    def column_dataprovider(self, dataset: DatasetProtocol, **settings) -> ColumnarDataProvider:
        settings["comment_char"] = "@"
        return super().column_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("dataset-column", ColumnarDataProvider.settings)
    def dataset_column_dataprovider(self, dataset: DatasetProtocol, **settings) -> DatasetColumnarDataProvider:
        settings["comment_char"] = "@"
        return super().dataset_column_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("dict", DictDataProvider.settings)
    def dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> DictDataProvider:
        settings["comment_char"] = "@"
        return super().dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("dataset-dict", DictDataProvider.settings)
    def dataset_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> DatasetDictDataProvider:
        settings["comment_char"] = "@"
        return super().dataset_dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("header", RegexLineDataProvider.settings)
    def header_dataprovider(self, dataset: DatasetProtocol, **settings) -> RegexLineDataProvider:
        dataset_source = DatasetDataProvider(dataset)
        headers_source = RegexLineDataProvider(dataset_source, regex_list=["^@"])
        return RegexLineDataProvider(headers_source, **settings)

    @dataproviders.decorators.dataprovider_factory("id-seq-qual", dict_dataprovider.settings)
    def id_seq_qual_dataprovider(self, dataset: DatasetProtocol, **settings) -> DictDataProvider:
        # provided as an example of a specified column dict (w/o metadata)
        settings["indeces"] = [0, 9, 10]
        settings["column_names"] = ["id", "seq", "qual"]
        return self.dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("genomic-region", GenomicRegionDataProvider.settings)
    def genomic_region_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        settings["comment_char"] = "@"
        return GenomicRegionDataProvider(dataset, 2, 3, 3, **settings)

    @dataproviders.decorators.dataprovider_factory("genomic-region-dict", GenomicRegionDataProvider.settings)
    def genomic_region_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        settings["comment_char"] = "@"
        return GenomicRegionDataProvider(dataset, 2, 3, 3, True, **settings)

    # @dataproviders.decorators.dataprovider_factory( 'samtools' )
    # def samtools_dataprovider( self, dataset, **settings ):
    #     dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
    #     return dataproviders.dataset.SamtoolsDataProvider( dataset_source, **settings )


@dataproviders.decorators.has_dataproviders
@build_sniff_from_prefix
class Pileup(Tabular):
    """Tab delimited data in pileup (6- or 10-column) format"""

    edam_format = "format_3015"
    file_ext = "pileup"
    line_class = "genomic coordinate"
    data_sources = {"data": "tabix"}

    MetadataElement(name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter)
    MetadataElement(name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter)
    MetadataElement(name="endCol", default=2, desc="End column", param=metadata.ColumnParameter)
    MetadataElement(name="baseCol", default=3, desc="Reference base column", param=metadata.ColumnParameter)

    def init_meta(self, dataset: HasMetadata, copy_from: Optional[HasMetadata] = None) -> None:
        super().init_meta(dataset, copy_from=copy_from)

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(
            dataset, column_parameter_alias={"chromCol": "Chrom", "startCol": "Start", "baseCol": "Base"}
        )

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Checks for 'pileup-ness'

        There are two main types of pileup: 6-column and 10-column. For both,
        the first three and last two columns are the same. We only check the
        first three to allow for some personalization of the format.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'interval.interval' )
        >>> Pileup().sniff( fname )
        False
        >>> fname = get_test_fname( '6col.pileup' )
        >>> Pileup().sniff( fname )
        True
        >>> fname = get_test_fname( '10col.pileup' )
        >>> Pileup().sniff( fname )
        True
        >>> fname = get_test_fname( '1.excel.xls' )
        >>> Pileup().sniff( fname )
        False
        >>> fname = get_test_fname( '2.txt' )
        >>> Pileup().sniff( fname )  # 2.txt
        False
        >>> fname = get_test_fname( 'test_tab2.tabular' )
        >>> Pileup().sniff( fname )
        False
        """
        found_non_comment_lines = False
        try:
            headers = iter_headers(file_prefix, "\t")
            for hdr in headers:
                if hdr and not hdr[0].startswith("#"):
                    if len(hdr) < 5:
                        return False
                    # chrom start in column 1 (with 0-based columns)
                    # and reference base is in column 2
                    chrom = int(hdr[1])
                    assert chrom >= 0
                    assert hdr[2] in ["A", "C", "G", "T", "N", "a", "c", "g", "t", "n"]
                    found_non_comment_lines = True
        except Exception:
            return False
        return found_non_comment_lines

    # Dataproviders
    @dataproviders.decorators.dataprovider_factory("genomic-region", GenomicRegionDataProvider.settings)
    def genomic_region_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        return GenomicRegionDataProvider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("genomic-region-dict", GenomicRegionDataProvider.settings)
    def genomic_region_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        settings["named_columns"] = True
        return self.genomic_region_dataprovider(dataset, **settings)


@dataproviders.decorators.has_dataproviders
@build_sniff_from_prefix
class BaseVcf(Tabular):
    """Variant Call Format for describing SNPs and other simple genome variations."""

    edam_format = "format_3016"
    track_type = "VariantTrack"
    data_sources = {"data": "tabix", "index": "bigwig"}

    column_names = ["Chrom", "Pos", "ID", "Ref", "Alt", "Qual", "Filter", "Info", "Format", "data"]

    MetadataElement(name="columns", default=10, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(
        name="column_types",
        default=["str", "int", "str", "str", "str", "int", "str", "list", "str", "str"],
        param=metadata.ColumnTypesParameter,
        desc="Column types",
        readonly=True,
        visible=False,
    )
    MetadataElement(
        name="viz_filter_cols",
        desc="Score column for visualization",
        default=[5],
        param=metadata.ColumnParameter,
        optional=True,
        multiple=True,
        visible=False,
    )
    MetadataElement(
        name="sample_names", default=[], desc="Sample names", readonly=True, visible=False, optional=True, no_value=[]
    )

    def _sniff(self, fname_or_file_prefix: Union[str, FilePrefix]) -> bool:
        # Because this sniffer is run on compressed files that might be BGZF (due to the VcfGz subclass), we should
        # handle unicode decode errors. This should ultimately be done in get_headers(), but guess_ext() currently
        # relies on get_headers() raising this exception.
        headers = get_headers(fname_or_file_prefix, "\n", count=1)
        return headers[0][0].startswith("##fileformat=VCF")

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        line = None
        with compression_utils.get_fileobj(dataset.get_file_name()) as fh:
            # Skip comments.
            for line in fh:
                if not line.startswith("##"):
                    break

        if line and line.startswith("#"):
            # Found header line, get sample names.
            dataset.metadata.sample_names = line.split()[9:]

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        stderr_f = tempfile.NamedTemporaryFile(prefix="bam_merge_stderr")
        stderr_name = stderr_f.name
        command = ["bcftools", "concat"] + split_files + ["-o", output_file]
        log.info(f"Merging vcf files with command [{' '.join(command)}]")
        exit_code = subprocess.call(args=command, stderr=open(stderr_name, "wb"))
        with open(stderr_name, "rb") as f:
            stderr = f.read().strip()
        # Did merge succeed?
        if exit_code != 0:
            raise Exception(f"Error merging VCF files: {stderr!r}")

    def validate(self, dataset: DatasetProtocol, **kwd) -> DatatypeValidation:
        def validate_row(row):
            if len(row) < 8:
                raise Exception("Not enough columns in row {}".format(row.join("\t")))

        validate_tabular(dataset.get_file_name(), sep="\t", validate_row=validate_row, comment_designator="#")
        return DatatypeValidation.validated()

    # Dataproviders
    @dataproviders.decorators.dataprovider_factory("genomic-region", GenomicRegionDataProvider.settings)
    def genomic_region_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        return GenomicRegionDataProvider(dataset, 0, 1, 1, **settings)

    @dataproviders.decorators.dataprovider_factory("genomic-region-dict", GenomicRegionDataProvider.settings)
    def genomic_region_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        settings["named_columns"] = True
        return self.genomic_region_dataprovider(dataset, **settings)


class Vcf(BaseVcf):
    file_ext = "vcf"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        return self._sniff(file_prefix)


class VcfGz(BaseVcf, binary.Binary):
    # This class name is a misnomer, should be VcfBgzip
    file_ext = "vcf_bgzip"
    file_ext_export_alias = "vcf.gz"
    compressed = True
    compressed_format = "gzip"

    MetadataElement(
        name="tabix_index",
        desc="Vcf Index File",
        param=metadata.FileParameter,
        file_ext="tbi",
        readonly=True,
        visible=False,
        optional=True,
    )

    def sniff(self, filename: str) -> bool:
        if not self._sniff(filename):
            return False
        # Check that the file is compressed with bgzip (not gzip), i.e. the
        # compressed format is BGZF, as explained in
        # http://samtools.github.io/hts-specs/SAMv1.pdf
        with open(filename, "rb") as fh:
            fh.seek(-28, 2)
            last28 = fh.read()
            return binascii.hexlify(last28) == b"1f8b08040000000000ff0600424302001b0003000000000000000000"

    def set_meta(
        self, dataset: DatasetProtocol, overwrite: bool = True, metadata_tmp_files_dir: Optional[str] = None, **kwd
    ) -> None:
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        # Creates the index for the VCF file.
        # These metadata values are not accessible by users, always overwrite
        index_file = dataset.metadata.tabix_index
        if not index_file:
            index_file = dataset.metadata.spec["tabix_index"].param.new_file(
                dataset=dataset, metadata_tmp_files_dir=metadata_tmp_files_dir
            )

        try:
            pysam.tabix_index(
                dataset.get_file_name(), index=index_file.get_file_name(), preset="vcf", keep_original=True, force=True
            )
        except Exception as e:
            raise Exception(f"Error setting VCF.gz metadata: {util.unicodify(e)}")
        dataset.metadata.tabix_index = index_file


@build_sniff_from_prefix
class Eland(Tabular):
    """Support for the export.txt.gz file used by Illumina's ELANDv2e aligner"""

    compressed = True
    compressed_format = "gzip"
    file_ext = "_export.txt.gz"
    MetadataElement(name="columns", default=0, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(
        name="column_types",
        default=[],
        param=metadata.ColumnTypesParameter,
        desc="Column types",
        readonly=True,
        visible=False,
        no_value=[],
    )
    MetadataElement(name="comment_lines", default=0, desc="Number of comments", readonly=True, visible=False)
    MetadataElement(
        name="tiles",
        default=[],
        param=metadata.ListParameter,
        desc="Set of tiles",
        readonly=True,
        visible=False,
        no_value=[],
    )
    MetadataElement(
        name="reads",
        default=[],
        param=metadata.ListParameter,
        desc="Set of reads",
        readonly=True,
        visible=False,
        no_value=[],
    )
    MetadataElement(
        name="lanes",
        default=[],
        param=metadata.ListParameter,
        desc="Set of lanes",
        readonly=True,
        visible=False,
        no_value=[],
    )
    MetadataElement(
        name="barcodes",
        default=[],
        param=metadata.ListParameter,
        desc="Set of barcodes",
        readonly=True,
        visible=False,
        no_value=[],
    )

    def __init__(self, **kwd):
        """Initialize eland datatype"""
        super().__init__(**kwd)
        self.column_names = [
            "MACHINE",
            "RUN_NO",
            "LANE",
            "TILE",
            "X",
            "Y",
            "INDEX",
            "READ_NO",
            "SEQ",
            "QUAL",
            "CHROM",
            "CONTIG",
            "POSITION",
            "STRAND",
            "DESC",
            "SRAS",
            "PRAS",
            "PART_CHROM",
            "PART_CONTIG",
            "PART_OFFSET",
            "PART_STRAND",
            "FILT",
        ]

    def make_html_table(
        self, dataset: DatasetProtocol, skipchars: Optional[List] = None, peek: Optional[List] = None, **kwargs
    ) -> str:
        """Create HTML table, used for displaying peek"""
        skipchars = skipchars or []
        try:
            out = ['<table cellspacing="0" cellpadding="3">']
            # Generate column header
            out.append("<tr>")
            for i, name in enumerate(self.column_names):
                out.append(f"<th>{str(i + 1)}.{name}</th>")
            # This data type requires at least 11 columns in the data
            if dataset.metadata.columns - len(self.column_names) > 0:
                for i in range(len(self.column_names), max(dataset.metadata.columns, self.max_peek_columns)):
                    out.append(f"<th>{str(i + 1)}</th>")
                out.append("</tr>")
            out.append(self.make_html_peek_rows(dataset, skipchars=skipchars, peek=peek))
            out.append("</table>")
            return "".join(out)
        except Exception as exc:
            return f"Can't create peek {exc}"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in ELAND export format

        A file in ELAND export format consists of lines of tab-separated data.
        There is no header.

        Rules for sniffing as True::

            - There must be 22 columns on each line
            - LANE, TILEm X, Y, INDEX, READ_NO, SEQ, QUAL, POSITION, *STRAND, FILT must be correct
            - We will only check that up to the first 5 alignments are correctly formatted.
        """
        count = 0
        for line in file_prefix.line_iterator():
            line = line.strip()
            if not line:
                break  # Had a EOF comment previously, but this does not indicate EOF. I assume empty lines are not valid and this was intentional.
            if line:
                line_pieces = line.split("\t")
                if len(line_pieces) != 22:
                    return False
                if int(line_pieces[1]) < 0:
                    raise Exception("Out of range")
                if int(line_pieces[2]) < 0:
                    raise Exception("Out of range")
                if int(line_pieces[3]) < 0:
                    raise Exception("Out of range")
                int(line_pieces[4])
                int(line_pieces[5])
                # can get a lot more specific
                count += 1
                if count == 5:
                    break
        if count > 0:
            return True
        return False

    def set_meta(
        self,
        dataset: DatasetProtocol,
        overwrite: bool = True,
        skip: Optional[int] = None,
        max_data_lines: Optional[int] = 5,
        **kwd,
    ) -> None:
        if dataset.has_data():
            with compression_utils.get_fileobj(dataset.get_file_name(), compressed_formats=["gzip"]) as dataset_fh:
                dataset_fh = cast(FileObjTypeStr, dataset_fh)
                lanes = {}
                tiles = {}
                barcodes = {}
                reads = {}
                # Should always read the entire file (until we devise a more clever way to pass metadata on)
                # if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
                # If the dataset is larger than optional_metadata, just count comment lines.
                #     dataset.metadata.data_lines = None
                # else:
                # Otherwise, read the whole thing and set num data lines.
                for i, line in enumerate(dataset_fh):
                    if line:
                        line_pieces = line.split("\t")
                        if len(line_pieces) != 22:
                            raise Exception(f"{dataset.get_file_name()}:{i}:Corrupt line!")
                        lanes[line_pieces[2]] = 1
                        tiles[line_pieces[3]] = 1
                        barcodes[line_pieces[6]] = 1
                        reads[line_pieces[7]] = 1
                dataset.metadata.data_lines = i + 1
            dataset.metadata.comment_lines = 0
            dataset.metadata.columns = 21
            dataset.metadata.column_types = [
                "str",
                "int",
                "int",
                "int",
                "int",
                "int",
                "str",
                "int",
                "str",
                "str",
                "str",
                "str",
                "str",
                "str",
                "str",
                "str",
                "str",
                "str",
                "str",
                "str",
                "str",
            ]
            dataset.metadata.lanes = list(lanes.keys())
            dataset.metadata.tiles = [f"{int(t):04d}" for t in tiles.keys()]
            dataset.metadata.barcodes = [_ for _ in barcodes.keys() if _ != "0"] + [
                "NoIndex" for _ in barcodes.keys() if _ == "0"
            ]
            dataset.metadata.reads = list(reads.keys())


@build_sniff_from_prefix
class ElandMulti(Tabular):
    file_ext = "elandmulti"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        return False


class FeatureLocationIndex(Tabular):
    """
    An index that stores feature locations in tabular format.
    """

    file_ext = "fli"
    MetadataElement(name="columns", default=2, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(
        name="column_types",
        default=["str", "str"],
        param=metadata.ColumnTypesParameter,
        desc="Column types",
        readonly=True,
        visible=False,
        no_value=[],
    )


@dataproviders.decorators.has_dataproviders
class BaseCSV(TabularData):
    """
    Delimiter-separated table data.
    This includes CSV, TSV and other dialects understood by the
    Python 'csv' module https://docs.python.org/2/library/csv.html
    Must be extended to define the dialect to use, strict_width and file_ext.
    See the Python module csv for documentation of dialect settings
    """

    @property
    def dialect(self):
        raise NotImplementedError

    @property
    def strict_width(self):
        raise NotImplementedError

    delimiter = ","
    peek_size = 1024  # File chunk used for sniffing CSV dialect
    big_peek_size = 10240  # Large File chunk used for sniffing CSV dialect

    def sniff(self, filename: str) -> bool:
        """Return True if if recognizes dialect and header."""
        # check the dialect works
        with open(filename, newline="") as f:
            reader = csv.reader(f, self.dialect)
            # Check we can read header and get columns
            header_row = next(reader)
            if len(header_row) < 2:
                # No columns so not separated by this dialect.
                return False

            # Check that there is a second row as it is used by set_meta and
            # that all rows can be read
            if self.strict_width:
                num_columns = len(header_row)
                found_second_line = False
                for data_row in reader:
                    found_second_line = True
                    # All columns must be the same length
                    if num_columns != len(data_row):
                        return False
                if not found_second_line:
                    return False
            else:
                data_row = next(reader)
                if len(data_row) < 2:
                    # No columns so not separated by this dialect.
                    return False
                # ignore the length in the rest
                for _ in reader:
                    pass

        # Optional: Check Python's csv comes up with a similar dialect
        with open(filename) as f:
            big_peek = f.read(self.big_peek_size)
        auto_dialect = csv.Sniffer().sniff(big_peek)
        if auto_dialect.delimiter != self.dialect.delimiter:
            return False
        if auto_dialect.quotechar != self.dialect.quotechar:
            return False
        # Not checking for other dialect options
        # They may be mis detected from just the sample.
        # Or not effect the read such as doublequote

        # Optional: Check for headers as in the past.
        # Note: No way around Python's csv calling Sniffer.sniff again.
        # Note: Without checking the dialect returned by sniff
        #       this test may be checking the wrong dialect.
        if not csv.Sniffer().has_header(big_peek):
            return False
        return True

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        column_types = []
        header_row = []
        data_row = []
        data_lines = 0
        if dataset.has_data():
            with open(dataset.get_file_name(), newline="") as csvfile:
                # Parse file with the correct dialect
                reader = csv.reader(csvfile, self.dialect)
                try:
                    header_row = next(reader)
                    data_row = next(reader)
                    for _ in reader:
                        pass
                except StopIteration:
                    pass
                except csv.Error as e:
                    raise Exception(f"CSV reader error - line {reader.line_num}: {e}")
                else:
                    data_lines = reader.line_num - 1

        # Guess column types
        for cell in data_row:
            column_types.append(self.guess_type(cell))

        # Set metadata
        dataset.metadata.data_lines = data_lines
        dataset.metadata.comment_lines = int(bool(header_row))
        dataset.metadata.column_types = column_types
        dataset.metadata.columns = max(len(header_row), len(data_row))
        dataset.metadata.column_names = header_row
        dataset.metadata.delimiter = self.dialect.delimiter


@dataproviders.decorators.has_dataproviders
class CSV(BaseCSV):
    """
    Comma-separated table data.
    Only sniffs comma-separated files with at least 2 rows and 2 columns.
    """

    file_ext = "csv"
    dialect = csv.excel  # This is the default
    strict_width = False  # Previous csv type did not check column width


@dataproviders.decorators.has_dataproviders
class TSV(BaseCSV):
    """
    Tab-separated table data.
    Only sniff tab-separated files with at least 2 rows and 2 columns.

    Note: Use of this datatype is optional as the general tabular datatype will
    handle most tab-separated files. This datatype is only required for datasets
    with tabs INSIDE double quotes.

    This datatype currently does not support TSV files where the header has one
    column less to indicate first column is row names. This kind of file is
    handled fine by the tabular datatype.
    """

    file_ext = "tsv"
    dialect = csv.excel_tab
    strict_width = True  # Leave files with different width to tabular


@build_sniff_from_prefix
class ConnectivityTable(Tabular):
    edam_format = "format_3309"
    file_ext = "ct"

    header_regexp = re.compile("^[0-9]+(?:	|[ ]+).*?(?:ENERGY|energy|dG)[ 	].*?=")
    structure_regexp = re.compile(
        "^[0-9]+(?:	|[ ]+)[ACGTURYKMSWBDHVN]+(?:	|[ ]+)[^	]+(?:	|[ ]+)[^	]+(?:	|[ ]+)[^	]+(?:	|[ ]+)[^	]+"
    )

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.columns = 6
        self.column_names = ["base_index", "base", "neighbor_left", "neighbor_right", "partner", "natural_numbering"]
        self.column_types = ["int", "str", "int", "int", "int", "int"]

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        data_lines = 0

        with open(dataset.get_file_name()) as fh:
            for _ in fh:
                data_lines += 1

        dataset.metadata.data_lines = data_lines

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        The ConnectivityTable (CT) is a file format used for describing
        RNA 2D structures by tools including MFOLD, UNAFOLD and
        the RNAStructure package. The tabular file format is defined as
        follows::

            5	energy = -12.3	sequence name
            1	G	0	2	0	1
            2	A	1	3	0	2
            3	A	2	4	0	3
            4	A	3	5	0	4
            5	C	4	6	1	5

        The links given at the edam ontology page do not indicate what
        type of separator is used (space or tab) while different
        implementations exist. The implementation that uses spaces as
        separator (implemented in RNAStructure) is as follows::

            10    ENERGY = -34.8  seqname
            1 G       0    2    9    1
            2 G       1    3    8    2
            3 G       2    4    7    3
            4 a       3    5    0    4
            5 a       4    6    0    5
            6 a       5    7    0    6
            7 C       6    8    3    7
            8 C       7    9    2    8
            9 C       8   10    1    9
            10 a       9    0    0   10
        """

        i = 0
        j = 1

        handle = file_prefix.string_io()
        for line in handle:
            line = line.strip()

            if len(line) > 0:
                if i == 0:
                    if not self.header_regexp.match(line):
                        return False
                    else:
                        length = int(re.split(r"\W+", line, maxsplit=1)[0])
                else:
                    if not self.structure_regexp.match(line.upper()):
                        return False
                    else:
                        if j != int(re.split(r"\W+", line, maxsplit=1)[0]):
                            return False
                        elif j == length:  # Last line of first sequence has been reached
                            return True
                        else:
                            j += 1
                i += 1
        return False

    def get_chunk(self, trans, dataset: HasFileName, offset: int = 0, ck_size: Optional[int] = None) -> str:
        ck_data, last_read = self._read_chunk(trans, dataset, offset, ck_size)
        try:
            # The ConnectivityTable format has several derivatives of which one is delimited by (multiple) spaces.
            # By converting these spaces back to tabs, chunks can still be interpreted by tab delimited file parsers
            ck_data_header, ck_data_body = ck_data.split("\n", 1)
            ck_data_header = re.sub("^([0-9]+)[ ]+", r"\1\t", ck_data_header)
            ck_data_body = re.sub("\n[ \t]+", "\n", ck_data_body)
            ck_data_body = re.sub("[ ]+", "\t", ck_data_body)
            ck_data = f"{ck_data_header}\n{ck_data_body}"
        except ValueError:
            pass  # 1 or 0 lines left

        return dumps(
            {
                "ck_data": util.unicodify(ck_data),
                "offset": last_read,
                "data_line_offset": self.data_line_offset,
            }
        )


@build_sniff_from_prefix
class MatrixMarket(TabularData):
    """
    The Matrix Market (MM) exchange formats provide a simple mechanism
    to facilitate the exchange of matrix data. MM coordinate format is
    suitable for representing sparse matrices. Only nonzero entries need
    be encoded, and the coordinates of each are given explicitly.

    The tabular file format is defined as follows:

    .. code-block::

        %%MatrixMarket matrix coordinate real general <--- header line
        %                                             <--+
        % comments                                       |-- 0 or more comment lines
        %                                             <--+
            M  N  L                                   <--- rows, columns, entries
            I1  J1  A(I1, J1)                         <--+
            I2  J2  A(I2, J2)                            |
            I3  J3  A(I3, J3)                            |-- L lines
                . . .                                    |
            IL JL  A(IL, JL)                          <--+

    Indices are 1-based, i.e. A(1,1) is the first element.

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> MatrixMarket().sniff( get_test_fname( 'sequence.maf' ) )
    False
    >>> MatrixMarket().sniff( get_test_fname( '1.mtx' ) )
    True
    >>> MatrixMarket().sniff( get_test_fname( '2.mtx' ) )
    True
    >>> MatrixMarket().sniff( get_test_fname( '3.mtx' ) )
    True
    """

    file_ext = "mtx"

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        return file_prefix.startswith("%%MatrixMarket matrix coordinate")

    def set_meta(
        self,
        dataset: DatasetProtocol,
        overwrite: bool = True,
        skip: Optional[int] = None,
        max_data_lines: Optional[int] = 5,
        **kwd,
    ) -> None:
        if dataset.has_data():
            # If the dataset is larger than optional_metadata, just count comment lines.
            with open(dataset.get_file_name()) as dataset_fh:
                line = ""
                data_lines = 0
                comment_lines = 0
                # If the dataset is larger than optional_metadata, just count comment lines.
                count_comments_only = (
                    self.max_optional_metadata_filesize >= 0
                    and dataset.get_size() > self.max_optional_metadata_filesize
                )
                for line in dataset_fh:
                    if line.startswith("%"):
                        comment_lines += 1
                    elif count_comments_only:
                        data_lines = None  # type: ignore [assignment]
                        break
                    else:
                        data_lines += 1
                if " " in line:
                    dataset.metadata.delimiter = " "
                else:
                    dataset.metadata.delimiter = "\t"
            dataset.metadata.comment_lines = comment_lines
            dataset.metadata.data_lines = data_lines
            dataset.metadata.columns = 3
            dataset.metadata.column_types = ["int", "int", "float"]


@build_sniff_from_prefix
class CMAP(TabularData):
    """
    # CMAP File Version:    2.0
    # Label Channels:   1
    # Nickase Recognition Site 1:   cttaag;green_01
    # Nickase Recognition Site 2:   cctcagc;red_01
    # Number of Consensus Maps: 459
    # Values corresponding to intervals (StdDev, HapDelta) refer to the interval between current site and next site
    #h  CMapId  ContigLength    NumSites    SiteID  LabelChannel    Position    StdDev  Coverage    Occurrence  ChimQuality SegDupL SegDupR FragileL    FragileR    OutlierFrac ChimNorm    Mask
    #f  int float   int int int float   float   float   float   float   float   float   float   float   float   float   Hex
    182 58474736.7  10235   1   1   58820.9 35.4    13.5    13.5    -1.00   -1.00   -1.00   3.63    0.00    0.00    -1.00   0
    182 58474736.7  10235   1   1   58820.9 35.4    13.5    13.5    -1.00   -1.00   -1.00   3.63    0.00    0.00    -1.00   0
    182 58474736.7  10235   1   1   58820.9 35.4    13.5    13.5    -1.00   -1.00   -1.00   3.63    0.00    0.00    -1.00   0
    """

    file_ext = "cmap"

    MetadataElement(
        name="cmap_version",
        default="0.2",
        desc="version of cmap",
        readonly=True,
        visible=True,
        optional=False,
        no_value="0.2",
    )
    MetadataElement(
        name="label_channels",
        default=1,
        desc="the number of label channels",
        readonly=True,
        visible=True,
        optional=False,
        no_value=1,
    )
    MetadataElement(
        name="nickase_recognition_site_1",
        default=[],
        desc="comma separated list of label motif recognition sequences for channel 1",
        readonly=True,
        visible=True,
        optional=False,
        no_value=[],
    )
    MetadataElement(
        name="number_of_consensus_nanomaps",
        default=0,
        desc="the total number of consensus genome maps in the CMAP file",
        readonly=True,
        visible=True,
        optional=False,
        no_value=0,
    )
    MetadataElement(
        name="nickase_recognition_site_2",
        default=[],
        desc="comma separated list of label motif recognition sequences for channel 2",
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="channel_1_color",
        default=[],
        desc="channel 1 color",
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="channel_2_color",
        default=[],
        desc="channel 2 color",
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        handle = file_prefix.string_io()
        for line in handle:
            if not line.startswith("#"):
                return False
            if line.startswith("# CMAP File Version:"):
                return True
        return False

    def set_meta(
        self,
        dataset: DatasetProtocol,
        overwrite: bool = True,
        skip: Optional[int] = None,
        max_data_lines: Optional[int] = 7,
        **kwd,
    ) -> None:
        if dataset.has_data():
            with open(dataset.get_file_name()) as dataset_fh:
                comment_lines = 0
                column_headers = None
                cleaned_column_types = []
                number_of_columns = 0
                for i, line in enumerate(dataset_fh):
                    line = line.strip("\n")
                    if line.startswith("#"):
                        if line.startswith("#h"):
                            column_headers = line.split("\t")[1:]
                        elif line.startswith("#f"):
                            for column_type in line.split("\t")[1:]:
                                if column_type == "Hex":
                                    cleaned_column_types.append("str")
                                else:
                                    cleaned_column_types.append(column_type)
                        comment_lines += 1
                        fields = line.split("\t")
                        if len(fields) == 2:
                            if fields[0] == "# CMAP File Version:":
                                dataset.metadata.cmap_version = fields[1]
                            elif fields[0] == "# Label Channels:":
                                dataset.metadata.label_channels = int(fields[1])
                            elif fields[0] == "# Nickase Recognition Site 1:":
                                fields2 = fields[1].split(";")
                                if len(fields2) == 2:
                                    dataset.metadata.channel_1_color = fields2[1]
                                dataset.metadata.nickase_recognition_site_1 = fields2[0].split(",")
                            elif fields[0] == "# Number of Consensus Maps:":
                                dataset.metadata.number_of_consensus_nanomaps = int(fields[1])
                            elif fields[0] == "# Nickase Recognition Site 2:":
                                fields2 = fields[1].split(";")
                                if len(fields2) == 2:
                                    dataset.metadata.channel_2_color = fields2[1]
                                dataset.metadata.nickase_recognition_site_2 = fields2[0].split(",")
                    elif (
                        self.max_optional_metadata_filesize >= 0
                        and dataset.get_size() > self.max_optional_metadata_filesize
                    ):
                        # If the dataset is larger than optional_metadata, just count comment lines.
                        # No more comments, and the file is too big to look at the whole thing. Give up.
                        dataset.metadata.data_lines = None
                        break
                    elif i == comment_lines + 1:
                        number_of_columns = len(line.split("\t"))
                if not (
                    self.max_optional_metadata_filesize >= 0
                    and dataset.get_size() > self.max_optional_metadata_filesize
                ):
                    dataset.metadata.data_lines = i + 1 - comment_lines
            dataset.metadata.comment_lines = comment_lines
            dataset.metadata.column_names = column_headers
            dataset.metadata.column_types = cleaned_column_types
            dataset.metadata.columns = number_of_columns
            dataset.metadata.delimiter = "\t"


@build_sniff_from_prefix
class Psl(Tabular):
    """Tab delimited data in psl format."""

    edam_format = "format_3007"
    file_ext = "psl"
    line_class = "assemblies"
    data_sources = {"data": "tabix"}

    def __init__(self, **kwd):
        """Initialize psl datatype"""
        super().__init__(**kwd)
        self.column_names = [
            "matches",
            "misMatches",
            "repMatches",
            "nCount",
            "qNumInsert",
            "qBaseInsert",
            "tNumInsert",
            "tBaseInsert",
            "strand",
            "qName",
            "qSize",
            "qStart",
            "qEnd",
            "tName",
            "tSize",
            "tStart",
            "tEnd",
            "blockCount",
            "blockSizes",
            "qStarts",
            "tStarts",
        ]

    def sniff_prefix(self, file_prefix: FilePrefix):
        """
        PSL lines represent alignments, and are typically generated
        by BLAT. Each line consists of 21 required fields, and track
        lines may optionally be used to provide more information.

        Fields are tab-separated, and all 21 are required.
        Although not part of the formal PSL specification, track lines
        may be used to further configure sets of features.  Track lines
        are placed at the beginning of the list of features they are
        to affect.

        Rules for sniffing as True::

            - There must be 21 columns on each fields line
            - matches, misMatches repMatches, nCount, qNumInsert,
              qBaseInsert, tNumInsert, tBaseInsert, strand, qSize, qStart,
              qEnd, tName, tSize, tStart, tEnd, blockCount, blockSizes,
              qStarts, tStarts  must be correct
            - We will only check that up to the first 10 alignments are
              correctly formatted.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( '1.psl' )
        >>> Psl().sniff( fname )
        True
        >>> fname = get_test_fname( '2.psl' )
        >>> Psl().sniff( fname )
        True
        >>> fname = get_test_fname( 'interval.interval' )
        >>> Psl().sniff( fname )
        False
        >>> fname = get_test_fname( '2.txt' )
        >>> Psl().sniff( fname )
        False
        >>> fname = get_test_fname( 'test_tab2.tabular' )
        >>> Psl().sniff( fname )
        False
        >>> fname = get_test_fname( 'mothur_datatypetest_true.mothur.ref.taxonomy' )
        >>> Psl().sniff( fname )
        False
        """

        def check_items(s):
            s_items = s.split(",")
            for item in s_items:
                if int(item) < 0:
                    raise Exception("Out of range")

        count = 0
        for line in file_prefix.line_iterator():
            line = line.strip()
            if not line:
                break
            if line:
                if line.startswith("browser") or line.startswith("track"):
                    # Skip track lines.
                    continue
                items = line.split("\t")
                if len(items) != 21:
                    return False
                # tName is a string
                items.pop(13)
                # qName is a string
                items.pop(9)
                # strand
                if items.pop(8) not in ["-", "+", "+-", "-+"]:
                    raise Exception("Invalid strand")
                # blockSizes
                s = items.pop(15).rstrip(",")
                check_items(s)
                # qStarts
                s = items.pop(15).rstrip(",")
                check_items(s)
                # tStarts
                s = items.pop(15).rstrip(",")
                check_items(s)
                if any(int(item) < 0 for item in items):
                    raise Exception("Out of range")
                count += 1
                if count == 10:
                    break
        if count > 0:
            return True
