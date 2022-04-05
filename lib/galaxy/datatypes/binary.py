"""Binary classes"""

import binascii
import gzip
import io
import json
import logging
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from json import dumps
from typing import Optional

import h5py
import numpy as np
import pysam
from bx.seq.twobit import (
    TWOBIT_MAGIC_NUMBER,
    TWOBIT_MAGIC_NUMBER_SWAP,
)

from galaxy import util
from galaxy.datatypes import metadata
from galaxy.datatypes.data import (
    Data,
    DatatypeValidation,
    get_file_peek,
)
from galaxy.datatypes.metadata import (
    DictParameter,
    FileParameter,
    ListParameter,
    MetadataElement,
    MetadataParameter,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.text import Html
from galaxy.util import (
    compression_utils,
    nice_size,
    sqlite,
)
from galaxy.util.checkers import (
    is_bz2,
    is_gzip,
)
from . import (
    data,
    dataproviders,
)

log = logging.getLogger(__name__)
# pysam 0.16.0.1 emits logs containing the word 'Error', this can confuse the stdout/stderr checkers.
# Can be be removed once https://github.com/pysam-developers/pysam/issues/939 is resolved.
pysam.set_verbosity(0)

# Currently these supported binary data types must be manually set on upload


class Binary(data.Data):
    """Binary data"""

    edam_format = "format_2333"
    file_ext = "binary"

    @staticmethod
    def register_sniffable_binary_format(data_type, ext, type_class):
        """Deprecated method."""

    @staticmethod
    def register_unsniffable_binary_ext(ext):
        """Deprecated method."""

    def set_peek(self, dataset, **kwd):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = "binary data"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return "application/octet-stream"


class Ab1(Binary):
    """Class describing an ab1 binary sequence file"""

    file_ext = "ab1"
    edam_format = "format_3000"
    edam_data = "data_0924"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary ab1 sequence file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary ab1 sequence file ({nice_size(dataset.get_size())})"


class Idat(Binary):
    """Binary data in idat format"""

    file_ext = "idat"
    edam_format = "format_2058"
    edam_data = "data_2603"

    def sniff(self, filename):
        try:
            header = open(filename, "rb").read(4)
            if header == b"IDAT":
                return True
            return False
        except Exception:
            return False


class Cel(Binary):
    """Cel File format described at:
    http://media.affymetrix.com/support/developer/powertools/changelog/gcos-agcc/cel.html
    """

    # cel 3 is a text format
    is_binary = "maybe"  # type: ignore[assignment]  # https://github.com/python/mypy/issues/8796
    file_ext = "cel"
    edam_format = "format_1638"
    edam_data = "data_3110"
    MetadataElement(
        name="version", default="3", desc="Version", readonly=True, visible=True, optional=True, no_value="3"
    )

    def sniff(self, filename):
        """
        Try to guess if the file is a Cel file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('affy_v_agcc.cel')
        >>> Cel().sniff(fname)
        True
        >>> fname = get_test_fname('affy_v_3.cel')
        >>> Cel().sniff(fname)
        True
        >>> fname = get_test_fname('affy_v_4.cel')
        >>> Cel().sniff(fname)
        True
        >>> fname = get_test_fname('test.gal')
        >>> Cel().sniff(fname)
        False
        """
        with open(filename, "rb") as handle:
            header_bytes = handle.read(8)
        found_cel_4 = False
        found_cel_3 = False
        found_cel_agcc = False
        if struct.unpack("<ii", header_bytes[:9]) == (64, 4):
            found_cel_4 = True
        elif struct.unpack(">bb", header_bytes[:2]) == (59, 1):
            found_cel_agcc = True
        elif header_bytes.decode("utf8", errors="ignore").startswith("[CEL]"):
            found_cel_3 = True
        return found_cel_3 or found_cel_4 or found_cel_agcc

    def set_meta(self, dataset, **kwd):
        """
        Set metadata for Cel file.
        """
        with open(dataset.file_name, "rb") as handle:
            header_bytes = handle.read(8)
        if struct.unpack("<ii", header_bytes[:9]) == (64, 4):
            dataset.metadata.version = "4"
        elif struct.unpack(">bb", header_bytes[:2]) == (59, 1):
            dataset.metadata.version = "agcc"
        elif header_bytes.decode("utf8", errors="ignore").startswith("[CEL]"):
            dataset.metadata.version = "3"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.blurb = f"Cel version: {dataset.metadata.version}"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class MashSketch(Binary):
    """
    Mash Sketch file.
    Sketches are used by the MinHash algorithm to allow fast distance estimations
    with low storage and memory requirements. To make a sketch, each k-mer in a sequence
    is hashed, which creates a pseudo-random identifier. By sorting these identifiers (hashes),
    a small subset from the top of the sorted list can represent the entire sequence (these are min-hashes).
    The more similar another sequence is, the more min-hashes it is likely to share.
    """

    file_ext = "msh"
    # example data is actually text, maybe text would be a better base
    is_binary = "maybe"  # type: ignore[assignment]  # https://github.com/python/mypy/issues/8796


class CompressedArchive(Binary):
    """
    Class describing an compressed binary file
    This class can be sublass'ed to implement archive filetypes that will not be unpacked by upload.py.
    """

    file_ext = "compressed_archive"
    compressed = True

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Compressed binary file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Compressed binary file ({nice_size(dataset.get_size())})"


class Meryldb(CompressedArchive):
    """MerylDB is a tar.gz archive, with 128 files. 64 data files and 64 index files."""

    file_ext = "meryldb"

    def sniff(self, filename):
        """
        Try to guess if the file is a Cel file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('affy_v_agcc.cel')
        >>> Meryldb().sniff(fname)
        False
        >>> fname = get_test_fname('read-db.meryldb')
        >>> Meryldb().sniff(fname)
        True
        """
        try:
            if filename and tarfile.is_tarfile(filename):
                with tarfile.open(filename, "r") as temptar:
                    _tar_content = temptar.getnames()
                    # 64 data files ad 64 indices + 2 folders
                    if len(_tar_content) == 130:
                        if len([_ for _ in _tar_content if _.endswith(".merylIndex")]) == 64:
                            return True
        except Exception as e:
            log.warning("%s, sniff Exception: %s", self, e)
        return False


class Bref3(Binary):
    """Bref3 format is a binary format for storing phased, non-missing genotypes for a list of samples."""

    file_ext = "bref3"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = binascii.unhexlify("7a8874f400156272")

    def sniff_prefix(self, sniff_prefix):
        return sniff_prefix.startswith_bytes(self._magic)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary bref3 file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary bref3 file ({nice_size(dataset.get_size())})"


class DynamicCompressedArchive(CompressedArchive):

    compressed_format: str
    uncompressed_datatype_instance: Data

    def matches_any(self, target_datatypes) -> bool:
        """Treat two aspects of compressed datatypes separately."""
        compressed_target_datatypes = []
        uncompressed_target_datatypes = []

        for target_datatype in target_datatypes:
            if (
                hasattr(target_datatype, "uncompressed_datatype_instance")
                and target_datatype.compressed_format == self.compressed_format
            ):
                uncompressed_target_datatypes.append(target_datatype.uncompressed_datatype_instance)
            else:
                compressed_target_datatypes.append(target_datatype)

        # TODO: Add gz and bz2 as proper datatypes and use those instances instead of
        # CompressedArchive() in the following check.
        if not hasattr(self, "uncompressed_datatype_instance"):
            raise Exception("Missing 'uncompressed_datatype_instance' attribute.")
        else:
            return self.uncompressed_datatype_instance.matches_any(
                uncompressed_target_datatypes
            ) or CompressedArchive().matches_any(compressed_target_datatypes)


class GzDynamicCompressedArchive(DynamicCompressedArchive):
    compressed_format = "gzip"


class Bz2DynamicCompressedArchive(DynamicCompressedArchive):
    compressed_format = "bz2"


class CompressedZipArchive(CompressedArchive):
    """
    Class describing an compressed binary file
    This class can be sublass'ed to implement archive filetypes that will not be unpacked by upload.py.
    """

    file_ext = "zip"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Compressed zip file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Compressed zip file ({nice_size(dataset.get_size())})"

    def sniff(self, filename):
        with zipfile.ZipFile(filename) as zf:
            zf_files = zf.infolist()
            count = 0
            for f in zf_files:
                if f.file_size > 0 and not f.filename.startswith("__MACOSX/") and not f.filename.endswith(".DS_Store"):
                    count += 1
                if count > 1:
                    return True


class GenericAsn1Binary(Binary):
    """Class for generic ASN.1 binary format"""

    file_ext = "asn1-binary"
    edam_format = "format_1966"
    edam_data = "data_0849"


class _BamOrSam:
    """
    Helper class to set the metadata common to sam and bam files
    """

    def set_meta(self, dataset, overwrite=True, **kwd):
        try:
            bam_file = pysam.AlignmentFile(dataset.file_name, mode="rb")
            # TODO: Reference names, lengths, read_groups and headers can become very large, truncate when necessary
            dataset.metadata.reference_names = list(bam_file.references)
            dataset.metadata.reference_lengths = list(bam_file.lengths)
            dataset.metadata.bam_header = dict(bam_file.header.items())
            dataset.metadata.read_groups = [
                read_group["ID"] for read_group in dataset.metadata.bam_header.get("RG", []) if "ID" in read_group
            ]
            dataset.metadata.sort_order = dataset.metadata.bam_header.get("HD", {}).get("SO", None)
            dataset.metadata.bam_version = dataset.metadata.bam_header.get("HD", {}).get("VN", None)
        except Exception:
            # Per Dan, don't log here because doing so will cause datasets that
            # fail metadata to end in the error state
            pass


class BamNative(CompressedArchive, _BamOrSam):
    """Class describing a BAM binary file that is not necessarily sorted"""

    edam_format = "format_2572"
    edam_data = "data_0863"
    file_ext = "unsorted.bam"
    sort_flag: Optional[str] = None

    MetadataElement(name="columns", default=12, desc="Number of columns", readonly=True, visible=False, no_value=0)
    MetadataElement(
        name="column_types",
        default=["str", "int", "str", "int", "int", "str", "str", "int", "int", "str", "str", "str"],
        desc="Column types",
        param=metadata.ColumnTypesParameter,
        readonly=True,
        visible=False,
        no_value=[],
    )
    MetadataElement(
        name="column_names",
        default=["QNAME", "FLAG", "RNAME", "POS", "MAPQ", "CIGAR", "MRNM", "MPOS", "ISIZE", "SEQ", "QUAL", "OPT"],
        desc="Column names",
        readonly=True,
        visible=False,
        optional=True,
        no_value=[],
    )

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

    def set_meta(self, dataset, overwrite=True, **kwd):
        _BamOrSam().set_meta(dataset)

    @staticmethod
    def merge(split_files, output_file):
        """
        Merges BAM files

        :param split_files: List of bam file paths to merge
        :param output_file: Write merged bam file to this location
        """
        pysam.merge("-O", "BAM", output_file, *split_files)

    def init_meta(self, dataset, copy_from=None):
        Binary.init_meta(self, dataset, copy_from=copy_from)

    def sniff(self, filename):
        return BamNative.is_bam(filename)

    @classmethod
    def is_bam(cls, filename):
        # BAM is compressed in the BGZF format, and must not be uncompressed in Galaxy.
        # The first 4 bytes of any bam file is 'BAM\1', and the file is binary.
        try:
            header = gzip.open(filename).read(4)
            if header == b"BAM\1":
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary bam alignments file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary bam alignments file ({nice_size(dataset.get_size())})"

    def to_archive(self, dataset, name=""):
        rel_paths = []
        file_paths = []
        rel_paths.append(f"{name or dataset.file_name}.{dataset.extension}")
        file_paths.append(dataset.file_name)
        rel_paths.append(f"{name or dataset.file_name}.{dataset.extension}.bai")
        file_paths.append(dataset.metadata.bam_index.file_name)
        return zip(file_paths, rel_paths)

    def groom_dataset_content(self, file_name):
        """
        Ensures that the BAM file contents are coordinate-sorted.  This function is called
        on an output dataset after the content is initially generated.
        """
        # Use pysam to sort the BAM file
        # This command may also creates temporary files <out.prefix>.%d.bam when the
        # whole alignment cannot fit into memory.
        # do this in a unique temp directory, because of possible <out.prefix>.%d.bam temp files
        if not self.dataset_content_needs_grooming(file_name):
            # Don't re-sort if already sorted
            return
        tmp_dir = tempfile.mkdtemp()
        tmp_sorted_dataset_file_name_prefix = os.path.join(tmp_dir, "sorted")
        sorted_file_name = f"{tmp_sorted_dataset_file_name_prefix}.bam"
        slots = os.environ.get("GALAXY_SLOTS", 1)
        sort_args = []
        if self.sort_flag:
            sort_args = [self.sort_flag]
        sort_args.extend(
            [f"-@{slots}", file_name, "-T", tmp_sorted_dataset_file_name_prefix, "-O", "BAM", "-o", sorted_file_name]
        )
        try:
            pysam.sort(*sort_args)
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise
        # Move samtools_created_sorted_file_name to our output dataset location
        shutil.move(sorted_file_name, file_name)
        # Remove temp file and empty temporary directory
        os.rmdir(tmp_dir)

    def get_chunk(self, trans, dataset, offset=0, ck_size=None):
        if not offset == -1:
            try:
                with pysam.AlignmentFile(dataset.file_name, "rb", check_sq=False) as bamfile:
                    ck_size = 300  # 300 lines
                    ck_data = ""
                    header_line_count = 0
                    if offset == 0:
                        ck_data = bamfile.text.replace("\t", " ")
                        header_line_count = bamfile.text.count("\n")
                    else:
                        bamfile.seek(offset)
                    for line_number, alignment in enumerate(bamfile):
                        # return only Header lines if 'header_line_count' exceeds 'ck_size'
                        # FIXME: Can be problematic if bam has million lines of header
                        offset = bamfile.tell()
                        if (line_number + header_line_count) > ck_size:
                            break
                        else:
                            bamline = alignment.tostring(bamfile)
                            # Galaxy display each tag as separate column because 'tostring()' funcition put tabs in between each tag of tags column.
                            # Below code will remove spaces between each tag.
                            bamline_modified = ("\t").join(bamline.split()[:11] + [(" ").join(bamline.split()[11:])])
                            ck_data = f"{ck_data}\n{bamline_modified}"
                    else:
                        # Nothing to enumerate; we've either offset to the end
                        # of the bamfile, or there is no data. (possible with
                        # header-only bams)
                        offset = -1
            except Exception as e:
                offset = -1
                ck_data = f"Could not display BAM file, error was:\n{e}"
        else:
            ck_data = ""
            offset = -1
        return dumps({"ck_data": util.unicodify(ck_data), "offset": offset})

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, offset=None, ck_size=None, **kwd):
        headers = kwd.get("headers", {})
        preview = util.string_as_bool(preview)
        if offset is not None:
            return self.get_chunk(trans, dataset, offset, ck_size), headers
        elif to_ext or not preview:
            return super().display_data(trans, dataset, preview, filename, to_ext, **kwd)
        else:
            column_names = dataset.metadata.column_names
            if not column_names:
                column_names = []
            column_types = dataset.metadata.column_types
            if not column_types:
                column_types = []
            column_number = dataset.metadata.columns
            if column_number is None:
                column_number = 1
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

    def validate(self, dataset, **kwd):
        if not BamNative.is_bam(dataset.file_name):
            return DatatypeValidation.invalid("This dataset does not appear to a BAM file.")
        elif self.dataset_content_needs_grooming(dataset.file_name):
            return DatatypeValidation.invalid(
                "This BAM file does not appear to have the correct sorting for declared datatype."
            )
        return DatatypeValidation.validated()


