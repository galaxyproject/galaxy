"""
File format detector
"""

import bz2
import gzip
import io
import logging
import os
import re
import shutil
import struct
import tempfile
import zipfile
from functools import partial
from typing import (
    Callable,
    Dict,
    IO,
    Iterable,
    NamedTuple,
    Optional,
    TYPE_CHECKING,
    Union,
)

from typing_extensions import Protocol

from galaxy.files.uris import stream_url_to_file as files_stream_url_to_file
from galaxy.util import (
    compression_utils,
    file_reader,
    is_binary,
)
from galaxy.util.checkers import (
    check_html,
    COMPRESSION_CHECK_FUNCTIONS,
    is_tar,
)
from galaxy.util.path import StrPath

try:
    import pylibmagic  # noqa: F401  # isort:skip
except ImportError:
    # Not available in conda, but docker image contains libmagic
    pass
import magic  # isort:skip

if TYPE_CHECKING:
    from .data import Data

log = logging.getLogger(__name__)

SNIFF_PREFIX_BYTES = int(os.environ.get("GALAXY_SNIFF_PREFIX_BYTES", None) or 2**20)
BINARY_MIMETYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def get_test_fname(fname):
    """Returns test data filename"""
    path = os.path.dirname(__file__)
    full_path = os.path.join(path, "test", fname)
    assert os.path.isfile(full_path), f"{full_path} is not a file"
    return full_path


def sniff_with_cls(cls, fname):
    path = get_test_fname(fname)
    try:
        return bool(cls().sniff(path))
    except Exception:
        return False


stream_url_to_file = partial(files_stream_url_to_file, prefix="gx_url_paste")


def handle_composite_file(datatype, src_path, extra_files, name, is_binary, tmp_dir, tmp_prefix, upload_opts):
    if not is_binary:
        if upload_opts.get("space_to_tab"):
            convert_newlines_sep2tabs(src_path, tmp_dir=tmp_dir, tmp_prefix=tmp_prefix)
        else:
            convert_newlines(src_path, tmp_dir=tmp_dir, tmp_prefix=tmp_prefix)

    file_output_path = os.path.join(extra_files, name)
    shutil.move(src_path, file_output_path)

    # groom the dataset file content if required by the corresponding datatype definition
    if datatype and datatype.dataset_content_needs_grooming(file_output_path):
        datatype.groom_dataset_content(file_output_path)


class ConvertResult(NamedTuple):
    line_count: int
    converted_path: Optional[str]
    converted_newlines: bool
    converted_regex: bool


class ConvertFunction(Protocol):
    def __call__(
        self, fname: str, in_place: bool = True, tmp_dir: Optional[str] = None, tmp_prefix: Optional[str] = "gxupload"
    ) -> ConvertResult: ...


def convert_newlines(
    fname: str,
    in_place: bool = True,
    tmp_dir: Optional[str] = None,
    tmp_prefix: Optional[str] = "gxupload",
    block_size: int = 128 * 1024,
    regexp=None,
) -> ConvertResult:
    """
    Converts in place a file from universal line endings
    to Posix line endings.
    """
    i = 0
    converted_newlines = False
    converted_regex = False
    NEWLINE_BYTE = 10
    CR_BYTE = 13
    with (
        tempfile.NamedTemporaryFile(mode="wb", prefix=tmp_prefix, dir=tmp_dir, delete=False) as fp,
        open(fname, mode="rb") as fi,
    ):
        last_char = None
        block = fi.read(block_size)
        last_block = b""
        while block:
            if last_char == CR_BYTE and block.startswith(b"\n"):
                # Last block ended with CR, new block startswith newline.
                # Since we replace CR with newline in the previous iteration we skip the first byte
                block = block[1:]
            if block:
                last_char = block[-1]
                if b"\r" in block:
                    block = block.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                    converted_newlines = True
                if regexp:
                    split_block = regexp.split(block)
                    if len(split_block) > 1:
                        converted_regex = True
                    block = b"\t".join(split_block)
                fp.write(block)
                i += block.count(b"\n")
                last_block = block
                block = fi.read(block_size)
        if last_block and last_block[-1] != NEWLINE_BYTE:
            converted_newlines = True
            i += 1
            fp.write(b"\n")
    if in_place:
        shutil.move(fp.name, fname)
        # Return number of lines in file.
        return ConvertResult(i, None, converted_newlines, converted_regex)
    else:
        return ConvertResult(i, fp.name, converted_newlines, converted_regex)