@dataproviders.decorators.has_dataproviders
class Bam(BamNative):
    """Class describing a BAM binary file"""

    edam_format = "format_2572"
    edam_data = "data_0863"
    file_ext = "bam"
    track_type = "ReadTrack"
    data_sources = {"data": "bai", "index": "bigwig"}

    MetadataElement(
        name="bam_index",
        desc="BAM Index File",
        param=metadata.FileParameter,
        file_ext="bai",
        readonly=True,
        visible=False,
        optional=True,
    )
    MetadataElement(
        name="bam_csi_index",
        desc="BAM CSI Index File",
        param=metadata.FileParameter,
        file_ext="bam.csi",
        readonly=True,
        visible=False,
        optional=True,
    )

    def get_index_flag(self, file_name):
        """
        Return pysam flag for bai index (default) or csi index (contig size > (2**29 - 1) )
        """
        index_flag = "-b"  # bai index
        try:
            with pysam.AlignmentFile(file_name) as alignment_file:
                if max(alignment_file.header.lengths) > (2**29) - 1:
                    index_flag = "-c"  # csi index
        except Exception:
            # File may not have a header, that's OK
            pass
        return index_flag

    def dataset_content_needs_grooming(self, file_name):
        """
        Check if file_name is a coordinate-sorted BAM file
        """
        # The best way to ensure that BAM files are coordinate-sorted and indexable
        # is to actually index them.
        index_flag = self.get_index_flag(file_name)
        index_name = tempfile.NamedTemporaryFile(prefix="bam_index").name
        try:
            # If pysam fails to index a file it will write to stderr,
            # and this causes the set_meta script to fail. So instead
            # we start another process and discard stderr.
            if index_flag == "-b":
                # IOError: No such file or directory: '-b' if index_flag is set to -b (pysam 0.15.4)
                cmd = [
                    "python",
                    "-c",
                    f"import pysam; pysam.set_verbosity(0); pysam.index('{file_name}', '{index_name}')",
                ]
            else:
                cmd = [
                    "python",
                    "-c",
                    f"import pysam; pysam.set_verbosity(0); pysam.index('{index_flag}', '{file_name}', '{index_name}')",
                ]
            with open(os.devnull, "w") as devnull:
                subprocess.check_call(cmd, stderr=devnull, shell=False)
            needs_sorting = False
        except subprocess.CalledProcessError:
            needs_sorting = True
        try:
            os.unlink(index_name)
        except Exception:
            pass
        return needs_sorting

    def set_meta(self, dataset, overwrite=True, **kwd):
        # These metadata values are not accessible by users, always overwrite
        super().set_meta(dataset=dataset, overwrite=overwrite, **kwd)
        index_flag = self.get_index_flag(dataset.file_name)
        if index_flag == "-b":
            spec_key = "bam_index"
            index_file = dataset.metadata.bam_index
        else:
            spec_key = "bam_csi_index"
            index_file = dataset.metadata.bam_csi_index
        if not index_file:
            index_file = dataset.metadata.spec[spec_key].param.new_file(dataset=dataset)
        if index_flag == "-b":
            # IOError: No such file or directory: '-b' if index_flag is set to -b (pysam 0.15.4)
            pysam.index(dataset.file_name, index_file.file_name)
        else:
            pysam.index(index_flag, dataset.file_name, index_file.file_name)
        dataset.metadata.bam_index = index_file

    def sniff(self, file_name):
        return super().sniff(file_name) and not self.dataset_content_needs_grooming(file_name)

    # ------------- Dataproviders
    # pipe through samtools view
    # ALSO: (as Sam)
    # bam does not use '#' to indicate comments/headers - we need to strip out those headers from the std. providers
    # TODO:?? seems like there should be an easier way to do/inherit this - metadata.comment_char?
    # TODO: incorporate samtools options to control output: regions first, then flags, etc.
    @dataproviders.decorators.dataprovider_factory("line", dataproviders.line.FilteredLineDataProvider.settings)
    def line_dataprovider(self, dataset, **settings):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        settings["comment_char"] = "@"
        return dataproviders.line.FilteredLineDataProvider(samtools_source, **settings)

    @dataproviders.decorators.dataprovider_factory("regex-line", dataproviders.line.RegexLineDataProvider.settings)
    def regex_line_dataprovider(self, dataset, **settings):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        settings["comment_char"] = "@"
        return dataproviders.line.RegexLineDataProvider(samtools_source, **settings)

    @dataproviders.decorators.dataprovider_factory("column", dataproviders.column.ColumnarDataProvider.settings)
    def column_dataprovider(self, dataset, **settings):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        settings["comment_char"] = "@"
        return dataproviders.column.ColumnarDataProvider(samtools_source, **settings)

    @dataproviders.decorators.dataprovider_factory("dict", dataproviders.column.DictDataProvider.settings)
    def dict_dataprovider(self, dataset, **settings):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        settings["comment_char"] = "@"
        return dataproviders.column.DictDataProvider(samtools_source, **settings)

    # these can't be used directly - may need BamColumn, BamDict (Bam metadata -> column/dict)
    # OR - see genomic_region_dataprovider
    # @dataproviders.decorators.dataprovider_factory('dataset-column', dataproviders.column.ColumnarDataProvider.settings)
    # def dataset_column_dataprovider(self, dataset, **settings):
    #    settings['comment_char'] = '@'
    #    return super().dataset_column_dataprovider(dataset, **settings)

    # @dataproviders.decorators.dataprovider_factory('dataset-dict', dataproviders.column.DictDataProvider.settings)
    # def dataset_dict_dataprovider(self, dataset, **settings):
    #    settings['comment_char'] = '@'
    #    return super().dataset_dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("header", dataproviders.line.RegexLineDataProvider.settings)
    def header_dataprovider(self, dataset, **settings):
        # in this case we can use an option of samtools view to provide just what we need (w/o regex)
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset, "-H")
        return dataproviders.line.RegexLineDataProvider(samtools_source, **settings)

    @dataproviders.decorators.dataprovider_factory("id-seq-qual", dataproviders.column.DictDataProvider.settings)
    def id_seq_qual_dataprovider(self, dataset, **settings):
        settings["indeces"] = [0, 9, 10]
        settings["column_types"] = ["str", "str", "str"]
        settings["column_names"] = ["id", "seq", "qual"]
        return self.dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("genomic-region", dataproviders.column.ColumnarDataProvider.settings)
    def genomic_region_dataprovider(self, dataset, **settings):
        # GenomicRegionDataProvider currently requires a dataset as source - may not be necc.
        # TODO:?? consider (at least) the possible use of a kwarg: metadata_source (def. to source.dataset),
        #   or remove altogether...
        # samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        # return dataproviders.dataset.GenomicRegionDataProvider(samtools_source, metadata_source=dataset,
        #                                                        2, 3, 3, **settings)

        # instead, set manually and use in-class column gen
        settings["indeces"] = [2, 3, 3]
        settings["column_types"] = ["str", "int", "int"]
        return self.column_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory(
        "genomic-region-dict", dataproviders.column.DictDataProvider.settings
    )
    def genomic_region_dict_dataprovider(self, dataset, **settings):
        settings["indeces"] = [2, 3, 3]
        settings["column_types"] = ["str", "int", "int"]
        settings["column_names"] = ["chrom", "start", "end"]
        return self.dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("samtools")
    def samtools_dataprovider(self, dataset, **settings):
        """Generic samtools interface - all options available through settings."""
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return dataproviders.dataset.SamtoolsDataProvider(dataset_source, **settings)


class ProBam(Bam):
    """Class describing a BAM binary file - extended for proteomics data"""

    edam_format = "format_3826"
    edam_data = "data_0863"
    file_ext = "probam"


class BamInputSorted(BamNative):
    """
    A class for BAM files that can formally be unsorted or queryname sorted.
    Alignments are either ordered based on the order with which the queries appear when producing the alignment,
    or ordered by their queryname.
    This notaby keeps alignments produced by paired end sequencing adjacent.
    """

    sort_flag = "-n"
    file_ext = "qname_input_sorted.bam"

    def sniff(self, file_name):
        # We never want to sniff to this datatype
        return False

    def dataset_content_needs_grooming(self, file_name):
        """
        Groom if the file is coordinate sorted
        """
        # The best way to ensure that BAM files are coordinate-sorted and indexable
        # is to actually index them.
        with pysam.AlignmentFile(filename=file_name) as f:
            # The only sure thing we know here is that the sort order can't be coordinate
            return f.header.get("HD", {}).get("SO") == "coordinate"


class BamQuerynameSorted(BamInputSorted):
    """A class for queryname sorted BAM files."""

    sort_flag = "-n"
    file_ext = "qname_sorted.bam"

    def sniff(self, file_name):
        return BamNative().sniff(file_name) and not self.dataset_content_needs_grooming(file_name)

    def dataset_content_needs_grooming(self, file_name):
        """
        Check if file_name is a queryname-sorted BAM file
        """
        # The best way to ensure that BAM files are coordinate-sorted and indexable
        # is to actually index them.
        with pysam.AlignmentFile(filename=file_name) as f:
            return f.header.get("HD", {}).get("SO") != "queryname"


class CRAM(Binary):
    file_ext = "cram"
    edam_format = "format_3462"
    edam_data = "data_0863"

    MetadataElement(
        name="cram_version",
        default=None,
        desc="CRAM Version",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=False,
    )
    MetadataElement(
        name="cram_index",
        desc="CRAM Index File",
        param=metadata.FileParameter,
        file_ext="crai",
        readonly=True,
        visible=False,
        optional=True,
    )

    def set_meta(self, dataset, overwrite=True, **kwd):
        major_version, minor_version = self.get_cram_version(dataset.file_name)
        if major_version != -1:
            dataset.metadata.cram_version = f"{str(major_version)}.{str(minor_version)}"

        if not dataset.metadata.cram_index:
            index_file = dataset.metadata.spec["cram_index"].param.new_file(dataset=dataset)
            if self.set_index_file(dataset, index_file):
                dataset.metadata.cram_index = index_file

    def get_cram_version(self, filename):
        try:
            with open(filename, "rb") as fh:
                header = bytearray(fh.read(6))
            return header[4], header[5]
        except Exception as exc:
            log.warning("%s, get_cram_version Exception: %s", self, exc)
            return -1, -1

    def set_index_file(self, dataset, index_file):
        try:
            pysam.index(dataset.file_name, index_file.file_name)
            return True
        except Exception as exc:
            log.warning("%s, set_index_file Exception: %s", self, exc)
            return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "CRAM binary alignment file"
            dataset.blurb = "binary data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff(self, filename):
        try:
            header = open(filename, "rb").read(4)
            if header == b"CRAM":
                return True
            return False
        except Exception:
            return False


class BaseBcf(CompressedArchive):
    edam_format = "format_3020"
    edam_data = "data_3498"