def convert_sep2tabs(
    fname: str,
    in_place: bool = True,
    tmp_dir: Optional[str] = None,
    tmp_prefix: Optional[str] = "gxupload",
    block_size: int = 128 * 1024,
):
    """
    Transforms in place a 'sep' separated file to a tab separated one
    """
    patt: bytes = rb"[^\S\r\n]+"
    regexp = re.compile(patt)
    i = 0
    converted_newlines = False
    converted_regex = False
    with (
        tempfile.NamedTemporaryFile(mode="wb", prefix=tmp_prefix, dir=tmp_dir, delete=False) as fp,
        open(fname, mode="rb") as fi,
    ):
        block = fi.read(block_size)
        while block:
            if block:
                split_block = regexp.split(block)
                if len(split_block) > 1:
                    converted_regex = True
                block = b"\t".join(split_block)
                fp.write(block)
                i += block.count(b"\n") or block.count(b"\r")
                block = fi.read(block_size)
    if in_place:
        shutil.move(fp.name, fname)
        # Return number of lines in file.
        return ConvertResult(i, None, converted_newlines, converted_regex)
    else:
        return ConvertResult(i, fp.name, converted_newlines, converted_regex)


def convert_newlines_sep2tabs(
    fname: str, in_place: bool = True, tmp_dir: Optional[str] = None, tmp_prefix: Optional[str] = "gxupload"
) -> ConvertResult:
    """
    Converts newlines in a file to posix newlines and replaces spaces with tabs.
    """
    patt: bytes = rb"[^\S\n]+"
    regexp = re.compile(patt)
    return convert_newlines(fname, in_place, tmp_dir, tmp_prefix, regexp=regexp)


def iter_headers(fname_or_file_prefix, sep, count=60, comment_designator=None):
    idx = 0
    if isinstance(fname_or_file_prefix, FilePrefix):
        file_iterator = fname_or_file_prefix.line_iterator()
    else:
        file_iterator = compression_utils.get_fileobj(fname_or_file_prefix)
    for line in file_iterator:
        line = line.rstrip("\n\r")
        if comment_designator is not None and comment_designator != "" and line.startswith(comment_designator):
            continue
        yield line.split(sep)
        idx += 1
        if idx == count:
            break


def validate_tabular(fname_or_file_prefix, validate_row, sep, comment_designator=None):
    for row in iter_headers(fname_or_file_prefix, sep, count=-1, comment_designator=comment_designator):
        validate_row(row)


def get_headers(fname_or_file_prefix, sep, count=60, comment_designator=None):
    """
    Returns a list with the first 'count' lines split by 'sep', ignoring lines
    starting with 'comment_designator'

    >>> fname = get_test_fname('complete.bed')
    >>> get_headers(fname,'\\t') == [['chr7', '127475281', '127491632', 'NM_000230', '0', '+', '127486022', '127488767', '0', '3', '29,172,3225,', '0,10713,13126,'], ['chr7', '127486011', '127488900', 'D49487', '0', '+', '127486022', '127488767', '0', '2', '155,490,', '0,2399']]
    True
    >>> fname = get_test_fname('test.gff')
    >>> get_headers(fname, '\\t', count=5, comment_designator='#') == [[''], ['chr7', 'bed2gff', 'AR', '26731313', '26731437', '.', '+', '.', 'score'], ['chr7', 'bed2gff', 'AR', '26731491', '26731536', '.', '+', '.', 'score'], ['chr7', 'bed2gff', 'AR', '26731541', '26731649', '.', '+', '.', 'score'], ['chr7', 'bed2gff', 'AR', '26731659', '26731841', '.', '+', '.', 'score']]
    True
    """
    return list(
        iter_headers(
            fname_or_file_prefix=fname_or_file_prefix, sep=sep, count=count, comment_designator=comment_designator
        )
    )


def is_column_based(fname_or_file_prefix, sep="\t", skip=0):
    """
    Checks whether the file is column based with respect to a separator
    (defaults to tab separator).

    >>> fname = get_test_fname('test.gff')
    >>> is_column_based(fname)
    True
    >>> fname = get_test_fname('test_tab.bed')
    >>> is_column_based(fname)
    True
    >>> is_column_based(fname, sep=' ')
    False
    >>> fname = get_test_fname('test_space.txt')
    >>> is_column_based(fname)
    False
    >>> is_column_based(fname, sep=' ')
    True
    >>> fname = get_test_fname('test_ensembl.tabular')
    >>> is_column_based(fname)
    True
    >>> fname = get_test_fname('test_tab1.tabular')
    >>> is_column_based(fname, sep=' ', skip=0)
    False
    >>> fname = get_test_fname('test_tab1.tabular')
    >>> is_column_based(fname)
    True
    """
    if getattr(fname_or_file_prefix, "binary", None) is True:
        return False

    try:
        headers = get_headers(fname_or_file_prefix, sep, comment_designator="#")[skip:]
    except UnicodeDecodeError:
        return False
    count = 0
    if not headers:
        return False
    for hdr in headers:
        if hdr and hdr != [""]:
            if count:
                if len(hdr) != count:
                    return False
            else:
                count = len(hdr)
                if count < 2:
                    return False
    return count >= 2