class Bcf(BaseBcf):
    """
    Class describing a (BGZF-compressed) BCF file

    """

    file_ext = "bcf"

    MetadataElement(
        name="bcf_index",
        desc="BCF Index File",
        param=metadata.FileParameter,
        file_ext="csi",
        readonly=True,
        visible=False,
        optional=True,
    )

    def sniff(self, filename):
        # BCF is compressed in the BGZF format, and must not be uncompressed in Galaxy.
        try:
            header = gzip.open(filename).read(3)
            # The first 3 bytes of any BCF file are 'BCF', and the file is binary.
            if header == b"BCF":
                return True
            return False
        except Exception:
            return False

    def set_meta(self, dataset, overwrite=True, **kwd):
        """Creates the index for the BCF file."""
        # These metadata values are not accessible by users, always overwrite
        index_file = dataset.metadata.bcf_index
        if not index_file:
            index_file = dataset.metadata.spec["bcf_index"].param.new_file(dataset=dataset)
        # Create the bcf index
        dataset_symlink = os.path.join(
            os.path.dirname(index_file.file_name),
            "__dataset_%d_%s" % (dataset.id, os.path.basename(index_file.file_name)),
        )
        os.symlink(dataset.file_name, dataset_symlink)
        try:
            cmd = ["python", "-c", f"import pysam.bcftools; pysam.bcftools.index('{dataset_symlink}')"]
            subprocess.check_call(cmd)
            shutil.move(f"{dataset_symlink}.csi", index_file.file_name)
        except Exception as e:
            raise Exception(f"Error setting BCF metadata: {util.unicodify(e)}")
        finally:
            # Remove temp file and symlink
            os.remove(dataset_symlink)
        dataset.metadata.bcf_index = index_file


class BcfUncompressed(BaseBcf):
    """
    Class describing an uncompressed BCF file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('1.bcf_uncompressed')
    >>> BcfUncompressed().sniff(fname)
    True
    >>> fname = get_test_fname('1.bcf')
    >>> BcfUncompressed().sniff(fname)
    False
    """

    file_ext = "bcf_uncompressed"
    compressed = False

    def sniff(self, filename):
        try:
            header = open(filename, mode="rb").read(3)
            # The first 3 bytes of any BCF file are 'BCF', and the file is binary.
            if header == b"BCF":
                return True
            return False
        except Exception:
            return False


class H5(Binary):
    """
    Class describing an HDF5 file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.mz5')
    >>> H5().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> H5().sniff(fname)
    False
    """

    file_ext = "h5"
    edam_format = "format_3590"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = binascii.unhexlify("894844460d0a1a0a")

    def sniff(self, filename):
        # The first 8 bytes of any hdf5 file are 0x894844460d0a1a0a
        try:
            header = open(filename, "rb").read(8)
            if header == self._magic:
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary HDF5 file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary HDF5 file ({nice_size(dataset.get_size())})"


class Loom(H5):
    """
    Class describing a Loom file: http://loompy.org/

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.loom')
    >>> Loom().sniff(fname)
    True
    >>> fname = get_test_fname('test.mz5')
    >>> Loom().sniff(fname)
    False
    """

    file_ext = "loom"
    edam_format = "format_3590"

    MetadataElement(name="title", default="", desc="title", readonly=True, visible=True, no_value="")
    MetadataElement(name="description", default="", desc="description", readonly=True, visible=True, no_value="")
    MetadataElement(name="url", default="", desc="url", readonly=True, visible=True, no_value="")
    MetadataElement(name="doi", default="", desc="doi", readonly=True, visible=True, no_value="")
    MetadataElement(
        name="loom_spec_version", default="", desc="loom_spec_version", readonly=True, visible=True, no_value=""
    )
    MetadataElement(name="creation_date", default=None, desc="creation_date", readonly=True, visible=True)
    MetadataElement(
        name="shape", default=(), desc="shape", param=metadata.ListParameter, readonly=True, visible=True, no_value=()
    )
    MetadataElement(name="layers_count", default=0, desc="layers_count", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="layers_names",
        desc="layers_names",
        default=[],
        param=metadata.SelectParameter,
        multiple=True,
        readonly=True,
    )
    MetadataElement(name="row_attrs_count", default=0, desc="row_attrs_count", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="row_attrs_names",
        desc="row_attrs_names",
        default=[],
        param=metadata.SelectParameter,
        multiple=True,
        readonly=True,
    )
    MetadataElement(name="col_attrs_count", default=0, desc="col_attrs_count", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="col_attrs_names",
        desc="col_attrs_names",
        default=[],
        param=metadata.SelectParameter,
        multiple=True,
        readonly=True,
    )
    MetadataElement(
        name="col_graphs_count", default=0, desc="col_graphs_count", readonly=True, visible=True, no_value=0
    )
    MetadataElement(
        name="col_graphs_names",
        desc="col_graphs_names",
        default=[],
        param=metadata.SelectParameter,
        multiple=True,
        readonly=True,
    )
    MetadataElement(
        name="row_graphs_count", default=0, desc="row_graphs_count", readonly=True, visible=True, no_value=0
    )
    MetadataElement(
        name="row_graphs_names",
        desc="row_graphs_names",
        default=[],
        param=metadata.SelectParameter,
        multiple=True,
        readonly=True,
    )

    def sniff(self, filename):
        if super().sniff(filename):
            with h5py.File(filename, "r") as loom_file:
                # Check the optional but distinctive LOOM_SPEC_VERSION attribute
                if bool(loom_file.attrs.get("LOOM_SPEC_VERSION")):
                    return True
                # Check some mandatory H5 datasets and groups
                for el in ("matrix", "row_attrs", "col_attrs"):
                    if loom_file.get(el) is None:
                        return False
                else:
                    return True
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary Loom file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary Loom file ({nice_size(dataset.get_size())})"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            with h5py.File(dataset.file_name, "r") as loom_file:
                dataset.metadata.title = loom_file.attrs.get("title")
                dataset.metadata.description = loom_file.attrs.get("description")
                dataset.metadata.url = loom_file.attrs.get("url")
                dataset.metadata.doi = loom_file.attrs.get("doi")
                loom_spec_version = loom_file.attrs.get("LOOM_SPEC_VERSION")
                if isinstance(loom_spec_version, np.ndarray):
                    loom_spec_version = loom_spec_version[0]
                    if isinstance(loom_spec_version, bytes):
                        loom_spec_version = loom_spec_version.decode()
                dataset.metadata.loom_spec_version = loom_spec_version
                dataset.creation_date = loom_file.attrs.get("creation_date")
                dataset.metadata.shape = tuple(loom_file["matrix"].shape)

                tmp = list(loom_file.get("layers", {}).keys())
                dataset.metadata.layers_count = len(tmp)
                dataset.metadata.layers_names = tmp

                tmp = list(loom_file["row_attrs"].keys())
                dataset.metadata.row_attrs_count = len(tmp)
                dataset.metadata.row_attrs_names = tmp

                tmp = list(loom_file["col_attrs"].keys())
                dataset.metadata.col_attrs_count = len(tmp)
                dataset.metadata.col_attrs_names = tmp

                # According to the Loom file format specification, col_graphs
                # and row_graphs are mandatory groups, but files created by
                # Bioconductor LoomExperiment do not always have them:
                # https://github.com/Bioconductor/LoomExperiment/issues/7
                tmp = list(loom_file.get("col_graphs", {}).keys())
                dataset.metadata.col_graphs_count = len(tmp)
                dataset.metadata.col_graphs_names = tmp

                tmp = list(loom_file.get("row_graphs", {}).keys())
                dataset.metadata.row_graphs_count = len(tmp)
                dataset.metadata.row_graphs_names = tmp
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)


class Anndata(H5):
    """
    Class describing an HDF5 anndata files: http://anndata.rtfd.io
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> Anndata().sniff(get_test_fname('pbmc3k_tiny.h5ad'))
    True
    >>> Anndata().sniff(get_test_fname('test.mz5'))
    False
    >>> Anndata().sniff(get_test_fname('import.loom.krumsiek11.h5ad'))
    True
    >>> Anndata().sniff(get_test_fname('adata_0_6_small2.h5ad'))
    True
    >>> Anndata().sniff(get_test_fname('adata_0_6_small.h5ad'))
    True
    >>> Anndata().sniff(get_test_fname('adata_0_7_4_small2.h5ad'))
    True
    >>> Anndata().sniff(get_test_fname('adata_0_7_4_small.h5ad'))
    True
    >>> Anndata().sniff(get_test_fname('adata_unk2.h5ad'))
    True
    >>> Anndata().sniff(get_test_fname('adata_unk.h5ad'))
    True
    """

    file_ext = "h5ad"

    MetadataElement(name="title", default="", desc="title", readonly=True, visible=True, no_value="")
    MetadataElement(name="description", default="", desc="description", readonly=True, visible=True, no_value="")
    MetadataElement(name="url", default="", desc="url", readonly=True, visible=True, no_value="")
    MetadataElement(name="doi", default="", desc="doi", readonly=True, visible=True, no_value="")
    MetadataElement(
        name="anndata_spec_version", default="", desc="anndata_spec_version", readonly=True, visible=True, no_value=""
    )
    MetadataElement(name="creation_date", default=None, desc="creation_date", readonly=True, visible=True)
    MetadataElement(name="layers_count", default=0, desc="layers_count", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="layers_names",
        desc="layers_names",
        default=[],
        param=metadata.SelectParameter,
        multiple=True,
        readonly=True,
    )
    MetadataElement(name="row_attrs_count", default=0, desc="row_attrs_count", readonly=True, visible=True, no_value=0)
    # obs_names: Cell1, Cell2, Cell3,...
    # obs_layers: louvain, leidein, isBcell
    # obs_count: number of obs_layers
    # obs_size: number of obs_names
    MetadataElement(name="obs_names", desc="obs_names", default=[], multiple=True, readonly=True)
    MetadataElement(
        name="obs_layers", desc="obs_layers", default=[], param=metadata.SelectParameter, multiple=True, readonly=True
    )
    MetadataElement(name="obs_count", default=0, desc="obs_count", readonly=True, visible=True, no_value=0)
    MetadataElement(name="obs_size", default=-1, desc="obs_size", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="obsm_layers", desc="obsm_layers", default=[], param=metadata.SelectParameter, multiple=True, readonly=True
    )
    MetadataElement(name="obsm_count", default=0, desc="obsm_count", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="raw_var_layers",
        desc="raw_var_layers",
        default=[],
        param=metadata.SelectParameter,
        multiple=True,
        readonly=True,
    )
    MetadataElement(name="raw_var_count", default=0, desc="raw_var_count", readonly=True, visible=True, no_value=0)
    MetadataElement(name="raw_var_size", default=0, desc="raw_var_size", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="var_layers", desc="var_layers", default=[], param=metadata.SelectParameter, multiple=True, readonly=True
    )
    MetadataElement(name="var_count", default=0, desc="var_count", readonly=True, visible=True, no_value=0)
    MetadataElement(name="var_size", default=-1, desc="var_size", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="varm_layers", desc="varm_layers", default=[], param=metadata.SelectParameter, multiple=True, readonly=True
    )
    MetadataElement(name="varm_count", default=0, desc="varm_count", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="uns_layers", desc="uns_layers", default=[], param=metadata.SelectParameter, multiple=True, readonly=True
    )
    MetadataElement(name="uns_count", default=0, desc="uns_count", readonly=True, visible=True, no_value=0)
    MetadataElement(
        name="shape",
        default=(-1, -1),
        desc="shape",
        param=metadata.ListParameter,
        readonly=True,
        visible=True,
        no_value=(0, 0),
    )

    def sniff(self, filename):
        if super().sniff(filename):
            try:
                with h5py.File(filename, "r") as f:
                    return all(attr in f for attr in ["X", "obs", "var"])
            except Exception:
                return False
        return False

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        with h5py.File(dataset.file_name, "r") as anndata_file:
            dataset.metadata.title = anndata_file.attrs.get("title")
            dataset.metadata.description = anndata_file.attrs.get("description")
            dataset.metadata.url = anndata_file.attrs.get("url")
            dataset.metadata.doi = anndata_file.attrs.get("doi")
            dataset.creation_date = anndata_file.attrs.get("creation_date")
            dataset.metadata.shape = anndata_file.attrs.get("shape", dataset.metadata.shape)
            # none of the above appear to work in any dataset tested, but could be useful for
            # future AnnData datasets
            dataset.metadata.layers_count = len(anndata_file)
            dataset.metadata.layers_names = list(anndata_file.keys())

            def _layercountsize(tmp, lennames=0):
                "From TMP and LENNAMES, return layers, their number, and the length of one of the layers (all equal)."
                if hasattr(tmp, "dtype"):
                    layers = list(tmp.dtype.names)
                    count = len(tmp.dtype)
                    size = int(tmp.size)
                else:
                    layers = list(tmp.keys())
                    count = len(layers)
                    size = lennames
                return (layers, count, size)

            if "obs" in dataset.metadata.layers_names:
                tmp = anndata_file["obs"]
                obs_index = None
                if "index" in tmp:
                    obs_index = "index"
                elif "_index" in tmp:
                    obs_index = "_index"
                # Determine cell labels
                if obs_index:
                    dataset.metadata.obs_names = list(tmp[obs_index])
                elif hasattr(tmp, "dtype"):
                    if "index" in tmp.dtype.names:
                        # Yes, we call tmp["index"], and not tmp.dtype["index"]
                        # here, despite the above tests.
                        dataset.metadata.obs_names = list(tmp["index"])
                    elif "_index" in tmp.dtype.names:
                        dataset.metadata.obs_names = list(tmp["_index"])
                    else:
                        log.warning("Could not determine cell labels for %s", self)
                else:
                    log.warning("Could not determine observation index for %s", self)

                x, y, z = _layercountsize(tmp, len(dataset.metadata.obs_names))
                dataset.metadata.obs_layers = x
                dataset.metadata.obs_count = y
                dataset.metadata.obs_size = z

            if "obsm" in dataset.metadata.layers_names:
                tmp = anndata_file["obsm"]
                dataset.metadata.obsm_layers, dataset.metadata.obsm_count, _ = _layercountsize(tmp)

            if "raw.var" in dataset.metadata.layers_names:
                tmp = anndata_file["raw.var"]
                # full set of genes would never need to be previewed
                # dataset.metadata.raw_var_names = tmp["index"]
                x, y, z = _layercountsize(tmp, len(tmp["index"]))
                dataset.metadata.raw_var_layers = x
                dataset.metadata.raw_var_count = y
                dataset.metadata.raw_var_size = z

            if "var" in dataset.metadata.layers_names:
                tmp = anndata_file["var"]
                var_index = None
                if "index" in tmp:
                    var_index = "index"
                elif "_index" in tmp:
                    var_index = "_index"
                # We never use var_names
                # dataset.metadata.var_names = tmp[var_index]
                if var_index:
                    x, y, z = _layercountsize(tmp, len(tmp[var_index]))
                else:
                    # failing to detect a var_index is not an indicator
                    # that the dataset is empty
                    x, y, z = _layercountsize(tmp)

                dataset.metadata.var_layers = x
                dataset.metadata.var_count = y
                dataset.metadata.var_size = z

            if "varm" in dataset.metadata.layers_names:
                tmp = anndata_file["varm"]
                dataset.metadata.varm_layers, dataset.metadata.varm_count, _ = _layercountsize(tmp)

            if "uns" in dataset.metadata.layers_names:
                tmp = anndata_file["uns"]
                dataset.metadata.uns_layers, dataset.metadata.uns_count, _ = _layercountsize(tmp)

            # Resolving the problematic shape parameter
            if "X" in dataset.metadata.layers_names:
                # Shape we determine here due to the non-standard representation of 'X' dimensions
                shape = anndata_file["X"].attrs.get("shape")
                if shape is not None:
                    dataset.metadata.shape = tuple(shape)
                elif hasattr(anndata_file["X"], "shape"):
                    dataset.metadata.shape = tuple(anndata_file["X"].shape)

            if dataset.metadata.shape is None:
                dataset.metadata.shape = (int(dataset.metadata.obs_size), int(dataset.metadata.var_size))

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            tmp = dataset.metadata

            def _makelayerstrings(layer, count, names):
                "Format the layers."
                if layer in tmp.layers_names:
                    return "\n[%s]: %d %s\n    %s" % (
                        layer,
                        count,
                        "layer" if count == 1 else "layers",
                        ", ".join(sorted(names)),
                    )
                return ""

            peekstr = "[n_obs x n_vars]\n    %d x %d" % tuple(tmp.shape)
            peekstr += _makelayerstrings("obs", tmp.obs_count, tmp.obs_layers)
            peekstr += _makelayerstrings("var", tmp.var_count, tmp.var_layers)
            peekstr += _makelayerstrings("obsm", tmp.obsm_count, tmp.obsm_layers)
            peekstr += _makelayerstrings("varm", tmp.varm_count, tmp.varm_layers)
            peekstr += _makelayerstrings("uns", tmp.uns_count, tmp.uns_layers)

            dataset.peek = peekstr
            dataset.blurb = f"Anndata file ({nice_size(dataset.get_size())})"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary Anndata file ({nice_size(dataset.get_size())})"


@build_sniff_from_prefix
class Grib(Binary):
    """
    Class describing an GRIB file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.grib')
    >>> Grib().sniff_prefix(FilePrefix(fname))
    True
    >>> fname = FilePrefix(get_test_fname('interval.interval'))
    >>> Grib().sniff_prefix(fname)
    False
    """

    file_ext = "grib"
    # GRIB not yet in EDAM (work in progress). For now, so set to binary
    edam_format = "format_2333"
    MetadataElement(
        name="grib_edition", default=1, desc="GRIB edition", readonly=True, visible=True, optional=True, no_value=0
    )

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = b"GRIB"

    def sniff_prefix(self, file_prefix: FilePrefix):
        # The first 4 bytes of any GRIB file are GRIB
        try:
            if file_prefix.startswith_bytes(self._magic):
                tmp = file_prefix.contents_header_bytes[4:8]
                _uint8struct = struct.Struct(b">B")
                edition = _uint8struct.unpack_from(tmp, 3)[0]
                if edition == 1 or edition == 2:
                    return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary GRIB file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary GRIB file ({nice_size(dataset.get_size())})"

    def set_meta(self, dataset, **kwd):
        """
        Set the GRIB edition.
        """
        dataset.metadata.grib_edition = self._get_grib_edition(dataset.file_name)

    def _get_grib_edition(self, filename):
        _uint8struct = struct.Struct(b">B")
        edition = 0
        with open(filename, "rb") as f:
            f.seek(4)
            tmp = f.read(4)
            edition = _uint8struct.unpack_from(tmp, 3)[0]
        return edition


@build_sniff_from_prefix
class GmxBinary(Binary):
    """
    Base class for GROMACS binary files - xtc, trr, cpt
    """

    magic_number: Optional[int] = None  # variables to be overwritten in the child class
    file_ext = ""

    def sniff_prefix(self, sniff_prefix):
        # The first 4 bytes of any GROMACS binary file containing the magic number
        return sniff_prefix.magic_header(">1i") == self.magic_number

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = f"Binary GROMACS {self.file_ext} file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary GROMACS {self.file_ext} trajectory file ({nice_size(dataset.get_size())})"


class Trr(GmxBinary):
    """
    Class describing an trr file from the GROMACS suite

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('md.trr')
    >>> Trr().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> Trr().sniff(fname)
    False
    """

    file_ext = "trr"
    magic_number = 1993  # magic number reference: https://github.com/gromacs/gromacs/blob/cec211b2c835ba6e8ea849fb1bf67d7fc19693a4/src/gromacs/fileio/trrio.cpp


class Cpt(GmxBinary):
    """
    Class describing a checkpoint (.cpt) file from the GROMACS suite

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('md.cpt')
    >>> Cpt().sniff(fname)
    True
    >>> fname = get_test_fname('md.trr')
    >>> Cpt().sniff(fname)
    False
    """

    file_ext = "cpt"
    magic_number = 171817  # magic number reference: https://github.com/gromacs/gromacs/blob/cec211b2c835ba6e8ea849fb1bf67d7fc19693a4/src/gromacs/fileio/checkpoint.cpp


class Xtc(GmxBinary):
    """
    Class describing an xtc file from the GROMACS suite

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('md.xtc')
    >>> Xtc().sniff(fname)
    True
    >>> fname = get_test_fname('md.trr')
    >>> Xtc().sniff(fname)
    False
    """

    file_ext = "xtc"
    magic_number = 1995  # reference: https://github.com/gromacs/gromacs/blob/cec211b2c835ba6e8ea849fb1bf67d7fc19693a4/src/gromacs/fileio/xtcio.cpp


class Edr(GmxBinary):
    """
    Class describing an edr file from the GROMACS suite

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('md.edr')
    >>> Edr().sniff(fname)
    True
    >>> fname = get_test_fname('md.trr')
    >>> Edr().sniff(fname)
    False
    """

    file_ext = "edr"
    magic_number = (
        -55555
    )  # reference: https://github.com/gromacs/gromacs/blob/cec211b2c835ba6e8ea849fb1bf67d7fc19693a4/src/gromacs/fileio/enxio.cpp