def guess_ext(fname_or_file_prefix: Union[str, "FilePrefix"], sniff_order, is_binary=None, auto_decompress=True):
    """
    Returns an extension that can be used in the datatype factory to
    generate a data for the 'fname' file

    >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
    >>> datatypes_registry = example_datatype_registry_for_sample()
    >>> sniff_order = datatypes_registry.sniff_order
    >>> fname = get_test_fname('empty.txt')
    >>> guess_ext(fname, sniff_order)
    'txt'
    >>> fname = get_test_fname('megablast_xml_parser_test1.blastxml')
    >>> guess_ext(fname, sniff_order)
    'blastxml'
    >>> fname = get_test_fname('1.psl')
    >>> guess_ext(fname, sniff_order)
    'psl'
    >>> fname = get_test_fname('2.psl')
    >>> guess_ext(fname, sniff_order)
    'psl'
    >>> fname = get_test_fname('interval.interval')
    >>> guess_ext(fname, sniff_order)
    'interval'
    >>> fname = get_test_fname('interv1.bed')
    >>> guess_ext(fname, sniff_order)
    'bed'
    >>> fname = get_test_fname('test_tab.bed')
    >>> guess_ext(fname, sniff_order)
    'bed'
    >>> fname = get_test_fname('sequence.maf')
    >>> guess_ext(fname, sniff_order)
    'maf'
    >>> fname = get_test_fname('sequence.fasta')
    >>> guess_ext(fname, sniff_order)
    'fasta'
    >>> fname = get_test_fname('1.genbank')
    >>> guess_ext(fname, sniff_order)
    'genbank'
    >>> fname = get_test_fname('1.genbank.gz')
    >>> guess_ext(fname, sniff_order)
    'genbank.gz'
    >>> fname = get_test_fname('file.html')
    >>> guess_ext(fname, sniff_order)
    'html'
    >>> fname = get_test_fname('test.gtf')
    >>> guess_ext(fname, sniff_order)
    'gtf'
    >>> fname = get_test_fname('test.gff')
    >>> guess_ext(fname, sniff_order)
    'gff'
    >>> fname = get_test_fname('gff.gff3')
    >>> guess_ext(fname, sniff_order)
    'gff3'
    >>> fname = get_test_fname('2.txt')
    >>> guess_ext(fname, sniff_order)
    'txt'
    >>> fname = get_test_fname('test_tab2.tabular')
    >>> guess_ext(fname, sniff_order)
    'tabular'
    >>> fname = get_test_fname('3.txt')
    >>> guess_ext(fname, sniff_order)
    'txt'
    >>> fname = get_test_fname('test_tab1.tabular')
    >>> guess_ext(fname, sniff_order)
    'tabular'
    >>> fname = get_test_fname('alignment.lav')
    >>> guess_ext(fname, sniff_order)
    'lav'
    >>> fname = get_test_fname('1.sff')
    >>> guess_ext(fname, sniff_order)
    'sff'
    >>> fname = get_test_fname('1.bam')
    >>> guess_ext(fname, sniff_order)
    'bam'
    >>> fname = get_test_fname('3unsorted.bam')
    >>> guess_ext(fname, sniff_order)
    'unsorted.bam'
    >>> fname = get_test_fname('test.idpdb')
    >>> guess_ext(fname, sniff_order)
    'idpdb'
    >>> fname = get_test_fname('test.mz5')
    >>> guess_ext(fname, sniff_order)
    'h5'
    >>> fname = get_test_fname('issue1818.tabular')
    >>> guess_ext(fname, sniff_order)
    'tabular'
    >>> fname = get_test_fname('drugbank_drugs.cml')
    >>> guess_ext(fname, sniff_order)
    'cml'
    >>> fname = get_test_fname('q.fps')
    >>> guess_ext(fname, sniff_order)
    'fps'
    >>> fname = get_test_fname('drugbank_drugs.inchi')
    >>> guess_ext(fname, sniff_order)
    'inchi'
    >>> fname = get_test_fname('drugbank_drugs.mol2')
    >>> guess_ext(fname, sniff_order)
    'mol2'
    >>> fname = get_test_fname('drugbank_drugs.sdf')
    >>> guess_ext(fname, sniff_order)
    'sdf'
    >>> fname = get_test_fname('5e5z.pdb')
    >>> guess_ext(fname, sniff_order)
    'pdb'
    >>> fname = get_test_fname('Si_uppercase.cell')
    >>> guess_ext(fname, sniff_order)
    'cell'
    >>> fname = get_test_fname('Si_lowercase.cell')
    >>> guess_ext(fname, sniff_order)
    'cell'
    >>> fname = get_test_fname('Si.cif')
    >>> guess_ext(fname, sniff_order)
    'cif'
    >>> fname = get_test_fname('LaMnO3.cif')
    >>> guess_ext(fname, sniff_order)
    'cif'
    >>> fname = get_test_fname('Si.xyz')
    >>> guess_ext(fname, sniff_order)
    'xyz'
    >>> fname = get_test_fname('Si_multi.xyz')
    >>> guess_ext(fname, sniff_order)
    'xyz'
    >>> fname = get_test_fname('Si.extxyz')
    >>> guess_ext(fname, sniff_order)
    'extxyz'
    >>> fname = get_test_fname('Si.castep')
    >>> guess_ext(fname, sniff_order)
    'castep'
    >>> fname = get_test_fname('test.fits')
    >>> guess_ext(fname, sniff_order)
    'fits'
    >>> fname = get_test_fname('Si.param')
    >>> guess_ext(fname, sniff_order)
    'param'
    >>> fname = get_test_fname('Si.den_fmt')
    >>> guess_ext(fname, sniff_order)
    'den_fmt'
    >>> fname = get_test_fname('ethanol.magres')
    >>> guess_ext(fname, sniff_order)
    'magres'
    >>> fname = get_test_fname('mothur_datatypetest_true.mothur.otu')
    >>> guess_ext(fname, sniff_order)
    'mothur.otu'
    >>> fname = get_test_fname('mothur_datatypetest_true.mothur.lower.dist')
    >>> guess_ext(fname, sniff_order)
    'mothur.lower.dist'
    >>> fname = get_test_fname('mothur_datatypetest_true.mothur.square.dist')
    >>> guess_ext(fname, sniff_order)
    'mothur.square.dist'
    >>> fname = get_test_fname('mothur_datatypetest_true.mothur.pair.dist')
    >>> guess_ext(fname, sniff_order)
    'mothur.pair.dist'
    >>> fname = get_test_fname('mothur_datatypetest_true.mothur.freq')
    >>> guess_ext(fname, sniff_order)
    'mothur.freq'
    >>> fname = get_test_fname('mothur_datatypetest_true.mothur.quan')
    >>> guess_ext(fname, sniff_order)
    'mothur.quan'
    >>> fname = get_test_fname('mothur_datatypetest_true.mothur.ref.taxonomy')
    >>> guess_ext(fname, sniff_order)
    'mothur.ref.taxonomy'
    >>> fname = get_test_fname('mothur_datatypetest_true.mothur.axes')
    >>> guess_ext(fname, sniff_order)
    'mothur.axes'
    >>> guess_ext(get_test_fname('infernal_model.cm'), sniff_order)
    'cm'
    >>> fname = get_test_fname('1.gg')
    >>> guess_ext(fname, sniff_order)
    'gg'
    >>> fname = get_test_fname('diamond_db.dmnd')
    >>> guess_ext(fname, sniff_order)
    'dmnd'
    >>> fname = get_test_fname('1.excel.xls')
    >>> guess_ext(fname, sniff_order, is_binary=True)
    'excel.xls'
    >>> fname = get_test_fname('biom2_sparse_otu_table_hdf5.biom2')
    >>> guess_ext(fname, sniff_order)
    'biom2'
    >>> fname = get_test_fname('454Score.pdf')
    >>> guess_ext(fname, sniff_order)
    'pdf'
    >>> fname = get_test_fname('1.obo')
    >>> guess_ext(fname, sniff_order)
    'obo'
    >>> fname = get_test_fname('1.arff')
    >>> guess_ext(fname, sniff_order)
    'arff'
    >>> fname = get_test_fname('1.afg')
    >>> guess_ext(fname, sniff_order)
    'afg'
    >>> fname = get_test_fname('1.owl')
    >>> guess_ext(fname, sniff_order)
    'owl'
    >>> fname = get_test_fname('Acanium.snaphmm')
    >>> guess_ext(fname, sniff_order)
    'snaphmm'
    >>> fname = get_test_fname('wiggle.wig')
    >>> guess_ext(fname, sniff_order)
    'wig'
    >>> fname = get_test_fname('example.iqtree')
    >>> guess_ext(fname, sniff_order)
    'iqtree'
    >>> fname = get_test_fname('1.stockholm')
    >>> guess_ext(fname, sniff_order)
    'stockholm'
    >>> fname = get_test_fname('1.xmfa')
    >>> guess_ext(fname, sniff_order)
    'xmfa'
    >>> fname = get_test_fname('test.blib')
    >>> guess_ext(fname, sniff_order)
    'blib'
    >>> fname = get_test_fname('test_strict_interleaved.phylip')
    >>> guess_ext(fname, sniff_order)
    'phylip'
    >>> fname = get_test_fname('test_relaxed_interleaved.phylip')
    >>> guess_ext(fname, sniff_order)
    'phylip'
    >>> fname = get_test_fname('1.smat')
    >>> guess_ext(fname, sniff_order)
    'smat'
    >>> fname = get_test_fname('1.ttl')
    >>> guess_ext(fname, sniff_order)
    'ttl'
    >>> fname = get_test_fname('1.hdt')
    >>> guess_ext(fname, sniff_order, is_binary=True)
    'hdt'
    >>> fname = get_test_fname('1.phyloxml')
    >>> guess_ext(fname, sniff_order)
    'phyloxml'
    >>> fname = get_test_fname('1.dzi')
    >>> guess_ext(fname, sniff_order)
    'dzi'
    >>> fname = get_test_fname('1.tiff')
    >>> guess_ext(fname, sniff_order)
    'tiff'
    >>> fname = get_test_fname('1.fastqsanger.gz')
    >>> guess_ext(fname, sniff_order)  # See test_datatype_registry for more compressed type tests.
    'fastqsanger.gz'
    >>> fname = get_test_fname('1.mtx')
    >>> guess_ext(fname, sniff_order)
    'mtx'
    >>> fname = get_test_fname('mc_preprocess_summ.metacyto_summary.txt')
    >>> guess_ext(fname, sniff_order)
    'metacyto_summary.txt'
    >>> fname = get_test_fname('Accuri_C6_A01_H2O.fcs')
    >>> guess_ext(fname, sniff_order)
    'fcs'
    >>> fname = get_test_fname('1imzml')
    >>> guess_ext(fname, sniff_order)  # This test case is ensuring doesn't throw exception, actual value could change if non-utf encoding handling improves.
    'data'
    >>> fname = get_test_fname('too_many_comments_gff3.tabular')
    >>> guess_ext(fname, sniff_order)  # It's a VCF but is sniffed as tabular because of the limit on the number of header lines we read
    'tabular'
    """
    file_prefix = _get_file_prefix(fname_or_file_prefix, auto_decompress=auto_decompress)
    file_ext = run_sniffers_raw(file_prefix, sniff_order)

    # Ugly hack for tsv vs tabular sniffing, we want to prefer tabular
    # to tsv but it doesn't have a sniffer - is TSV was sniffed just check
    # if it is an okay tabular and use that instead.
    if file_ext == "tsv":
        if is_column_based(file_prefix, "\t", 1):
            file_ext = "tabular"
    if file_ext is not None:
        return file_ext

    # skip header check if data is already known to be binary
    if file_prefix.binary:
        return file_ext or "binary"
    try:
        get_headers(file_prefix, None)
    except UnicodeDecodeError:
        return "data"  # default data type file extension
    if is_column_based(file_prefix, "\t", 1):
        return "tabular"  # default tabular data type file extension
    return "txt"  # default text data type file extension


def guess_ext_from_file_name(fname, registry, requested_ext="auto"):
    if requested_ext != "auto":
        return requested_ext
    return registry.get_datatype_from_filename(fname).file_ext


class FilePrefix:
    def __init__(self, filename, auto_decompress=True):
        non_utf8_error = None
        compressed_format = None
        contents_header_bytes = None
        contents_header = None  # First MAX_BYTES of the file.
        truncated = False
        # A future direction to optimize sniffing even more for sniffers at the top of the list
        # is to lazy load contents_header based on what interface is requested. For instance instead
        # of returning a StringIO directly in string_io() return an object that reads the contents and
        # populates contents_header while providing a StringIO-like interface until the file is read
        # but then would fallback to native string_io()
        try:
            compressed_format, f = compression_utils.get_fileobj_raw(filename, "rb")
            try:
                contents_header_bytes = f.read(SNIFF_PREFIX_BYTES)
                truncated = len(contents_header_bytes) == SNIFF_PREFIX_BYTES
                contents_header = contents_header_bytes.decode("utf-8")
            finally:
                f.close()
        except UnicodeDecodeError as e:
            non_utf8_error = e

        self.auto_decompress = auto_decompress
        self.truncated = truncated
        self.filename = filename
        self.non_utf8_error = non_utf8_error
        file_magic = magic.detect_from_content(contents_header_bytes)
        self.encoding = file_magic.encoding
        self.mime_type = file_magic.mime_type
        self.compressed_mime_type = None
        self.compressed_encoding = None
        if compressed_format:
            compressed_magic = magic.detect_from_filename(filename)
            self.compressed_mime_type = compressed_magic.mime_type
            self.compressed_encoding = compressed_magic.encoding
        self.compressed_format = compressed_format
        self.contents_header = contents_header
        self.contents_header_bytes = contents_header_bytes
        self._is_binary = None
        self._file_size = None

    @property
    def binary(self):
        if self._is_binary is None:
            self._is_binary = bool({self.mime_type, self.compressed_mime_type} & BINARY_MIMETYPES) or is_binary(
                self.contents_header_bytes
            )
            if (
                not self._is_binary
                and self.encoding == "binary"
                and self.non_utf8_error
                or not self.auto_decompress
                and self.compressed_encoding == "binary"
            ):
                # Try harder ... if we have a non-utf-8 error, the file could be latin-1 encoded,
                # but magic would recognize this and set the encoding appropriately
                self._is_binary = True
        return self._is_binary

    @property
    def file_size(self):
        if self._file_size is None:
            self._file_size = os.path.getsize(self.filename)
        return self._file_size

    def string_io(self) -> io.StringIO:
        if self.non_utf8_error is not None:
            raise self.non_utf8_error
        rval = io.StringIO(self.contents_header)
        return rval

    def text_io(self, *args, **kwargs) -> io.TextIOWrapper:
        return io.TextIOWrapper(io.BytesIO(self.contents_header_bytes), *args, **kwargs)

    def startswith(self, prefix):
        return self.string_io().read(len(prefix)) == prefix

    def line_iterator(self):
        s = self.string_io()
        s_len = len(s.getvalue())
        for line in iter(s.readline, ""):
            if line.endswith("\n") or line.endswith("\r"):
                yield line
            elif s.tell() == s_len and not self.truncated:
                # At the end, return the last line if it wasn't truncated when reading it in.
                yield line

    # Convenience wrappers around contents_header, shielding contents_header means we can
    # potentially do a better job lazy loading this data later on.
    def search(self, pattern):
        return pattern.search(self.contents_header)

    def search_str(self, query_str):
        return query_str in self.contents_header

    def magic_header(self, pattern):
        """
        Unpack header and get first element
        """
        size = struct.calcsize(pattern)
        header_bytes = self.contents_header_bytes[:size]
        if len(header_bytes) < size:
            return None
        return struct.unpack(pattern, header_bytes)[0]

    def startswith_bytes(self, test_bytes):
        return self.contents_header_bytes.startswith(test_bytes)