class Biom2(H5):
    """
    Class describing a biom2 file (http://biom-format.org/documentation/biom_format.html)
    """

    MetadataElement(name="id", default=None, desc="table id", readonly=True, visible=True)
    MetadataElement(name="format_url", default=None, desc="format-url", readonly=True, visible=True)
    MetadataElement(
        name="format_version", default=None, desc="format-version (equal to format)", readonly=True, visible=True
    )
    MetadataElement(name="format", default=None, desc="format (equal to format=version)", readonly=True, visible=True)
    MetadataElement(name="type", default=None, desc="table type", readonly=True, visible=True)
    MetadataElement(name="generated_by", default=None, desc="generated by", readonly=True, visible=True)
    MetadataElement(name="creation_date", default=None, desc="creation date", readonly=True, visible=True)
    MetadataElement(
        name="nnz",
        default=-1,
        desc="nnz: The number of non-zero elements in the table",
        readonly=True,
        visible=True,
        no_value=-1,
    )
    MetadataElement(
        name="shape",
        default=(),
        desc="shape: The number of rows and columns in the dataset",
        readonly=True,
        visible=True,
        no_value=(),
    )

    file_ext = "biom2"
    edam_format = "format_3746"

    def sniff(self, filename):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('biom2_sparse_otu_table_hdf5.biom2')
        >>> Biom2().sniff(fname)
        True
        >>> fname = get_test_fname('test.mz5')
        >>> Biom2().sniff(fname)
        False
        >>> fname = get_test_fname('wiggle.wig')
        >>> Biom2().sniff(fname)
        False
        """
        if super().sniff(filename):
            with h5py.File(filename, "r") as f:
                required_fields = {"id", "format-url", "type", "generated-by", "creation-date", "nnz", "shape"}
                return required_fields.issubset(f.attrs.keys())
        return False

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            with h5py.File(dataset.file_name, "r") as f:
                attributes = f.attrs

                dataset.metadata.id = util.unicodify(attributes["id"])
                dataset.metadata.format_url = util.unicodify(attributes["format-url"])
                if "format-version" in attributes:  # biom 2.1
                    dataset.metadata.format_version = ".".join(str(_) for _ in attributes["format-version"])
                    dataset.metadata.format = dataset.metadata.format_version
                elif "format" in attributes:  # biom 2.0
                    dataset.metadata.format = util.unicodify(attributes["format"])
                    dataset.metadata.format_version = dataset.metadata.format
                dataset.metadata.type = util.unicodify(attributes["type"])
                dataset.metadata.shape = tuple(int(_) for _ in attributes["shape"])
                dataset.metadata.generated_by = util.unicodify(attributes["generated-by"])
                dataset.metadata.creation_date = util.unicodify(attributes["creation-date"])
                dataset.metadata.nnz = int(attributes["nnz"])
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, util.unicodify(e))

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            lines = ["Biom2 (HDF5) file"]
            try:
                with h5py.File(dataset.file_name) as f:
                    for k, v in f.attrs.items():
                        lines.append(f"{k}:  {util.unicodify(v)}")
            except Exception as e:
                log.warning("%s, set_peek Exception: %s", self, util.unicodify(e))
            dataset.peek = "\n".join(lines)
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Biom2 (HDF5) file ({nice_size(dataset.get_size())})"


class Cool(H5):
    """
    Class describing the cool format (https://github.com/mirnylab/cooler)
    """

    file_ext = "cool"

    def sniff(self, filename):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('matrix.cool')
        >>> Cool().sniff(fname)
        True
        >>> fname = get_test_fname('test.mz5')
        >>> Cool().sniff(fname)
        False
        >>> fname = get_test_fname('wiggle.wig')
        >>> Cool().sniff(fname)
        False
        >>> fname = get_test_fname('biom2_sparse_otu_table_hdf5.biom2')
        >>> Cool().sniff(fname)
        False
        """

        MAGIC = "HDF5::Cooler"
        URL = "https://github.com/mirnylab/cooler"

        if super().sniff(filename):
            keys = ["chroms", "bins", "pixels", "indexes"]
            with h5py.File(filename, "r") as handle:
                fmt = util.unicodify(handle.attrs.get("format"))
                url = util.unicodify(handle.attrs.get("format-url"))
                if fmt == MAGIC or url == URL:
                    if not all(name in handle.keys() for name in keys):
                        return False
                    return True
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Cool (HDF5) file for storing genomic interaction data."
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Cool (HDF5) file ({nice_size(dataset.get_size())})."


class MCool(H5):
    """
    Class describing the multi-resolution cool format (https://github.com/mirnylab/cooler)
    """

    file_ext = "mcool"

    def sniff(self, filename):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('matrix.mcool')
        >>> MCool().sniff(fname)
        True
        >>> fname = get_test_fname('matrix.cool')
        >>> MCool().sniff(fname)
        False
        >>> fname = get_test_fname('test.mz5')
        >>> MCool().sniff(fname)
        False
        >>> fname = get_test_fname('wiggle.wig')
        >>> MCool().sniff(fname)
        False
        >>> fname = get_test_fname('biom2_sparse_otu_table_hdf5.biom2')
        >>> MCool().sniff(fname)
        False
        """

        MAGIC = "HDF5::Cooler"
        URL = "https://github.com/mirnylab/cooler"

        if super().sniff(filename):
            keys0 = ["resolutions"]
            with h5py.File(filename, "r") as handle:
                if not all(name in handle.keys() for name in keys0):
                    return False
                res0 = next(iter(handle["resolutions"].keys()))
                keys = ["chroms", "bins", "pixels", "indexes"]
                fmt = util.unicodify(handle["resolutions"][res0].attrs.get("format"))
                url = util.unicodify(handle["resolutions"][res0].attrs.get("format-url"))
                if fmt == MAGIC or url == URL:
                    if not all(name in handle["resolutions"][res0].keys() for name in keys):
                        return False
                    return True
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Multi-resolution Cool (HDF5) file for storing genomic interaction data."
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"MCool (HDF5) file ({nice_size(dataset.get_size())})."


class H5MLM(H5):
    """
    Machine learning model generated by Galaxy-ML.
    """

    file_ext = "h5mlm"
    URL = "https://github.com/goeckslab/Galaxy-ML"

    max_peek_size = 1000  # 1 KB
    max_preview_size = 1000000  # 1 MB

    MetadataElement(
        name="hyper_params",
        desc="Hyperparameter File",
        param=FileParameter,
        file_ext="tabular",
        readonly=True,
        visible=False,
        optional=True,
    )

    def set_meta(self, dataset, overwrite=True, **kwd):
        try:
            spec_key = "hyper_params"
            params_file = dataset.metadata.hyper_params
            if not params_file:
                params_file = dataset.metadata.spec[spec_key].param.new_file(dataset=dataset)
            with h5py.File(dataset.file_name, "r") as handle:
                hyper_params = handle["-model_hyperparameters-"][()]
            hyper_params = json.loads(util.unicodify(hyper_params))
            with open(params_file.file_name, "w") as f:
                f.write("\tParameter\tValue\n")
                for p in hyper_params:
                    f.write("\t".join(p) + "\n")
            dataset.metadata.hyper_params = params_file
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super().sniff(filename):
            keys = ["-model_config-"]
            with h5py.File(filename, "r") as handle:
                if not all(name in handle.keys() for name in keys):
                    return False
                url = util.unicodify(handle.attrs.get("-URL-"))
            if url == self.URL:
                return True
        return False

    def get_repr(self, filename):
        try:
            with h5py.File(filename, "r") as handle:
                repr_ = util.unicodify(handle.attrs.get("-repr-"))
            return repr_
        except Exception as e:
            log.warning("%s, get_repr Except: %s", self, e)
            return ""

    def get_config_string(self, filename):
        try:
            with h5py.File(filename, "r") as handle:
                config = util.unicodify(handle["-model_config-"][()])
            return config
        except Exception as e:
            log.warning("%s, get model configuration Except: %s", self, e)
            return ""

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            repr_ = self.get_repr(dataset.file_name)
            dataset.peek = repr_[: self.max_peek_size]
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "HDF5 Model (%s)" % (nice_size(dataset.get_size()))

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, **kwd):
        headers = kwd.get("headers", {})
        preview = util.string_as_bool(preview)

        if to_ext or not preview:
            to_ext = to_ext or dataset.extension
            return self._serve_raw(dataset, to_ext, headers, **kwd)

        rval = {}
        try:
            with h5py.File(dataset.file_name, "r") as handle:
                rval["Attributes"] = {}
                attributes = handle.attrs
                for k in set(attributes.keys()) - {"-URL-", "-repr-"}:
                    rval["Attributes"][k] = util.unicodify(attributes.get(k))
        except Exception as e:
            log.warning(e)

        config = self.get_config_string(dataset.file_name)
        rval["Config"] = json.loads(config) if config else ""
        rval = json.dumps(rval, sort_keys=True, indent=2)
        rval = rval[: self.max_preview_size]

        repr_ = self.get_repr(dataset.file_name)

        return f"<pre>{repr_}</pre><pre>{rval}</pre>", headers


class LudwigModel(Html):
    """
    Composite datatype that encloses multiple files for a Ludwig trained model.
    """

    composite_type = "auto_primary_file"
    file_ext = "ludwig_model"

    def __init__(self, **kwd):
        super().__init__(**kwd)

        self.add_composite_file("model_hyperparameters.json", description="Model hyperparameters", is_binary=False)
        self.add_composite_file("model_weights", description="Model weights", is_binary=True)
        self.add_composite_file("training_set_metadata.json", description="Training set metadata", is_binary=False)
        self.add_composite_file(
            "training_progress.json", description="Training progress", is_binary=False, optional=True
        )

    def generate_primary_file(self, dataset=None):
        rval = ["<html><head><title>Ludwig Model Composite Dataset.</title></head><p/>"]
        rval.append("<div>This model dataset is composed of the following items:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            description = composite_file.get("description")
            link_text = f"{composite_name} ({description})" if description else composite_name
            opt_text = " (optional)" if composite_file.optional else ""
            rval.append(f'<li><a href="{composite_name}" type="text/plain">{link_text}</a>{opt_text}</li>')
        rval.append("</ul></div></html>")
        return "\n".join(rval)


class HexrdMaterials(H5):
    """
    Class describing a Hexrd Materials file: https://github.com/HEXRD/hexrd

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('hexrd.materials.h5')
    >>> HexrdMaterials().sniff(fname)
    True
    >>> fname = get_test_fname('test.loom')
    >>> HexrdMaterials().sniff(fname)
    False
    """

    file_ext = "hexrd.materials.h5"
    edam_format = "format_3590"

    MetadataElement(
        name="materials", desc="materials", default=[], param=metadata.SelectParameter, multiple=True, readonly=True
    )
    MetadataElement(
        name="SpaceGroupNumber",
        default={},
        param=DictParameter,
        desc="SpaceGroupNumber",
        readonly=True,
        visible=True,
        no_value={},
    )
    MetadataElement(
        name="LatticeParameters",
        default={},
        param=DictParameter,
        desc="LatticeParameters",
        readonly=True,
        visible=True,
        no_value={},
    )

    def sniff(self, filename):
        if super().sniff(filename):
            req = {"AtomData", "Atomtypes", "CrystalSystem", "LatticeParameters"}
            with h5py.File(filename, "r") as mat_file:
                for k in mat_file.keys():
                    if isinstance(mat_file[k], h5py._hl.group.Group) and set(mat_file[k].keys()) >= req:
                        return True
        return False

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            with h5py.File(dataset.file_name, "r") as mat_file:
                dataset.metadata.materials = list(mat_file.keys())
                sgn = dict()
                lp = dict()
                for m in mat_file.keys():
                    if "SpaceGroupNumber" in mat_file[m] and len(mat_file[m]["SpaceGroupNumber"]) > 0:
                        sgn[m] = mat_file[m]["SpaceGroupNumber"][0].item()
                    if "LatticeParameters" in mat_file[m]:
                        lp[m] = mat_file[m]["LatticeParameters"][0:].tolist()
                dataset.metadata.SpaceGroupNumber = sgn
                dataset.metadata.LatticeParameters = lp
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            lines = ["Material SpaceGroup Lattice"]
            if dataset.metadata.materials:
                for m in dataset.metadata.materials:
                    try:
                        lines.append(
                            f"{m} {dataset.metadata.SpaceGroupNumber[m]} {dataset.metadata.LatticeParameters[m]}"
                        )
                    except Exception:
                        continue
            dataset.peek = "\n".join(lines)
            dataset.blurb = f"Materials: {' '.join(dataset.metadata.materials)}"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class Scf(Binary):
    """Class describing an scf binary sequence file"""

    edam_format = "format_1632"
    edam_data = "data_0924"
    file_ext = "scf"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary scf sequence file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary scf sequence file ({nice_size(dataset.get_size())})"


@build_sniff_from_prefix
class Sff(Binary):
    """Standard Flowgram Format (SFF)"""

    edam_format = "format_3284"
    edam_data = "data_0924"
    file_ext = "sff"

    def sniff_prefix(self, sniff_prefix):
        # The first 4 bytes of any sff file is '.sff', and the file is binary. For details
        # about the format, see http://www.ncbi.nlm.nih.gov/Traces/trace.cgi?cmd=show&f=formats&m=doc&s=format
        return sniff_prefix.startswith_bytes(b".sff")

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary sff file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary sff file ({nice_size(dataset.get_size())})"


@build_sniff_from_prefix
class BigWig(Binary):
    """
    Accessing binary BigWig files from UCSC.
    The supplemental info in the paper has the binary details:
    http://bioinformatics.oxfordjournals.org/cgi/content/abstract/btq351v1
    """

    edam_format = "format_3006"
    edam_data = "data_3002"
    file_ext = "bigwig"
    track_type = "LineTrack"
    data_sources = {"data_standalone": "bigwig"}

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = 0x888FFC26
        self._name = "BigWig"

    def sniff_prefix(self, sniff_prefix):
        return sniff_prefix.magic_header("I") == self._magic

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = f"Binary UCSC {self._name} file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary UCSC {self._name} file ({nice_size(dataset.get_size())})"


class BigBed(BigWig):
    """BigBed support from UCSC."""

    edam_format = "format_3004"
    edam_data = "data_3002"
    file_ext = "bigbed"
    data_sources = {"data_standalone": "bigbed"}

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic = 0x8789F2EB
        self._name = "BigBed"


@build_sniff_from_prefix
class TwoBit(Binary):
    """Class describing a TwoBit format nucleotide file"""

    edam_format = "format_3009"
    edam_data = "data_0848"
    file_ext = "twobit"

    def sniff_prefix(self, sniff_prefix):
        magic = sniff_prefix.magic_header(">L")
        return magic == TWOBIT_MAGIC_NUMBER or magic == TWOBIT_MAGIC_NUMBER_SWAP

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary TwoBit format nucleotide file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            return super().set_peek(dataset)

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary TwoBit format nucleotide file ({nice_size(dataset.get_size())})"


@dataproviders.decorators.has_dataproviders
class SQlite(Binary):
    """Class describing a Sqlite database"""

    MetadataElement(
        name="tables", default=[], param=ListParameter, desc="Database Tables", readonly=True, visible=True, no_value=[]
    )
    MetadataElement(
        name="table_columns",
        default={},
        param=DictParameter,
        desc="Database Table Columns",
        readonly=True,
        visible=True,
        no_value={},
    )
    MetadataElement(
        name="table_row_count",
        default={},
        param=DictParameter,
        desc="Database Table Row Count",
        readonly=True,
        visible=True,
        no_value={},
    )
    file_ext = "sqlite"
    edam_format = "format_3621"

    def init_meta(self, dataset, copy_from=None):
        Binary.init_meta(self, dataset, copy_from=copy_from)

    def set_meta(self, dataset, overwrite=True, **kwd):
        try:
            tables = []
            columns = dict()
            rowcounts = dict()
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"
            rslt = c.execute(tables_query).fetchall()
            for table, _ in rslt:
                tables.append(table)
                try:
                    col_query = f"SELECT * FROM {table} LIMIT 0"
                    cur = conn.cursor().execute(col_query)
                    cols = [col[0] for col in cur.description]
                    columns[table] = cols
                except Exception as exc:
                    log.warning("%s, set_meta Exception: %s", self, exc)
            for table in tables:
                try:
                    row_query = f"SELECT count(*) FROM {table}"
                    rowcounts[table] = c.execute(row_query).fetchone()[0]
                except Exception as exc:
                    log.warning("%s, set_meta Exception: %s", self, exc)
            dataset.metadata.tables = tables
            dataset.metadata.table_columns = columns
            dataset.metadata.table_row_count = rowcounts
        except Exception as exc:
            log.warning("%s, set_meta Exception: %s", self, exc)

    def sniff(self, filename):
        # The first 16 bytes of any SQLite3 database file is 'SQLite format 3\0', and the file is binary. For details
        # about the format, see http://www.sqlite.org/fileformat.html
        try:
            header = open(filename, "rb").read(16)
            if header == b"SQLite format 3\0":
                return True
            return False
        except Exception:
            return False

    def sniff_table_names(self, filename, table_names):
        # All table names should be in the schema
        try:
            conn = sqlite.connect(filename)
            c = conn.cursor()
            tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            result = c.execute(tables_query).fetchall()
            result = [_[0] for _ in result]
            for table_name in table_names:
                if table_name not in result:
                    return False
            return True
        except Exception as e:
            log.warning("%s, sniff Exception: %s", self, e)
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "SQLite Database"
            lines = ["SQLite Database"]
            if dataset.metadata.tables:
                for table in dataset.metadata.tables:
                    try:
                        lines.append(f"{table} [{dataset.metadata.table_row_count[table]}]")
                    except Exception:
                        continue
            dataset.peek = "\n".join(lines)
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"SQLite Database ({nice_size(dataset.get_size())})"

    @dataproviders.decorators.dataprovider_factory("sqlite", dataproviders.dataset.SQliteDataProvider.settings)
    def sqlite_dataprovider(self, dataset, **settings):
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return dataproviders.dataset.SQliteDataProvider(dataset_source, **settings)

    @dataproviders.decorators.dataprovider_factory(
        "sqlite-table", dataproviders.dataset.SQliteDataTableProvider.settings
    )
    def sqlite_datatableprovider(self, dataset, **settings):
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return dataproviders.dataset.SQliteDataTableProvider(dataset_source, **settings)

    @dataproviders.decorators.dataprovider_factory("sqlite-dict", dataproviders.dataset.SQliteDataDictProvider.settings)
    def sqlite_datadictprovider(self, dataset, **settings):
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return dataproviders.dataset.SQliteDataDictProvider(dataset_source, **settings)


class GeminiSQLite(SQlite):
    """Class describing a Gemini Sqlite database"""

    MetadataElement(
        name="gemini_version",
        default="0.10.0",
        param=MetadataParameter,
        desc="Gemini Version",
        readonly=True,
        visible=True,
        no_value="0.10.0",
    )
    file_ext = "gemini.sqlite"
    edam_format = "format_3622"
    edam_data = "data_3498"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT version FROM version"
            result = c.execute(tables_query).fetchall()
            for (version,) in result:
                dataset.metadata.gemini_version = version
            # TODO: Can/should we detect even more attributes, such as use of PED file, what was input annotation type, etc.
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = [
                "gene_detailed",
                "gene_summary",
                "resources",
                "sample_genotype_counts",
                "sample_genotypes",
                "samples",
                "variant_impacts",
                "variants",
                "version",
            ]
            return self.sniff_table_names(filename, table_names)
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Gemini SQLite Database, version %s" % (dataset.metadata.gemini_version or "unknown")
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Gemini SQLite Database, version %s" % (dataset.metadata.gemini_version or "unknown")


class ChiraSQLite(SQlite):
    """Class describing a ChiRAViz Sqlite database"""

    file_ext = "chira.sqlite"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

    def sniff(self, filename):
        if super().sniff(filename):
            self.sniff_table_names(filename, ["Chimeras"])
        return False


class CuffDiffSQlite(SQlite):
    """Class describing a CuffDiff SQLite database"""

    MetadataElement(
        name="cuffdiff_version",
        default="2.2.1",
        param=MetadataParameter,
        desc="CuffDiff Version",
        readonly=True,
        visible=True,
        no_value="2.2.1",
    )
    MetadataElement(
        name="genes", default=[], param=MetadataParameter, desc="Genes", readonly=True, visible=True, no_value=[]
    )
    MetadataElement(
        name="samples", default=[], param=MetadataParameter, desc="Samples", readonly=True, visible=True, no_value=[]
    )
    file_ext = "cuffdiff.sqlite"
    # TODO: Update this when/if there is a specific EDAM format for CuffDiff SQLite data.
    edam_format = "format_3621"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            genes = []
            samples = []
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT value FROM runInfo where param = 'version'"
            result = c.execute(tables_query).fetchall()
            for (version,) in result:
                dataset.metadata.cuffdiff_version = version
            genes_query = "SELECT gene_id, gene_short_name FROM genes ORDER BY gene_short_name"
            result = c.execute(genes_query).fetchall()
            for gene_id, gene_name in result:
                if gene_name is None:
                    continue
                gene = f"{gene_id}: {gene_name}"
                if gene not in genes:
                    genes.append(gene)
            samples_query = "SELECT DISTINCT(sample_name) as sample_name FROM samples ORDER BY sample_name"
            result = c.execute(samples_query).fetchall()
            for (sample_name,) in result:
                if sample_name not in samples:
                    samples.append(sample_name)
            dataset.metadata.genes = genes
            dataset.metadata.samples = samples
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super().sniff(filename):
            # These tables should be in any CuffDiff SQLite output.
            table_names = ["CDS", "genes", "isoforms", "replicates", "runInfo", "samples", "TSS"]
            return self.sniff_table_names(filename, table_names)
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "CuffDiff SQLite Database, version %s" % (dataset.metadata.cuffdiff_version or "unknown")
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "CuffDiff SQLite Database, version %s" % (dataset.metadata.cuffdiff_version or "unknown")


class MzSQlite(SQlite):
    """Class describing a Proteomics Sqlite database"""

    file_ext = "mz.sqlite"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = [
                "DBSequence",
                "Modification",
                "Peaks",
                "Peptide",
                "PeptideEvidence",
                "Score",
                "SearchDatabase",
                "Source",
                "SpectraData",
                "Spectrum",
                "SpectrumIdentification",
            ]
            return self.sniff_table_names(filename, table_names)
        return False


class PQP(SQlite):
    """
    Class describing a Peptide query parameters file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.pqp')
    >>> PQP().sniff(fname)
    True
    >>> fname = get_test_fname('test.osw')
    >>> PQP().sniff(fname)
    False
    """

    file_ext = "pqp"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

    def sniff(self, filename):
        """
        table definition according to https://github.com/grosenberger/OpenMS/blob/develop/src/openms/source/ANALYSIS/OPENSWATH/TransitionPQPFile.cpp#L264
        for now VERSION GENE PEPTIDE_GENE_MAPPING are excluded, since
        there is test data wo these tables, see also here https://github.com/OpenMS/OpenMS/issues/4365
        """
        if not super().sniff(filename):
            return False
        table_names = [
            "COMPOUND",
            "PEPTIDE",
            "PEPTIDE_PROTEIN_MAPPING",
            "PRECURSOR",
            "PRECURSOR_COMPOUND_MAPPING",
            "PRECURSOR_PEPTIDE_MAPPING",
            "PROTEIN",
            "TRANSITION",
            "TRANSITION_PEPTIDE_MAPPING",
            "TRANSITION_PRECURSOR_MAPPING",
        ]
        osw_table_names = ["FEATURE", "FEATURE_MS1", "FEATURE_MS2", "FEATURE_TRANSITION", "RUN"]
        return self.sniff_table_names(filename, table_names) and not self.sniff_table_names(filename, osw_table_names)


class OSW(SQlite):
    """
    Class describing OpenSwath output

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.osw')
    >>> OSW().sniff(fname)
    True
    >>> fname = get_test_fname('test.sqmass')
    >>> OSW().sniff(fname)
    False
    """

    file_ext = "osw"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

    def sniff(self, filename):
        # osw seems to be an extension of pqp (few tables are added)
        # see also here https://github.com/OpenMS/OpenMS/issues/4365
        if not super().sniff(filename):
            return False
        table_names = [
            "COMPOUND",
            "PEPTIDE",
            "PEPTIDE_PROTEIN_MAPPING",
            "PRECURSOR",
            "PRECURSOR_COMPOUND_MAPPING",
            "PRECURSOR_PEPTIDE_MAPPING",
            "PROTEIN",
            "TRANSITION",
            "TRANSITION_PEPTIDE_MAPPING",
            "TRANSITION_PRECURSOR_MAPPING",
            "FEATURE",
            "FEATURE_MS1",
            "FEATURE_MS2",
            "FEATURE_TRANSITION",
            "RUN",
        ]
        return self.sniff_table_names(filename, table_names)


class SQmass(SQlite):
    """
    Class describing a Sqmass database

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.sqmass')
    >>> SQmass().sniff(fname)
    True
    >>> fname = get_test_fname('test.pqp')
    >>> SQmass().sniff(fname)
    False
    """

    file_ext = "sqmass"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = ["CHROMATOGRAM", "PRECURSOR", "RUN", "SPECTRUM", "DATA", "PRODUCT", "RUN_EXTRA"]
            return self.sniff_table_names(filename, table_names)
        return False


class BlibSQlite(SQlite):
    """Class describing a Proteomics Spectral Library Sqlite database"""

    MetadataElement(
        name="blib_version",
        default="1.8",
        param=MetadataParameter,
        desc="Blib Version",
        readonly=True,
        visible=True,
        no_value="1.8",
    )
    file_ext = "blib"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT majorVersion,minorVersion FROM LibInfo"
            (majorVersion, minorVersion) = c.execute(tables_query).fetchall()[0]
            dataset.metadata.blib_version = f"{majorVersion}.{minorVersion}"
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = [
                "IonMobilityTypes",
                "LibInfo",
                "Modifications",
                "RefSpectra",
                "RefSpectraPeakAnnotations",
                "RefSpectraPeaks",
                "ScoreTypes",
                "SpectrumSourceFiles",
            ]
            return self.sniff_table_names(filename, table_names)
        return False


class DlibSQlite(SQlite):
    """
    Class describing a Proteomics Spectral Library Sqlite database
    DLIBs only have the "entries", "metadata", and "peptidetoprotein" tables populated.
    ELIBs have the rest of the tables populated too, such as "peptidequants" or "peptidescores".

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.dlib')
    >>> DlibSQlite().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> DlibSQlite().sniff(fname)
    False
    """

    MetadataElement(
        name="dlib_version",
        default="1.8",
        param=MetadataParameter,
        desc="Dlib Version",
        readonly=True,
        visible=True,
        no_value="1.8",
    )
    file_ext = "dlib"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT Value FROM metadata WHERE Key = 'version'"
            version = c.execute(tables_query).fetchall()[0]
            dataset.metadata.dlib_version = f"{version}"
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = ["entries", "metadata", "peptidetoprotein"]
            return self.sniff_table_names(filename, table_names)
        return False


class ElibSQlite(SQlite):
    """
    Class describing a Proteomics Chromatagram Library Sqlite database
    DLIBs only have the "entries", "metadata", and "peptidetoprotein" tables populated.
    ELIBs have the rest of the tables populated too, such as "peptidequants" or "peptidescores".

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.elib')
    >>> ElibSQlite().sniff(fname)
    True
    >>> fname = get_test_fname('test.dlib')
    >>> ElibSQlite().sniff(fname)
    False
    """

    MetadataElement(
        name="version",
        default="0.1.14",
        param=MetadataParameter,
        desc="Elib Version",
        readonly=True,
        visible=True,
        no_value="0.1.14",
    )
    file_ext = "elib"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT Value FROM metadata WHERE Key = 'version'"
            version = c.execute(tables_query).fetchall()[0]
            dataset.metadata.dlib_version = f"{version}"
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = [
                "entries",
                "fragmentquants",
                "metadata",
                "peptidelocalizations",
                "peptidequants",
                "peptidescores",
                "peptidetoprotein",
                "proteinscores",
                "retentiontimes",
            ]
            if self.sniff_table_names(filename, table_names):
                try:
                    conn = sqlite.connect(filename)
                    c = conn.cursor()
                    row_query = "SELECT count(*) FROM peptidescores"
                    count = c.execute(row_query).fetchone()[0]
                    return int(count) > 0
                except Exception as e:
                    log.warning("%s, sniff Exception: %s", self, e)
        return False


class IdpDB(SQlite):
    """
    Class describing an IDPicker 3 idpDB (sqlite) database

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.idpdb')
    >>> IdpDB().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> IdpDB().sniff(fname)
    False
    """

    file_ext = "idpdb"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = [
                "About",
                "Analysis",
                "AnalysisParameter",
                "PeptideSpectrumMatch",
                "Spectrum",
                "SpectrumSource",
            ]
            return self.sniff_table_names(filename, table_names)
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "IDPickerDB SQLite file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"IDPickerDB SQLite file ({nice_size(dataset.get_size())})"


class GAFASQLite(SQlite):
    """Class describing a GAFA SQLite database"""

    MetadataElement(
        name="gafa_schema_version",
        default="0.3.0",
        param=MetadataParameter,
        desc="GAFA schema version",
        readonly=True,
        visible=True,
        no_value="0.3.0",
    )
    file_ext = "gafa.sqlite"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            version_query = "SELECT version FROM meta"
            results = c.execute(version_query).fetchall()
            if len(results) == 0:
                raise Exception("version not found in meta table")
            elif len(results) > 1:
                raise Exception("Multiple versions found in meta table")
            dataset.metadata.gafa_schema_version = results[0][0]
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = frozenset({"gene", "gene_family", "gene_family_member", "meta", "transcript"})
            return self.sniff_table_names(filename, table_names)
        return False


class NcbiTaxonomySQlite(SQlite):
    """Class describing the NCBI Taxonomy database stored in SQLite as done by rust-ncbitaxonomy"""

    MetadataElement(
        name="ncbitaxonomy_schema_version",
        default="20200501095116",
        param=MetadataParameter,
        desc="ncbitaxonomy schema version",
        readonly=True,
        visible=True,
        no_value="20200501095116",
    )
    MetadataElement(
        name="taxon_count",
        default=[],
        param=MetadataParameter,
        desc="Count of taxa in the taxonomy",
        readonly=True,
        visible=True,
        no_value=[],
    )

    file_ext = "ncbitaxonomy.sqlite"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            version_query = "SELECT version FROM __diesel_schema_migrations ORDER BY run_on DESC LIMIT 1"
            results = c.execute(version_query).fetchall()
            if len(results) == 0:
                raise Exception("version not found in __diesel_schema_migrations table")
            dataset.metadata.ncbitaxonomy_schema_version = results[0][0]
            taxons_query = "SELECT count(name) FROM taxonomy"
            results = c.execute(taxons_query).fetchall()
            if len(results) == 0:
                raise Exception("could not count size of taxonomy table")
            dataset.metadata.taxon_count = results[0][0]
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super().sniff(filename):
            table_names = frozenset({"__diesel_schema_migrations", "taxonomy"})
            return self.sniff_table_names(filename, table_names)
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "NCBI Taxonomy SQLite Database, version {} ({} taxons)".format(
                getattr(dataset.metadata, "ncbitaxonomy_schema_version", "unknown"),
                getattr(dataset.metadata, "taxon_count", "unknown"),
            )
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "NCBI Taxonomy SQLite Database, version {} ({} taxons)".format(
                getattr(dataset.metadata, "ncbitaxonomy_schema_version", "unknown"),
                getattr(dataset.metadata, "taxon_count", "unknown"),
            )


@build_sniff_from_prefix
class Xlsx(Binary):
    """Class for Excel 2007 (xlsx) files"""

    file_ext = "xlsx"
    compressed = True

    def sniff_prefix(self, sniff_prefix):
        # Xlsx is compressed in zip format and must not be uncompressed in Galaxy.
        return sniff_prefix.compressed_mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@build_sniff_from_prefix
class ExcelXls(Binary):
    """Class describing an Excel (xls) file"""

    file_ext = "excel.xls"
    edam_format = "format_3468"

    def sniff_prefix(self, sniff_prefix):
        return sniff_prefix.mime_type == self.get_mime()

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return "application/vnd.ms-excel"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Microsoft Excel XLS file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Microsoft Excel XLS file ({data.nice_size(dataset.get_size())})"


@build_sniff_from_prefix
class Sra(Binary):
    """Sequence Read Archive (SRA) datatype originally from mdshw5/sra-tools-galaxy"""

    file_ext = "sra"

    def sniff_prefix(self, sniff_prefix):
        """The first 8 bytes of any NCBI sra file is 'NCBI.sra', and the file is binary.
        For details about the format, see http://www.ncbi.nlm.nih.gov/books/n/helpsra/SRA_Overview_BK/#SRA_Overview_BK.4_SRA_Data_Structure
        """
        return sniff_prefix.startswith_bytes(b"NCBI.sra")

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary sra file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary sra file ({nice_size(dataset.get_size())})"


@build_sniff_from_prefix
class RData(CompressedArchive):
    """Generic R Data file datatype implementation, i.e. files generated with R's save or save.img function
    see https://www.loc.gov/preservation/digital/formats/fdd/fdd000470.shtml
    and https://cran.r-project.org/doc/manuals/r-patched/R-ints.html#Serialization-Formats

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.rdata')
    >>> RData().sniff(fname)
    True
    >>> from galaxy.util.bunch import Bunch
    >>> dataset = Bunch()
    >>> dataset.metadata = Bunch
    >>> dataset.file_name = fname
    >>> dataset.has_data = lambda: True
    >>> RData().set_meta(dataset)
    >>> dataset.metadata.version
    '3'
    """

    VERSION_2_PREFIX = b"RDX2\nX\n"
    VERSION_3_PREFIX = b"RDX3\nX\n"
    file_ext = "rdata"

    MetadataElement(
        name="version",
        default=None,
        desc="serialisation version",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=False,
    )

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        _, fh = compression_utils.get_fileobj_raw(dataset.file_name, "rb")
        try:
            dataset.metadata.version = self._parse_rdata_header(fh)
        except Exception:
            pass
        finally:
            fh.close()

    def sniff_prefix(self, sniff_prefix):
        return sniff_prefix.startswith_bytes((self.VERSION_2_PREFIX, self.VERSION_3_PREFIX))

    def _parse_rdata_header(self, fh):
        header = fh.read(7)
        if header == self.VERSION_2_PREFIX:
            return "2"
        elif header == self.VERSION_3_PREFIX:
            return "3"
        else:
            raise ValueError()


@build_sniff_from_prefix
class RDS(CompressedArchive):
    """
    File using a serialized R object generated with R's saveRDS function
    see https://cran.r-project.org/doc/manuals/r-patched/R-ints.html#Serialization-Formats

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('int-r3.rds')
    >>> RDS().sniff(fname)
    True
    >>> fname = get_test_fname('int-r4.rds')
    >>> RDS().sniff(fname)
    True
    >>> fname = get_test_fname('int-r3-version2.rds')
    >>> RDS().sniff(fname)
    True
    >>> from galaxy.util.bunch import Bunch
    >>> dataset = Bunch()
    >>> dataset.metadata = Bunch
    >>> dataset.file_name = get_test_fname('int-r4.rds')
    >>> dataset.has_data = lambda: True
    >>> RDS().set_meta(dataset)
    >>> dataset.metadata.version
    '3'
    >>> dataset.metadata.rversion
    '4.1.1'
    >>> dataset.metadata.minrversion
    '3.5.0'
    """

    file_ext = "rds"

    MetadataElement(
        name="version",
        default=None,
        desc="serialisation version",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=False,
    )
    MetadataElement(
        name="rversion",
        default=None,
        desc="R version",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=False,
    )
    MetadataElement(
        name="minrversion",
        default=None,
        desc="minimum R version",
        param=MetadataParameter,
        readonly=False,
        visible=True,
        optional=False,
    )

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        _, fh = compression_utils.get_fileobj_raw(dataset.file_name, "rb")
        try:
            (
                _,
                dataset.metadata.version,
                dataset.metadata.rversion,
                dataset.metadata.minrversion,
            ) = self._parse_rds_header(fh.read(14))
        except Exception:
            pass
        finally:
            fh.close()

    def sniff_prefix(self, sniff_prefix):
        try:
            self._parse_rds_header(sniff_prefix.contents_header_bytes[:14])
        except Exception:
            return False
        return True

    def _parse_rds_header(self, header_bytes):
        """
        get the header info from a rds file
        - starts with b'X\n' or 'A\n'
        - then 3 integers (each 4bytes) encoded with base 10, e.g. b"\x00\x03\x06\x03" for version "3.6.3"
          - the serialization version (2/3)
          - the r version used to generate the file
          - the minimum r version needed to read the file
        """
        header = header_bytes[:2]
        if header == b"X\n":
            mode = "X"
        elif header == b"A\n":
            mode = "A"
        else:
            raise Exception()
        version = header_bytes[2:6]
        rversion = header_bytes[6:10]
        minrversion = header_bytes[10:14]
        version = int("".join(str(_) for _ in version))
        if version not in [2, 3]:
            raise Exception()
        rversion = int("".join(str(_) for _ in rversion))
        minrversion = int("".join(str(_) for _ in minrversion))
        version = ".".join(str(version))
        rversion = ".".join(str(rversion))
        minrversion = ".".join(str(minrversion))
        return mode, version, rversion, minrversion


class OxliBinary(Binary):
    @staticmethod
    def _sniff(filename, oxlitype):
        try:
            with open(filename, "rb") as fileobj:
                header = fileobj.read(4)
                if header == b"OXLI":
                    fileobj.read(1)  # skip the version number
                    ftype = fileobj.read(1)
                    if binascii.hexlify(ftype) == oxlitype:
                        return True
            return False
        except OSError:
            return False


class OxliCountGraph(OxliBinary):
    """
    OxliCountGraph starts with "OXLI" + one byte version number +
    8-bit binary '1'
    Test file generated via::

        load-into-counting.py --n_tables 1 --max-tablesize 1 \\
            oxli_countgraph.oxlicg khmer/tests/test-data/100-reads.fq.bz2

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliCountGraph().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_countgraph.oxlicg")
    >>> OxliCountGraph().sniff(fname)
    True
    """

    file_ext = "oxlicg"

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"01")


class OxliNodeGraph(OxliBinary):
    """
    OxliNodeGraph starts with "OXLI" + one byte version number +
    8-bit binary '2'
    Test file generated via::

        load-graph.py --n_tables 1 --max-tablesize 1 oxli_nodegraph.oxling \\
            khmer/tests/test-data/100-reads.fq.bz2

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliNodeGraph().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_nodegraph.oxling")
    >>> OxliNodeGraph().sniff(fname)
    True
    """

    file_ext = "oxling"

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"02")


class OxliTagSet(OxliBinary):
    """
    OxliTagSet starts with "OXLI" + one byte version number +
    8-bit binary '3'
    Test file generated via::

        load-graph.py --n_tables 1 --max-tablesize 1 oxli_nodegraph.oxling \\
            khmer/tests/test-data/100-reads.fq.bz2;
        mv oxli_nodegraph.oxling.tagset oxli_tagset.oxlits

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliTagSet().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_tagset.oxlits")
    >>> OxliTagSet().sniff(fname)
    True
    """

    file_ext = "oxlits"

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"03")


class OxliStopTags(OxliBinary):
    """
    OxliStopTags starts with "OXLI" + one byte version number +
    8-bit binary '4'
    Test file adapted from khmer 2.0's
    "khmer/tests/test-data/goodversion-k32.stoptags"

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliStopTags().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_stoptags.oxlist")
    >>> OxliStopTags().sniff(fname)
    True
    """

    file_ext = "oxlist"

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"04")


class OxliSubset(OxliBinary):
    """
    OxliSubset starts with "OXLI" + one byte version number +
    8-bit binary '5'
    Test file generated via::

        load-graph.py -k 20 example tests/test-data/random-20-a.fa;
        partition-graph.py example;
        mv example.subset.0.pmap oxli_subset.oxliss

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliSubset().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_subset.oxliss")
    >>> OxliSubset().sniff(fname)
    True
    """

    file_ext = "oxliss"

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"05")


class OxliGraphLabels(OxliBinary):
    """
    OxliGraphLabels starts with "OXLI" + one byte version number +
    8-bit binary '6'
    Test file generated via::

        python -c "from khmer import GraphLabels; \\
            gl = GraphLabels(20, 1e7, 4); \\
            gl.consume_fasta_and_tag_with_labels('tests/test-data/test-labels.fa'); \\
            gl.save_labels_and_tags('oxli_graphlabels.oxligl')"

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliGraphLabels().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_graphlabels.oxligl")
    >>> OxliGraphLabels().sniff(fname)
    True
    """

    file_ext = "oxligl"

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"06")


class PostgresqlArchive(CompressedArchive):
    """
    Class describing a Postgresql database packed into a tar archive

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('postgresql_fake.tar.bz2')
    >>> PostgresqlArchive().sniff(fname)
    True
    >>> fname = get_test_fname('test.fast5.tar')
    >>> PostgresqlArchive().sniff(fname)
    False
    """

    MetadataElement(
        name="version",
        default=None,
        param=MetadataParameter,
        desc="PostgreSQL database version",
        readonly=True,
        visible=True,
    )
    file_ext = "postgresql"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            if dataset and tarfile.is_tarfile(dataset.file_name):
                with tarfile.open(dataset.file_name, "r") as temptar:
                    pg_version_file = temptar.extractfile("postgresql/db/PG_VERSION")
                    dataset.metadata.version = util.unicodify(pg_version_file.read()).strip()
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, util.unicodify(e))

    def sniff(self, filename):
        if filename and tarfile.is_tarfile(filename):
            with tarfile.open(filename, "r") as temptar:
                return "postgresql/db/PG_VERSION" in temptar.getnames()
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = f"PostgreSQL Archive ({nice_size(dataset.get_size())})"
            dataset.blurb = "PostgreSQL version %s" % (dataset.metadata.version or "unknown")
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"PostgreSQL Archive ({nice_size(dataset.get_size())})"


class Fast5Archive(CompressedArchive):
    """
    Class describing a FAST5 archive

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.fast5.tar')
    >>> Fast5Archive().sniff(fname)
    True
    """

    MetadataElement(
        name="fast5_count", default="0", param=MetadataParameter, desc="Read Count", readonly=True, visible=True
    )
    file_ext = "fast5.tar"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            if dataset and tarfile.is_tarfile(dataset.file_name):
                with tarfile.open(dataset.file_name, "r") as temptar:
                    dataset.metadata.fast5_count = sum(1 for f in temptar if f.name.endswith(".fast5"))
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        try:
            if filename and tarfile.is_tarfile(filename):
                with tarfile.open(filename, "r") as temptar:
                    for f in temptar:
                        if not f.isfile():
                            continue
                        if f.name.endswith(".fast5"):
                            return True
                        else:
                            return False
        except Exception as e:
            log.warning("%s, sniff Exception: %s", self, e)
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = f"FAST5 Archive ({nice_size(dataset.get_size())})"
            dataset.blurb = "%s sequences" % (dataset.metadata.fast5_count or "unknown")
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"FAST5 Archive ({nice_size(dataset.get_size())})"


class Fast5ArchiveGz(Fast5Archive):
    """
    Class describing a gzip-compressed FAST5 archive

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.fast5.tar.gz')
    >>> Fast5ArchiveGz().sniff(fname)
    True
    >>> fname = get_test_fname('test.fast5.tar.bz2')
    >>> Fast5ArchiveGz().sniff(fname)
    False
    >>> fname = get_test_fname('test.fast5.tar')
    >>> Fast5ArchiveGz().sniff(fname)
    False
    """

    file_ext = "fast5.tar.gz"

    def sniff(self, filename):
        if not is_gzip(filename):
            return False
        return Fast5Archive.sniff(self, filename)


class Fast5ArchiveBz2(Fast5Archive):
    """
    Class describing a bzip2-compressed FAST5 archive

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.fast5.tar.bz2')
    >>> Fast5ArchiveBz2().sniff(fname)
    True
    >>> fname = get_test_fname('test.fast5.tar.gz')
    >>> Fast5ArchiveBz2().sniff(fname)
    False
    >>> fname = get_test_fname('test.fast5.tar')
    >>> Fast5ArchiveBz2().sniff(fname)
    False
    """

    file_ext = "fast5.tar.bz2"

    def sniff(self, filename):
        if not is_bz2(filename):
            return False
        return Fast5Archive.sniff(self, filename)


class SearchGuiArchive(CompressedArchive):
    """Class describing a SearchGUI archive"""

    MetadataElement(
        name="searchgui_version",
        default="1.28.0",
        param=MetadataParameter,
        desc="SearchGui Version",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="searchgui_major_version",
        default="1",
        param=MetadataParameter,
        desc="SearchGui Major Version",
        readonly=True,
        visible=True,
    )
    file_ext = "searchgui_archive"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            if dataset and zipfile.is_zipfile(dataset.file_name):
                with zipfile.ZipFile(dataset.file_name) as tempzip:
                    if "searchgui.properties" in tempzip.namelist():
                        with tempzip.open("searchgui.properties") as fh:
                            for line in io.TextIOWrapper(fh):
                                if line.startswith("searchgui.version"):
                                    version = line.split("=")[1].strip()
                                    dataset.metadata.searchgui_version = version
                                    dataset.metadata.searchgui_major_version = version.split(".")[0]
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        try:
            if filename and zipfile.is_zipfile(filename):
                with zipfile.ZipFile(filename, "r") as tempzip:
                    is_searchgui = "searchgui.properties" in tempzip.namelist()
                return is_searchgui
        except Exception as e:
            log.warning("%s, sniff Exception: %s", self, e)
        return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "SearchGUI Archive, version %s" % (dataset.metadata.searchgui_version or "unknown")
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "SearchGUI Archive, version %s" % (dataset.metadata.searchgui_version or "unknown")


@build_sniff_from_prefix
class NetCDF(Binary):
    """Binary data in netCDF format"""

    file_ext = "netcdf"
    edam_format = "format_3650"
    edam_data = "data_0943"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary netCDF file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary netCDF file ({nice_size(dataset.get_size())})"

    def sniff_prefix(self, sniff_prefix):
        return sniff_prefix.startswith_bytes(b"CDF")


class Dcd(Binary):
    """
    Class describing a dcd file from the CHARMM molecular simulation program

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test_glucose_vacuum.dcd')
    >>> Dcd().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> Dcd().sniff(fname)
    False
    """

    file_ext = "dcd"
    edam_data = "data_3842"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic_number = b"CORD"

    def sniff(self, filename):
        # Match the keyword 'CORD' at position 4 or 8 - intsize dependent
        # Not checking for endianness
        try:
            with open(filename, "rb") as header:
                intsize = 4
                header.seek(intsize)
                if header.read(intsize) == self._magic_number:
                    return True
                else:
                    intsize = 8
                    header.seek(intsize)
                    if header.read(intsize) == self._magic_number:
                        return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary CHARMM/NAMD dcd file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary CHARMM/NAMD dcd file ({nice_size(dataset.get_size())})"


class Vel(Binary):
    """
    Class describing a velocity file from the CHARMM molecular simulation program

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test_charmm.vel')
    >>> Vel().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> Vel().sniff(fname)
    False
    """

    file_ext = "vel"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic_number = b"VELD"

    def sniff(self, filename):
        # Match the keyword 'VELD' at position 4 or 8 - intsize dependent
        # Not checking for endianness
        try:
            with open(filename, "rb") as header:
                intsize = 4
                header.seek(intsize)
                if header.read(intsize) == self._magic_number:
                    return True
                else:
                    intsize = 8
                    header.seek(intsize)
                    if header.read(intsize) == self._magic_number:
                        return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary CHARMM velocity file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Binary CHARMM velocity file ({nice_size(dataset.get_size())})"


@build_sniff_from_prefix
class DAA(Binary):
    """
    Class describing an DAA (diamond alignment archive) file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('diamond.daa')
    >>> DAA().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> DAA().sniff(fname)
    False
    """

    file_ext = "daa"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = binascii.unhexlify("6be33e6d47530e3c")

    def sniff_prefix(self, sniff_prefix):
        # The first 8 bytes of any daa file are 0x3c0e53476d3ee36b
        return sniff_prefix.startswith_bytes(self._magic)


@build_sniff_from_prefix
class RMA6(Binary):
    """
    Class describing an RMA6 (MEGAN6 read-match archive) file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('diamond.rma6')
    >>> RMA6().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> RMA6().sniff(fname)
    False
    """

    file_ext = "rma6"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = binascii.unhexlify("000003f600000006")

    def sniff_prefix(self, sniff_prefix):
        return sniff_prefix.startswith_bytes(self._magic)


@build_sniff_from_prefix
class DMND(Binary):
    """
    Class describing an DMND file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('diamond_db.dmnd')
    >>> DMND().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> DMND().sniff(fname)
    False
    """

    file_ext = "dmnd"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = binascii.unhexlify("6d18ee15a4f84a02")

    def sniff_prefix(self, sniff_prefix):
        # The first 8 bytes of any dmnd file are 0x24af8a415ee186d
        return sniff_prefix.startswith_bytes(self._magic)


class ICM(Binary):
    """
    Class describing an ICM (interpolated context model) file, used by Glimmer
    """

    file_ext = "icm"
    edam_data = "data_0950"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary ICM (interpolated context model) file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff(self, dataset):
        line = open(dataset).read(100)
        if (
            ">ver = " in line
            and "len = " in line
            and "depth = " in line
            and "periodicity =" in line
            and "nodes = " in line
        ):
            return True

        return False


@build_sniff_from_prefix
class Parquet(Binary):
    """
    Class describing Apache Parquet file (https://parquet.apache.org/)
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('example.parquet')
    >>> Parquet().sniff(fname)
    True
    >>> fname = get_test_fname('test.mz5')
    >>> Parquet().sniff(fname)
    False
    """

    file_ext = "parquet"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = b"PAR1"  # Defined at https://parquet.apache.org/documentation/latest/

    def sniff_prefix(self, sniff_prefix):
        return sniff_prefix.startswith_bytes(self._magic)


class BafTar(CompressedArchive):
    """
    Base class for common behavior of tar files of directory-based raw file formats
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('brukerbaf.d.tar')
    >>> BafTar().sniff(fname)
    True
    >>> fname = get_test_fname('test.fast5.tar')
    >>> BafTar().sniff(fname)
    False
    """

    edam_data = "data_2536"  # mass spectrometry data
    edam_format = "format_3712"  # TODO: add more raw formats to EDAM?
    file_ext = "brukerbaf.d.tar"

    def get_signature_file(self):
        return "analysis.baf"

    def sniff(self, filename):
        if tarfile.is_tarfile(filename):
            with tarfile.open(filename) as rawtar:
                return self.get_signature_file() in [os.path.basename(f).lower() for f in rawtar.getnames()]
        return False

    def get_type(self):
        return "Bruker BAF directory archive"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = self.get_type()
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"{self.get_type()} ({nice_size(dataset.get_size())})"


class YepTar(BafTar):
    """A tar'd up .d directory containing Agilent/Bruker YEP format data"""

    file_ext = "agilentbrukeryep.d.tar"

    def get_signature_file(self):
        return "analysis.yep"

    def get_type(self):
        return "Agilent/Bruker YEP directory archive"


class TdfTar(BafTar):
    """A tar'd up .d directory containing Bruker TDF format data"""

    file_ext = "brukertdf.d.tar"

    def get_signature_file(self):
        return "analysis.tdf"

    def get_type(self):
        return "Bruker TDF directory archive"


class MassHunterTar(BafTar):
    """A tar'd up .d directory containing Agilent MassHunter format data"""

    file_ext = "agilentmasshunter.d.tar"

    def get_signature_file(self):
        return "msscan.bin"

    def get_type(self):
        return "Agilent MassHunter directory archive"


class MassLynxTar(BafTar):
    """A tar'd up .d directory containing Waters MassLynx format data"""

    file_ext = "watersmasslynx.raw.tar"

    def get_signature_file(self):
        return "_func001.dat"

    def get_type(self):
        return "Waters MassLynx RAW directory archive"


class WiffTar(BafTar):
    """
    A tar'd up .wiff/.scan pair containing Sciex WIFF format data
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('some.wiff.tar')
    >>> WiffTar().sniff(fname)
    True
    >>> fname = get_test_fname('brukerbaf.d.tar')
    >>> WiffTar().sniff(fname)
    False
    >>> fname = get_test_fname('test.fast5.tar')
    >>> WiffTar().sniff(fname)
    False
    """

    file_ext = "wiff.tar"

    def sniff(self, filename):
        if tarfile.is_tarfile(filename):
            with tarfile.open(filename) as rawtar:
                return ".wiff" in [os.path.splitext(os.path.basename(f).lower())[1] for f in rawtar.getnames()]
        return False

    def get_type(self):
        return "Sciex WIFF/SCAN archive"


@build_sniff_from_prefix
class Pretext(Binary):
    """
    PretextMap contact map file
    Try to guess if the file is a Pretext file.
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sample.pretext')
    >>> Pretext().sniff(fname)
    True
    """

    file_ext = "pretext"

    def sniff_prefix(self, sniff_prefix):
        # The first 4 bytes of any pretext file is 'pstm', and the rest of the
        # file contains binary data.
        return sniff_prefix.startswith_bytes(b"pstm")

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary pretext file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary pretext file (%s)" % (nice_size(dataset.get_size()))


class JP2(Binary):
    """
    JPEG 2000 binary image format
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.jp2')
    >>> JP2().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> JP2().sniff(fname)
    False
    """

    file_ext = "jp2"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self._magic = binascii.unhexlify("0000000C6A5020200D0A870A")

    def sniff(self, filename):
        # The first 12 bytes of any jp2 file are 0000000C6A5020200D0A870A
        try:
            header = open(filename, "rb").read(12)
            if header == self._magic:
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = "Binary JPEG 2000 file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary JPEG 2000 file (%s)" % (nice_size(dataset.get_size()))


class Npz(CompressedArchive):
    """
    Class describing an Numpy NPZ file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('hexrd.images.npz')
    >>> Npz().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> Npz().sniff(fname)
    False
    """

    file_ext = "npz"
    # edam_format = "format_4003"

    MetadataElement(name="nfiles", default=0, desc="nfiles", readonly=True, visible=True, no_value=0)
    MetadataElement(name="files", default=[], desc="files", readonly=True, visible=True, no_value=[])

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def sniff(self, filename):
        try:
            npz = np.load(filename)
            if isinstance(npz, np.lib.npyio.NpzFile):
                for f in npz.files:
                    if isinstance(npz[f], np.ndarray):
                        return True
        except Exception:
            return False
        return False

    def set_meta(self, dataset, **kwd):
        try:
            with np.load(dataset.file_name) as npz:
                dataset.metadata.nfiles = len(npz.files)
                dataset.metadata.files = npz.files
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = f"Binary Numpy npz {dataset.metadata.nfiles} files ({nice_size(dataset.get_size())})"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary Numpy npz file (%s)" % (nice_size(dataset.get_size()))


class HexrdImagesNpz(Npz):
    """
    Class describing an HEXRD Images Numpy NPZ file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('hexrd.images.npz')
    >>> HexrdImagesNpz().sniff(fname)
    True
    >>> fname = get_test_fname('eta_ome.npz')
    >>> HexrdImagesNpz().sniff(fname)
    False
    """

    file_ext = "hexrd.images.npz"

    MetadataElement(
        name="panel_id",
        default="",
        desc="Detector Panel ID",
        param=MetadataParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value="",
    )
    MetadataElement(
        name="shape", default=(), desc="shape", param=metadata.ListParameter, readonly=True, visible=True, no_value=()
    )
    MetadataElement(name="nframes", default=0, desc="nframes", readonly=True, visible=True, no_value=0)
    MetadataElement(name="omegas", desc="has omegas", default="False", visible=False)

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def sniff(self, filename):
        if super().sniff(filename):
            try:
                req_files = {"0_row", "0_col", "0_data", "shape", "nframes", "dtype"}
                with np.load(filename) as npz:
                    return set(npz.files) >= req_files
            except Exception as e:
                log.warning("%s, sniff Exception: %s", self, e)
                return False
        return False

    def set_meta(self, dataset, **kwd):
        super().set_meta(dataset, **kwd)
        try:
            with np.load(dataset.file_name) as npz:
                if "panel_id" in npz.files:
                    dataset.metadata.panel_id = str(npz["panel_id"])
                if "omega" in npz.files:
                    dataset.metadata.omegas = "True"
                dataset.metadata.shape = npz["shape"].tolist()
                dataset.metadata.nframes = npz["nframes"].tolist()
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            lines = [
                f"Binary Hexrd Image npz {dataset.metadata.nfiles} files ({nice_size(dataset.get_size())})",
                f"Panel: {dataset.metadata.panel_id} Frames: {dataset.metadata.nframes} Shape: {dataset.metadata.shape}",
            ]
            dataset.peek = "\n".join(lines)
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary Numpy npz file (%s)" % (nice_size(dataset.get_size()))


class HexrdEtaOmeNpz(Npz):
    """
    Class describing an HEXRD Eta-Ome Numpy NPZ file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('hexrd.eta_ome.npz')
    >>> HexrdEtaOmeNpz().sniff(fname)
    True
    >>> fname = get_test_fname('hexrd.images.npz')
    >>> HexrdEtaOmeNpz().sniff(fname)
    False
    """

    file_ext = "hexrd.eta_ome.npz"

    MetadataElement(
        name="HKLs", default=(), desc="HKLs", param=metadata.ListParameter, readonly=True, visible=True, no_value=()
    )
    MetadataElement(name="nframes", default=0, desc="nframes", readonly=True, visible=True, no_value=0)

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def sniff(self, filename):
        if super().sniff(filename):
            try:
                req_files = {"dataStore", "etas", "etaEdges", "iHKLList", "omegas", "omeEdges", "planeData_hkls"}
                with np.load(filename) as npz:
                    return set(npz.files) >= req_files
            except Exception as e:
                log.warning("%s, sniff Exception: %s", self, e)
                return False
        return False

    def set_meta(self, dataset, **kwd):
        super().set_meta(dataset, **kwd)
        try:
            with np.load(dataset.file_name) as npz:
                dataset.metadata.HKLs = npz["iHKLList"].tolist()
                dataset.metadata.nframes = len(npz["omegas"])
        except Exception as e:
            log.warning("%s, set_meta Exception: %s", self, e)

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            lines = [
                f"Binary Hexrd Eta-Ome npz {dataset.metadata.nfiles} files ({nice_size(dataset.get_size())})",
                f"Eta-Ome HKLs: {dataset.metadata.HKLs} Frames: {dataset.metadata.nframes}",
            ]
            dataset.peek = "\n".join(lines)
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary Numpy npz file (%s)" % (nice_size(dataset.get_size()))


if __name__ == "__main__":
    import doctest

    doctest.testmod(sys.modules[__name__])