def _get_file_prefix(filename_or_file_prefix: Union[str, FilePrefix], auto_decompress: bool = True) -> FilePrefix:
    if not isinstance(filename_or_file_prefix, FilePrefix):
        return FilePrefix(filename_or_file_prefix, auto_decompress=auto_decompress)
    return filename_or_file_prefix


def run_sniffers_raw(file_prefix: FilePrefix, sniff_order: Iterable["Data"]):
    """Run through sniffers specified by sniff_order, return None of None match."""
    fname = file_prefix.filename
    file_ext = None
    for datatype in sniff_order:
        """
        Some classes may not have a sniff function, which is ok.  In fact,
        Binary, Data, Tabular and Text are examples of classes that should never
        have a sniff function. Since these classes are default classes, they contain
        few rules to filter out data of other formats, so they should be called
        from this function after all other datatypes in sniff_order have not been
        successfully discovered.
        """
        datatype_compressed = getattr(datatype, "compressed", False)
        if datatype_compressed and not file_prefix.compressed_format and not datatype.file_ext.endswith(".tar"):
            # we don't auto-detect tar as compressed
            continue
        if not datatype_compressed and file_prefix.compressed_format:
            continue
        if file_prefix.binary != datatype.is_binary and not datatype.is_binary == "maybe":
            # Binary detection doesn't match datatype ...
            compressed_data_for_compressed_text_datatype = (
                file_prefix.binary and file_prefix.compressed_format and datatype_compressed and not datatype.is_binary
            )
            if not compressed_data_for_compressed_text_datatype:
                # ... and mismatch is not due to compressed text data for a compressed text datatype
                continue
        try:
            if hasattr(datatype, "sniff_prefix"):
                datatype_compressed_format = getattr(datatype, "compressed_format", None)
                if file_prefix.compressed_format and datatype_compressed_format:
                    # Compare the compressed format detected
                    # to the expected.
                    if file_prefix.compressed_format != datatype_compressed_format:
                        continue
                if datatype.sniff_prefix(file_prefix):
                    file_ext = datatype.file_ext
                    break
            elif hasattr(datatype, "sniff") and datatype.sniff(fname):
                file_ext = datatype.file_ext
                break
        except Exception:
            pass

    return file_ext


def zip_single_fileobj(path: StrPath) -> IO[bytes]:
    z = zipfile.ZipFile(path)
    for name in z.namelist():
        if not name.endswith("/"):
            return z.open(name)
    raise ValueError("No file present in the zip file")


def build_sniff_from_prefix(klass):
    # Build and attach a sniff function to this class (klass) from the sniff_prefix function
    # expected to be defined for the class.
    def auto_sniff(self, filename):
        file_prefix = FilePrefix(filename)
        datatype_compressed = getattr(self, "compressed", False)
        if file_prefix.compressed_format and not datatype_compressed:
            return False
        if datatype_compressed:
            if not file_prefix.compressed_format:
                # This not a compressed file we are looking but the type expects it to be
                # must return False.
                return False

        if hasattr(self, "compressed_format"):
            if self.compressed_format != file_prefix.compressed_format:
                return False
        return self.sniff_prefix(file_prefix)

    klass.sniff = auto_sniff
    return klass


def disable_parent_class_sniffing(klass):
    klass.sniff = lambda self, filename: False
    klass.sniff_prefix = lambda self, file_prefix: False
    return klass


class HandleCompressedFileResponse(NamedTuple):
    is_valid: bool
    ext: str
    uncompressed_path: str
    compressed_type: Optional[str]
    is_compressed: Optional[bool]


def handle_compressed_file(
    file_prefix: FilePrefix,
    datatypes_registry,
    ext: str = "auto",
    tmp_prefix: Optional[str] = "sniff_uncompress_",
    tmp_dir: Optional[str] = None,
    in_place: bool = False,
    check_content: bool = True,
) -> HandleCompressedFileResponse:
    """
    Check uploaded files for compression, check compressed file contents, and uncompress if necessary.

    Supports GZip, BZip2, and the first file in a Zip file.

    For performance reasons, the temporary file used for uncompression is located in the same directory as the
    input/output file. This behavior can be changed with the `tmp_dir` param.

    ``ext`` as returned will only be changed from the ``ext`` input param if the param was an autodetect type (``auto``)
    and the file was sniffed as a keep-compressed datatype.

    ``is_valid`` as returned will only be set if the file is compressed and contains invalid contents (or the first file
    in the case of a zip file), this is so lengthy decompression can be bypassed if there is invalid content in the
    first 32KB. Otherwise the caller should be checking content.
    """
    CHUNK_SIZE = 2**20  # 1Mb
    is_compressed = False
    compressed_type = None
    keep_compressed = False
    is_valid = False
    filename = file_prefix.filename
    uncompressed_path = filename
    tmp_dir = tmp_dir or os.path.dirname(filename)
    check_compressed_function = COMPRESSION_CHECK_FUNCTIONS.get(file_prefix.compressed_format)
    if check_compressed_function:
        is_compressed, is_valid = check_compressed_function(filename, check_content=check_content)
        compressed_type = file_prefix.compressed_format
    if is_compressed and is_valid:
        if ext in AUTO_DETECT_EXTENSIONS:
            # attempt to sniff for a keep-compressed datatype (observing the sniff order)
            sniff_datatypes = filter(lambda d: getattr(d, "compressed", False), datatypes_registry.sniff_order)
            sniffed_ext = run_sniffers_raw(file_prefix, sniff_datatypes)
            if sniffed_ext:
                ext = sniffed_ext
                keep_compressed = True
        else:
            datatype = datatypes_registry.get_datatype_by_extension(ext)
            keep_compressed = getattr(datatype, "compressed", False)
    # don't waste time decompressing if we sniff invalid contents
    if is_compressed and is_valid and file_prefix.auto_decompress and not keep_compressed:
        assert compressed_type  # Tell type checker is_compressed will only be true if compressed_type is also set.
        with tempfile.NamedTemporaryFile(prefix=tmp_prefix, dir=tmp_dir, delete=False) as uncompressed:
            with DECOMPRESSION_FUNCTIONS[compressed_type](filename) as compressed_file:
                # TODO: it'd be ideal to convert to posix newlines and space-to-tab here as well
                try:
                    for chunk in file_reader(compressed_file, CHUNK_SIZE):
                        if not chunk:
                            break
                        uncompressed.write(chunk)
                except OSError as e:
                    os.remove(uncompressed.name)
                    raise OSError(
                        f"Problem uncompressing {compressed_type} data, please try retrieving the data uncompressed: {e}"
                    )
                finally:
                    is_compressed = False
        uncompressed_path = uncompressed.name
        if in_place:
            # Replace the compressed file with the uncompressed file
            shutil.move(uncompressed_path, filename)
            uncompressed_path = filename
    elif not is_compressed or not check_content:
        is_valid = True
    return HandleCompressedFileResponse(is_valid, ext, uncompressed_path, compressed_type, is_compressed)


def handle_uploaded_dataset_file(filename, *args, **kwds) -> str:
    """Legacy wrapper about handle_uploaded_dataset_file_internal for tools using it."""
    file_prefix = FilePrefix(filename)
    return handle_uploaded_dataset_file_internal(file_prefix, *args, **kwds)[0]


class HandleUploadedDatasetFileInternalResponse(NamedTuple):
    ext: str
    converted_path: str
    compressed_type: Optional[str]
    converted_newlines: bool
    converted_spaces: bool


def convert_function(convert_to_posix_lines, convert_spaces_to_tabs) -> ConvertFunction:
    assert convert_to_posix_lines or convert_spaces_to_tabs
    if convert_spaces_to_tabs and convert_to_posix_lines:
        convert_fxn = convert_newlines_sep2tabs
    elif convert_to_posix_lines:
        convert_fxn = convert_newlines
    else:
        convert_fxn = convert_sep2tabs
    return convert_fxn


def handle_uploaded_dataset_file_internal(
    file_prefix: FilePrefix,
    datatypes_registry,
    ext: str = "auto",
    tmp_prefix: Optional[str] = "sniff_upload_",
    tmp_dir: Optional[str] = None,
    in_place: bool = False,
    check_content: bool = True,
    is_binary: Optional[bool] = None,
    uploaded_file_ext: Optional[str] = None,
    convert_to_posix_lines: Optional[bool] = None,
    convert_spaces_to_tabs: Optional[bool] = None,
) -> HandleUploadedDatasetFileInternalResponse:
    is_valid, ext, converted_path, compressed_type, is_compressed = handle_compressed_file(
        file_prefix,
        datatypes_registry,
        ext=ext,
        tmp_prefix=tmp_prefix,
        tmp_dir=tmp_dir,
        in_place=in_place,
        check_content=check_content,
    )
    converted_newlines = False
    converted_spaces = False
    try:
        if not is_valid:
            if is_tar(converted_path):
                raise InappropriateDatasetContentError("TAR file uploads are not supported")
            raise InappropriateDatasetContentError("The uploaded compressed file contains invalid content")

        is_binary = file_prefix.binary
        guessed_ext = ext
        if ext in AUTO_DETECT_EXTENSIONS:
            # TODO: skip this if we haven't actually converted the dataset
            guessed_ext = guess_ext(
                converted_path,
                sniff_order=datatypes_registry.sniff_order,
                auto_decompress=file_prefix.auto_decompress,
            )

        if not is_binary and not is_compressed and (convert_to_posix_lines or convert_spaces_to_tabs):
            # Convert universal line endings to Posix line endings, spaces to tabs (if desired)
            convert_fxn = convert_function(convert_to_posix_lines, convert_spaces_to_tabs)
            line_count, _converted_path, converted_newlines, converted_spaces = convert_fxn(
                converted_path, in_place=in_place, tmp_dir=tmp_dir, tmp_prefix=tmp_prefix
            )
            if not in_place:
                if converted_path and file_prefix.filename != converted_path:
                    os.unlink(converted_path)
                assert _converted_path
                converted_path = _converted_path
            if ext in AUTO_DETECT_EXTENSIONS:
                ext = guess_ext(converted_path, sniff_order=datatypes_registry.sniff_order)
        else:
            ext = guessed_ext

        if not is_binary and check_content and check_html(converted_path):
            raise InappropriateDatasetContentError("The uploaded file contains invalid HTML content")
    except Exception:
        if file_prefix.filename != converted_path:
            os.unlink(converted_path)
        raise
    return HandleUploadedDatasetFileInternalResponse(
        ext, converted_path, compressed_type, converted_newlines, converted_spaces
    )


AUTO_DETECT_EXTENSIONS = ["auto"]  # should 'data' also cause auto detect?


DECOMPRESSION_FUNCTIONS: Dict[str, Callable] = dict(gzip=gzip.GzipFile, bz2=bz2.BZ2File, zip=zip_single_fileobj)


class InappropriateDatasetContentError(Exception):
    pass
