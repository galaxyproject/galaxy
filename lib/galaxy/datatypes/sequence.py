"""
Sequence classes
"""

import json
import logging
import math
import os
import re
import string
import subprocess
from itertools import islice
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
)

import bx.align.maf
from markupsafe import escape

from galaxy import util
from galaxy.datatypes import metadata
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.data import DatatypeValidation
from galaxy.datatypes.metadata import (
    DictParameter,
    MetadataElement,
)
from galaxy.datatypes.protocols import (
    DatasetHasHidProtocol,
    DatasetProtocol,
    HasMetadata,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    get_headers,
    iter_headers,
)
from galaxy.exceptions import InvalidFileFormatError
from galaxy.util import (
    compression_utils,
    nice_size,
)
from galaxy.util.checkers import is_gzip
from galaxy.util.image_util import check_image_type
from . import data

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class SequenceSplitLocations(data.Text):
    """
    Class storing information about a sequence file composed of multiple gzip files concatenated as
    one OR an uncompressed file. In the GZIP case, each sub-file's location is stored in start and end.

    The format of the file is JSON::

      { "sections" : [
              { "start" : "x", "end" : "y", "sequences" : "z" },
              ...
      ]}

    """

    file_ext = "fqtoc"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            try:
                parsed_data = json.load(open(dataset.get_file_name()))
                # dataset.peek = json.dumps(data, sort_keys=True, indent=4)
                dataset.peek = data.get_file_peek(dataset.get_file_name())
                dataset.blurb = "%d sections" % len(parsed_data["sections"])
            except Exception:
                dataset.peek = "Not FQTOC file"
                dataset.blurb = "Not FQTOC file"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            try:
                data = json.loads(file_prefix.contents_header)
                sections = data["sections"]
                for section in sections:
                    if "start" not in section or "end" not in section or "sequences" not in section:
                        return False
                return True
            except Exception:
                pass
        return False


class Sequence(data.Text):
    """Class describing a sequence"""

    edam_data = "data_2044"

    MetadataElement(
        name="sequences", default=0, desc="Number of sequences", readonly=True, visible=False, optional=True, no_value=0
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of sequences and the number of data lines in dataset.
        """
        data_lines = 0
        sequences = 0
        with compression_utils.get_fileobj(dataset.get_file_name()) as fh:
            for line in fh:
                line = line.strip()
                if line and line.startswith("#"):
                    # We don't count comment lines for sequence data types
                    continue
                if line and line.startswith(">"):
                    sequences += 1
                    data_lines += 1
                else:
                    data_lines += 1
            dataset.metadata.data_lines = data_lines
            dataset.metadata.sequences = sequences

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            if dataset.metadata.sequences:
                dataset.blurb = f"{util.commaify(str(dataset.metadata.sequences))} sequences"
            else:
                dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    @staticmethod
    def get_sequences_per_file(total_sequences: int, split_params: Dict) -> List:
        if split_params["split_mode"] == "number_of_parts":
            # legacy basic mode - split into a specified number of parts
            parts = int(split_params["split_size"])
            sequences_per_file = [total_sequences / parts for i in range(parts)]
            for i in range(total_sequences % parts):
                sequences_per_file[i] += 1
        elif split_params["split_mode"] == "to_size":
            # loop through the sections and calculate the number of sequences
            chunk_size = int(split_params["split_size"])
            rem = total_sequences % chunk_size
            sequences_per_file = [chunk_size for i in range(total_sequences // chunk_size)]
            # TODO: Should we invest the time in a better way to handle small remainders?
            if rem > 0:
                sequences_per_file.append(rem)
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")
        return sequences_per_file

    @classmethod
    def do_slow_split(cls, input_datasets, subdir_generator_function, split_params):
        # count the sequences so we can split
        # TODO: if metadata is present, take the number of lines / 4
        if input_datasets[0].metadata is not None and input_datasets[0].metadata.sequences is not None:
            total_sequences = input_datasets[0].metadata.sequences
        else:
            with compression_utils.get_fileobj(input_datasets[0].get_file_name()) as in_file:
                total_sequences = sum(1 for line in in_file)
            total_sequences /= 4

        sequences_per_file = cls.get_sequences_per_file(total_sequences, split_params)
        return cls.write_split_files(input_datasets, None, subdir_generator_function, sequences_per_file)

    @classmethod
    def do_fast_split(cls, input_datasets, toc_file_datasets, subdir_generator_function, split_params):
        data = json.load(open(toc_file_datasets[0].get_file_name()))
        sections = data["sections"]
        total_sequences = 0
        for section in sections:
            total_sequences += int(section["sequences"])
        sequences_per_file = cls.get_sequences_per_file(total_sequences, split_params)
        return cls.write_split_files(input_datasets, toc_file_datasets, subdir_generator_function, sequences_per_file)

    @classmethod
    def write_split_files(cls, input_datasets, toc_file_datasets, subdir_generator_function, sequences_per_file):
        directories = []

        def get_subdir(idx):
            if idx < len(directories):
                return directories[idx]
            dir = subdir_generator_function()
            directories.append(dir)
            return dir

        # we know how many splits and how many sequences in each. What remains is to write out instructions for the
        # splitting of all the input files. To decouple the format of those instructions from this code, the exact format of
        # those instructions is delegated to scripts
        start_sequence = 0
        for part_no in range(len(sequences_per_file)):
            dir = get_subdir(part_no)
            for ds_no in range(len(input_datasets)):
                ds = input_datasets[ds_no]
                base_name = os.path.basename(ds.get_file_name())
                part_path = os.path.join(dir, base_name)
                split_data = dict(
                    class_name=f"{cls.__module__}.{cls.__name__}",
                    output_name=part_path,
                    input_name=ds.get_file_name(),
                    args=dict(start_sequence=start_sequence, num_sequences=sequences_per_file[part_no]),
                )
                if toc_file_datasets is not None:
                    toc = toc_file_datasets[ds_no]
                    split_data["args"]["toc_file"] = toc.get_file_name()
                with open(os.path.join(dir, f"split_info_{base_name}.json"), "w") as f:
                    json.dump(split_data, f)
            start_sequence += sequences_per_file[part_no]
        return directories

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Optional[Dict]) -> None:
        """Split a generic sequence file (not sensible or possible, see subclasses)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split generic sequence files")

    @staticmethod
    def get_split_commands_with_toc(
        input_name: str, output_name: str, toc_file: Any, start_sequence: int, sequence_count: int
    ) -> List:
        """
        Uses a Table of Contents dict, parsed from an FQTOC file, to come up with a set of
        shell commands that will extract the parts necessary
        >>> three_sections=[dict(start=0, end=74, sequences=10), dict(start=74, end=148, sequences=10), dict(start=148, end=148+76, sequences=10)]
        >>> Sequence.get_split_commands_with_toc('./input.gz', './output.gz', dict(sections=three_sections), start_sequence=0, sequence_count=10)
        ['dd bs=1 skip=0 count=74 if=./input.gz 2> /dev/null >> ./output.gz']
        >>> Sequence.get_split_commands_with_toc('./input.gz', './output.gz', dict(sections=three_sections), start_sequence=1, sequence_count=5)
        ['(dd bs=1 skip=0 count=74 if=./input.gz 2> /dev/null )| zcat | ( tail -n +5 2> /dev/null) | head -20 | gzip -c >> ./output.gz']
        >>> Sequence.get_split_commands_with_toc('./input.gz', './output.gz', dict(sections=three_sections), start_sequence=0, sequence_count=20)
        ['dd bs=1 skip=0 count=148 if=./input.gz 2> /dev/null >> ./output.gz']
        >>> Sequence.get_split_commands_with_toc('./input.gz', './output.gz', dict(sections=three_sections), start_sequence=5, sequence_count=10)
        ['(dd bs=1 skip=0 count=74 if=./input.gz 2> /dev/null )| zcat | ( tail -n +21 2> /dev/null) | head -20 | gzip -c >> ./output.gz', '(dd bs=1 skip=74 count=74 if=./input.gz 2> /dev/null )| zcat | ( tail -n +1 2> /dev/null) | head -20 | gzip -c >> ./output.gz']
        >>> Sequence.get_split_commands_with_toc('./input.gz', './output.gz', dict(sections=three_sections), start_sequence=10, sequence_count=10)
        ['dd bs=1 skip=74 count=74 if=./input.gz 2> /dev/null >> ./output.gz']
        >>> Sequence.get_split_commands_with_toc('./input.gz', './output.gz', dict(sections=three_sections), start_sequence=5, sequence_count=20)
        ['(dd bs=1 skip=0 count=74 if=./input.gz 2> /dev/null )| zcat | ( tail -n +21 2> /dev/null) | head -20 | gzip -c >> ./output.gz', 'dd bs=1 skip=74 count=74 if=./input.gz 2> /dev/null >> ./output.gz', '(dd bs=1 skip=148 count=76 if=./input.gz 2> /dev/null )| zcat | ( tail -n +1 2> /dev/null) | head -20 | gzip -c >> ./output.gz']
        """
        sections = toc_file["sections"]
        result = []

        current_sequence = 0
        i = 0
        # skip to the section that contains my starting sequence
        while i < len(sections) and start_sequence >= current_sequence + int(sections[i]["sequences"]):
            current_sequence += int(sections[i]["sequences"])
            i += 1
        if i == len(sections):  # bad input data!
            raise Exception(f"No FQTOC section contains starting sequence {start_sequence}")

        # These two variables act as an accumulator for consecutive entire blocks that
        # can be copied verbatim (without decompressing)
        start_chunk = -1
        end_chunk = -1
        copy_chunk_cmd = "dd bs=1 skip=%s count=%s if=%s 2> /dev/null >> %s"

        while sequence_count > 0 and i < len(sections):
            # we need to extract partial data. So, find the byte offsets of the chunks that contain the data we need
            # use a combination of dd (to pull just the right sections out) tail (to skip lines) and head (to get the
            # right number of lines
            sequences = int(sections[i]["sequences"])
            skip_sequences = start_sequence - current_sequence
            sequences_to_extract = min(sequence_count, sequences - skip_sequences)
            start_copy = int(sections[i]["start"])
            end_copy = int(sections[i]["end"])
            if sequences_to_extract < sequences:
                if start_chunk > -1:
                    result.append(copy_chunk_cmd % (start_chunk, end_chunk - start_chunk, input_name, output_name))
                    start_chunk = -1
                # extract, unzip, trim, recompress
                result.append(
                    f"(dd bs=1 skip={start_copy} count={end_copy - start_copy} if={input_name} 2> /dev/null )| zcat | ( tail -n +{skip_sequences * 4 + 1} 2> /dev/null) | head -{sequences_to_extract * 4} | gzip -c >> {output_name}"
                )
            else:  # whole section - add it to the start_chunk/end_chunk accumulator
                if start_chunk == -1:
                    start_chunk = start_copy
                end_chunk = end_copy
            sequence_count -= sequences_to_extract
            start_sequence += sequences_to_extract
            current_sequence += sequences
            i += 1
        if start_chunk > -1:
            result.append(copy_chunk_cmd % (start_chunk, end_chunk - start_chunk, input_name, output_name))

        if sequence_count > 0:
            raise Exception(f"{sequence_count} sequences not found in file")

        return result

    @staticmethod
    def get_split_commands_sequential(
        is_compressed: bool, input_name: str, output_name: str, start_sequence: int, sequence_count: int
    ) -> List:
        """
        Does a brain-dead sequential scan & extract of certain sequences
        >>> Sequence.get_split_commands_sequential(True, './input.gz', './output.gz', start_sequence=0, sequence_count=10)
        ['zcat "./input.gz" | ( tail -n +1 2> /dev/null) | head -40 | gzip -c > "./output.gz"']
        >>> Sequence.get_split_commands_sequential(False, './input.fastq', './output.fastq', start_sequence=10, sequence_count=10)
        ['tail -n +41 "./input.fastq" 2> /dev/null | head -40 > "./output.fastq"']
        """
        start_line = start_sequence * 4
        line_count = sequence_count * 4
        # TODO: verify that tail can handle 64-bit numbers
        if is_compressed:
            cmd = f'zcat "{input_name}" | ( tail -n +{start_line + 1} 2> /dev/null) | head -{line_count} | gzip -c'
        else:
            cmd = f'tail -n +{start_line + 1} "{input_name}" 2> /dev/null | head -{line_count}'
        cmd += f' > "{output_name}"'

        return [cmd]

    def display_data(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        **kwd,
    ):
        headers = kwd.get("headers", {})
        if preview:
            with compression_utils.get_fileobj(dataset.get_file_name()) as fh:
                max_peek_size = 100000
                try:
                    chunk = fh.read(max_peek_size + 1)
                except UnicodeDecodeError:
                    raise InvalidFileFormatError("Dataset appears to contain binary data, cannot display.")
                if len(chunk) <= max_peek_size:
                    mime = "text/plain"
                    self._clean_and_set_mime_type(trans, mime, headers)
                    return chunk[:-1], headers
                return (
                    trans.fill_template_mako("/dataset/large_file.mako", truncated_data=chunk[:-1], data=dataset),
                    headers,
                )
        else:
            return super().display_data(trans, dataset, preview, filename, to_ext, **kwd)


class Alignment(data.Text):
    """Class describing an alignment"""

    edam_data = "data_0863"

    MetadataElement(
        name="species", desc="Species", default=[], param=metadata.SelectParameter, multiple=True, readonly=True
    )

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Optional[Dict]) -> None:
        """Split a generic alignment file (not sensible or possible, see subclasses)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split generic alignment files")


@build_sniff_from_prefix
class Fasta(Sequence):
    """Class representing a FASTA sequence"""

    edam_format = "format_1929"
    file_ext = "fasta"

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of sequences and the number of data lines in a FASTA dataset.
        """
        data_lines = 0
        sequences = 0
        with compression_utils.get_fileobj(dataset.get_file_name()) as fh:
            for line in fh:
                if not line:
                    continue
                elif line[0] == ">":
                    sequences += 1
                    data_lines += 1
                else:
                    data_lines += 1
            dataset.metadata.data_lines = data_lines
            dataset.metadata.sequences = sequences

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in fasta format

        A sequence in FASTA format consists of a single-line description, followed by lines of sequence data.
        The first character of the description line is a greater-than (">") symbol in the first column.
        All lines should be shorter than 80 characters

        For complete details see http://www.ncbi.nlm.nih.gov/blast/fasta.shtml

        Rules for sniffing as True:

            We don't care about line length (other than empty lines).

            The first non-empty line must start with '>' and the Very Next line.strip() must have sequence data and not be a header.

                'sequence data' here is loosely defined as non-empty lines which do not start with '>'

                This will cause Color Space FASTA (csfasta) to be detected as True (they are, after all, still FASTA files - they have a header line followed by sequence data)

                    Previously this method did some checking to determine if the sequence data had integers (presumably to differentiate between fasta and csfasta)

                    This should be done through sniff order, where csfasta (currently has a null sniff function) is detected for first (stricter definition) followed sometime after by fasta

            We will only check that the first purported sequence is correctly formatted.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Fasta().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> Fasta().sniff( fname )
        True
        """
        fh = file_prefix.string_io()
        for line in fh:
            line = line.strip()
            if line:  # first non-empty line
                if line.startswith(">"):
                    # The next line.strip() must not be '', nor startwith '>'
                    line = fh.readline().strip()
                    if line == "" or line.startswith(">"):
                        return False

                    # If there is a third line, and it isn't a header line, it may not contain chars like '()[].' otherwise it's most likely a DotBracket file
                    line = fh.readline()
                    if not line:
                        return True
                    if not line.startswith(">") and re.search(r"[\(\)\[\]\.]", line):
                        return False
                    return True
                else:
                    return False
        return False

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Optional[Dict]) -> None:
        """Split a FASTA file sequence by sequence.

        Note that even if split_mode="number_of_parts", the actual number of
        sub-files produced may not match that requested by split_size.

        If split_mode="to_size" then split_size is treated as the number of
        FASTA records to put in each sub-file (not size in bytes).
        """
        if split_params is None:
            return
        if len(input_datasets) > 1:
            raise Exception("FASTA file splitting does not support multiple files")
        input_file = input_datasets[0].get_file_name()

        # Counting chunk size as number of sequences.
        if "split_mode" not in split_params:
            raise Exception("Tool does not define a split mode")
        elif split_params["split_mode"] == "number_of_parts":
            split_size = int(split_params["split_size"])
            log.debug("Split %s into %i parts..." % (input_file, split_size))
            # if split_mode = number_of_parts, and split_size = 10, and
            # we know the number of sequences (say 1234), then divide by
            # by ten, giving ten files of approx 123 sequences each.
            if input_datasets[0].metadata is not None and input_datasets[0].metadata.sequences:
                # Galaxy has already counted/estimated the number
                batch_size = 1 + input_datasets[0].metadata.sequences // split_size
                cls._count_split(input_file, batch_size, subdir_generator_function)
            else:
                # OK, if Galaxy hasn't counted them, it may be a big file.
                # We're not going to count the records which would be slow
                # and a waste of disk IO time - instead we'll split using
                # the file size.
                chunk_size = os.path.getsize(input_file) // split_size
                cls._size_split(input_file, chunk_size, subdir_generator_function)
        elif split_params["split_mode"] == "to_size":
            # Split the input file into as many sub-files as required,
            # each containing to_size many sequences
            batch_size = int(split_params["split_size"])
            log.debug("Split %s into batches of %i records..." % (input_file, batch_size))
            cls._count_split(input_file, batch_size, subdir_generator_function)
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

    @classmethod
    def _size_split(cls, input_file: str, chunk_size: int, subdir_generator_function: Callable) -> None:
        """Split a FASTA file into chunks based on size on disk.

        This does of course preserve complete records - it only splits at the
        start of a new FASTQ sequence record.
        """
        log.debug("Attemping to split FASTA file %s into chunks of %i bytes" % (input_file, chunk_size))
        with open(input_file) as f:
            part_file = None
            try:
                # Note if the input FASTA file has no sequences, we will
                # produce just one sub-file which will be a copy of it.
                part_dir = subdir_generator_function()
                part_path = os.path.join(part_dir, os.path.basename(input_file))
                part_file = open(part_path, "w")
                log.debug(f"Writing {input_file} part to {part_path}")
                start_offset = 0
                for line in iter(f.readline, ""):
                    offset = f.tell()
                    if not line:
                        break
                    if line[0] == ">" and offset - start_offset >= chunk_size:
                        # Start a new sub-file
                        part_file.close()
                        part_dir = subdir_generator_function()
                        part_path = os.path.join(part_dir, os.path.basename(input_file))
                        part_file = open(part_path, "w")
                        log.debug(f"Writing {input_file} part to {part_path}")
                        start_offset = f.tell()
                    part_file.write(line)
            except Exception as e:
                log.error("Unable to size split FASTA file: %s", util.unicodify(e))
                raise
            finally:
                if part_file:
                    part_file.close()

    @classmethod
    def _count_split(cls, input_file: str, chunk_size: int, subdir_generator_function: Callable) -> None:
        """Split a FASTA file into chunks based on counting records."""
        log.debug("Attemping to split FASTA file %s into chunks of %i sequences" % (input_file, chunk_size))
        with open(input_file) as f:
            part_file = None
            try:
                # Note if the input FASTA file has no sequences, we will
                # produce just one sub-file which will be a copy of it.
                part_dir = subdir_generator_function()
                part_path = os.path.join(part_dir, os.path.basename(input_file))
                part_file = open(part_path, "w")
                log.debug(f"Writing {input_file} part to {part_path}")
                rec_count = 0
                for line in f:
                    if not line:
                        break
                    if line[0] == ">":
                        rec_count += 1
                        if rec_count > chunk_size:
                            # Start a new sub-file
                            part_file.close()
                            part_dir = subdir_generator_function()
                            part_path = os.path.join(part_dir, os.path.basename(input_file))
                            part_file = open(part_path, "w")
                            log.debug(f"Writing {input_file} part to {part_path}")
                            rec_count = 1
                    part_file.write(line)
            except Exception as e:
                log.error("Unable to count split FASTA file: %s", util.unicodify(e))
                raise
            finally:
                if part_file:
                    part_file.close()


@build_sniff_from_prefix
class csFasta(Sequence):
    """Class representing the SOLID Color-Space sequence ( csfasta )"""

    edam_format = "format_3589"
    file_ext = "csfasta"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Color-space sequence:
            >2_15_85_F3
            T213021013012303002332212012112221222112212222

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> csFasta().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.csfasta' )
        >>> csFasta().sniff( fname )
        True
        """
        fh = file_prefix.string_io()
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):  # first non-empty non-comment line
                if line.startswith(">"):
                    line = fh.readline().strip()
                    if line == "" or line.startswith(">"):
                        break
                    elif line[0] not in string.ascii_uppercase:
                        return False
                    elif len(line) > 1 and not re.search(r"^[\d.]+$", line[1:]):
                        return False
                    return True
                else:
                    return False
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            dataset.metadata.data_lines = None
            dataset.metadata.sequences = None
            return
        return Sequence.set_meta(self, dataset, overwrite=overwrite, **kwd)


@build_sniff_from_prefix
class Fastg(Sequence):
    """Class representing a FASTG sequence
    http://fastg.sourceforge.net/FASTG_Spec_v1.00.pdf"""

    edam_format = "format_3823"
    file_ext = "fastg"

    MetadataElement(
        name="version", default="1.0", desc="FASTG format version", readonly=True, visible=True, no_value="1.0"
    )
    MetadataElement(
        name="properties",
        default={},
        param=DictParameter,
        desc="FASTG properites",
        readonly=True,
        visible=True,
        no_value={},
    )

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """FASTG must begin with lines:
           #FASTG:begin;
           #FASTG:version=*.*;
           #FASTG:properties;

        Or these can be combined on a line:
           #FASTG:begin:version=*.*:properties;

        FASTG must end with line:
           #FASTG:end;

        Example FASTG file:
            #FASTG:begin;
            #FASTG:version=1.0:assembly_name="tiny example";
            >chr1:chr1;
            ACGANNNNN[5:gap:size=(5,4..6)]CAGGC[1:alt:allele|C,G]TATACG
            >chr2;
            ACATACGCATATATATATATATATATAT[20:tandem:size=(10,8..12)|AT]TCAGGCA[1:alt|A,T,TT]GGAC
            #FASTG:end;

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> Fastg().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.fastg' )
        >>> Fastg().sniff( fname )
        True
        """
        fh = file_prefix.string_io()
        for i, line in enumerate(fh):
            if not line:
                break  # EOF
            line = line.strip()
            if i == 0:
                if not line.startswith("#FASTG:begin"):
                    break
            elif line and not line.startswith("#"):  # first non-empty non-comment line
                if line.startswith(">"):
                    # The next line.strip() must not be '', nor startwith '>'
                    line = fh.readline().strip()
                    if line == "" or line.startswith(">"):
                        break
                    return True
                else:
                    break  # we found a non-empty line, but it's not a header
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        with open(dataset.get_file_name()) as fh:
            for i, line in enumerate(fh):
                if not line:
                    break  # EOF
                line = line.strip()
                if i == 0:
                    if not line.startswith("#FASTG:begin"):
                        break
                if line.startswith("#FASTG"):
                    props = {
                        x.split("=")[0][1:]: x.split("=")[1]
                        for x in re.findall(':[a-zA-Z0-9_]+=[a-zA-Z0-9_().," ]+', line)
                    }
                    dataset.metadata.properties.update(props)
                    if "version" in props:
                        dataset.metadata.version = props["version"]
                if line and line.startswith(">"):
                    break
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            dataset.metadata.data_lines = None
            dataset.metadata.sequences = None
            return
        return Sequence.set_meta(self, dataset, overwrite=overwrite, **kwd)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            if dataset.metadata.sequences:
                dataset.blurb = f"{util.commaify(str(dataset.metadata.sequences))} sequences"
            else:
                dataset.blurb = nice_size(dataset.get_size())
            dataset.blurb += f"\nversion={dataset.metadata.version}"
            for k, v in dataset.metadata.properties.items():
                if k != "version":
                    dataset.blurb += f"\n{k}={v}"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class BaseFastq(Sequence):
    """Base class for FastQ sequences"""

    edam_format = "format_1930"
    file_ext = "fastq"
    bases_regexp = re.compile(r"^[NGTAC 0123\.]*$", re.IGNORECASE)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of sequences and the number of data lines
        in dataset.
        FIXME: This does not properly handle line wrapping
        """
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            dataset.metadata.data_lines = None
            dataset.metadata.sequences = None
            return
        data_lines = 0
        sequences = 0
        with compression_utils.get_fileobj(dataset.get_file_name()) as in_file:
            for line in in_file:
                if line.startswith("@") and data_lines % 4 == 0:
                    sequences += 1
                data_lines += 1
            dataset.metadata.data_lines = data_lines
            dataset.metadata.sequences = sequences

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in generic fastq format
        For details, see http://maq.sourceforge.net/fastq.shtml

        Note: There are three kinds of FASTQ files, known as "Sanger" (sometimes called "Standard"), Solexa, and Illumina
              These differ in the representation of the quality scores

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('1.fastqsanger')
        >>> FastqSanger().sniff(fname)
        True
        >>> fname = get_test_fname('4.fastqsanger')
        >>> FastqSanger().sniff(fname)
        True
        >>> fname = get_test_fname('3.fastq')
        >>> FastqSanger().sniff(fname)
        False
        >>> Fastq().sniff(fname)
        True
        >>> fname = get_test_fname('2.fastq')
        >>> Fastq().sniff(fname)
        True
        >>> FastqSanger().sniff(fname)
        False
        >>> fname = get_test_fname('1.fastq')
        >>> FastqSanger().sniff(fname)
        False
        >>> fname = get_test_fname('1.fastqcssanger')
        >>> FastqSanger().sniff(fname)
        False
        >>> Fastq().sniff(fname)
        True
        >>> FastqCSSanger().sniff(fname)
        True
        """
        compressed = file_prefix.compressed_format is not None
        if compressed and not isinstance(self, Binary):
            return False
        headers = iter_headers(file_prefix, sep="\n", count=1000)
        # check to see if the base qualities match
        if not self.quality_check(headers):
            return False
        return self.check_first_block(file_prefix)

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Optional[Dict]) -> None:
        """
        FASTQ files are split on cluster boundaries, in increments of 4 lines
        """
        if split_params is None:
            return None

        # first, see if there are any associated FQTOC files that will give us the split locations
        # if so, we don't need to read the files to do the splitting
        toc_file_datasets = []
        for ds in input_datasets:
            tmp_ds = ds
            fqtoc_file = None
            while fqtoc_file is None and tmp_ds is not None:
                fqtoc_file = tmp_ds.get_converted_files_by_type("fqtoc")
                tmp_ds = tmp_ds.copied_from_library_dataset_dataset_association

            if fqtoc_file is not None:
                toc_file_datasets.append(fqtoc_file)

        if len(toc_file_datasets) == len(input_datasets):
            return cls.do_fast_split(input_datasets, toc_file_datasets, subdir_generator_function, split_params)
        return cls.do_slow_split(input_datasets, subdir_generator_function, split_params)

    @staticmethod
    def process_split_file(data: Dict) -> bool:
        """
        This is called in the context of an external process launched by a Task (possibly not on the Galaxy machine)
        to create the input files for the Task. The parameters:
        data - a dict containing the contents of the split file
        """
        args = data["args"]
        input_name = data["input_name"]
        output_name = data["output_name"]
        start_sequence = int(args["start_sequence"])
        sequence_count = int(args["num_sequences"])

        if "toc_file" in args:
            with open(args["toc_file"]) as f:
                toc_file = json.load(f)
            commands = Sequence.get_split_commands_with_toc(
                input_name, output_name, toc_file, start_sequence, sequence_count
            )
        else:
            commands = Sequence.get_split_commands_sequential(
                is_gzip(input_name), input_name, output_name, start_sequence, sequence_count
            )
        for cmd in commands:
            subprocess.check_call(cmd, shell=True)
        return True

    @staticmethod
    def quality_check(lines: Iterable) -> bool:
        return True

    @classmethod
    def check_first_block(cls, file_prefix: FilePrefix):
        # check that first block looks like a fastq block
        block = get_headers(file_prefix, sep="\n", count=4)
        return cls.check_block(block)

    @classmethod
    def check_block(cls, block: List) -> bool:
        if (
            len(block) == 4
            and block[0][0]
            and block[0][0][0] == "@"
            and block[2][0]
            and block[2][0][0] == "+"
            and block[1][0]
        ):
            # Check the sequence line, make sure it contains only G/C/A/T/N
            match = cls.bases_regexp.match(block[1][0])
            if match:
                start, end = match.span()
                if (end - start) == len(block[1][0]):
                    return True
        return False

    def validate(self, dataset: DatasetProtocol, **kwd) -> DatatypeValidation:
        headers = iter_headers(dataset.get_file_name(), sep="\n", count=-1)
        # check to see if the base qualities match
        if not self.quality_check(headers):
            return DatatypeValidation.invalid("Invalid quality score(s) found for this fastq datatype.")

        headers = iter_headers(dataset.get_file_name(), sep="\n", count=-1)
        while True:
            block = list(islice(headers, 4))
            if len(block) == 0:
                break
            if not self.check_block(block):
                return DatatypeValidation.invalid("Invalid FASTQ structure found.")

        return DatatypeValidation.validated()


class Fastq(BaseFastq):
    """Class representing a generic FASTQ sequence"""

    edam_format = "format_1930"
    file_ext = "fastq"


class FastqSanger(Fastq):
    """Class representing a FASTQ sequence (the Sanger variant)

    phred scored quality values 0:50 represented by ASCII 33:83
    """

    edam_format = "format_1932"
    file_ext = "fastqsanger"
    bases_regexp = re.compile("^[NGTAC]*$", re.IGNORECASE)

    @staticmethod
    def quality_check(lines: Iterable) -> bool:
        """
        Presuming lines are lines from a fastq file,
        return True if the qualities are compatible with sanger encoding
        """
        for line in islice(lines, 3, None, 4):
            if not all(q >= "!" and q <= "S" for q in line[0]):
                return False
        return True


class FastqSolexa(Fastq):
    """Class representing a FASTQ sequence ( the Solexa variant )

    solexa scored quality values -5:40 represented by ASCII 59:104
    """

    edam_format = "format_1933"
    file_ext = "fastqsolexa"

    @staticmethod
    def quality_check(lines: Iterable) -> bool:
        """
        Presuming lines are lines from a fastq file,
        return True if the qualities are compatible with sanger encoding
        """
        for line in islice(lines, 3, None, 4):
            if not all(q >= ";" and q <= "h" for q in line[0]):
                return False
        return True

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        # we expicitely do not want to have this sniffed. so we keep this here
        # such that it can not be enabled in datatypes_conf
        raise NotImplementedError


class FastqIllumina(Fastq):
    """Class representing a FASTQ sequence ( the Illumina 1.3+ variant )

    phred scored quality values 0:40 represented by ASCII 64:104
    """

    edam_format = "format_1931"
    file_ext = "fastqillumina"

    @staticmethod
    def quality_check(lines: Iterable) -> bool:
        """
        Presuming lines are lines from a fastq file,
        return True if the qualities are compatible with sanger encoding
        """
        for line in islice(lines, 3, None, 4):
            if not all(q >= "@" and q <= "h" for q in line[0]):
                return False
        return True

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        # we expicitely do not want to have this sniffed. so we keep this here
        # such that it can not be enabled in datatypes_conf
        raise NotImplementedError


class FastqCSSanger(Fastq):
    """Class representing a Color Space FASTQ sequence ( e.g a SOLiD variant )

    sequence in in color space
    phred scored quality values 0:93 represented by ASCII 33:126
    """

    file_ext = "fastqcssanger"
    bases_regexp = re.compile(r"^[NGTAC][0123\.]*$", re.IGNORECASE)


@build_sniff_from_prefix
class Maf(Alignment):
    """Class describing a Maf alignment"""

    edam_format = "format_3008"
    file_ext = "maf"

    # Readonly and optional, users can't unset it, but if it is not set, we are generally ok; if required use a metadata validator in the tool definition
    MetadataElement(
        name="blocks", default=0, desc="Number of blocks", readonly=True, optional=True, visible=False, no_value=0
    )
    MetadataElement(
        name="species_chromosomes",
        desc="Species Chromosomes",
        param=metadata.FileParameter,
        readonly=True,
        visible=False,
        optional=True,
    )
    MetadataElement(
        name="maf_index",
        desc="MAF Index File",
        param=metadata.FileParameter,
        readonly=True,
        visible=False,
        optional=True,
    )

    def init_meta(self, dataset: HasMetadata, copy_from: Optional[HasMetadata] = None) -> None:
        Alignment.init_meta(self, dataset, copy_from=copy_from)

    def set_meta(
        self, dataset: DatasetProtocol, overwrite: bool = True, metadata_tmp_files_dir: Optional[str] = None, **kwd
    ) -> None:
        """
        Parses and sets species, chromosomes, index from MAF file.
        """
        # these metadata values are not accessable by users, always overwrite
        # Imported here to avoid circular dependency
        from galaxy.tools.util.maf_utilities import build_maf_index_species_chromosomes

        indexes, species, species_chromosomes, blocks = build_maf_index_species_chromosomes(dataset.get_file_name())
        if indexes is None:
            return  # this is not a MAF file
        dataset.metadata.species = species
        dataset.metadata.blocks = blocks

        # write species chromosomes to a file
        chrom_file = dataset.metadata.species_chromosomes
        if not chrom_file:
            chrom_file = dataset.metadata.spec["species_chromosomes"].param.new_file(
                dataset=dataset, metadata_tmp_files_dir=metadata_tmp_files_dir
            )
        with open(chrom_file.get_file_name(), "w") as chrom_out:
            for spec, chroms in species_chromosomes.items():
                chrom_out.write("{}\t{}\n".format(spec, "\t".join(chroms)))
        dataset.metadata.species_chromosomes = chrom_file

        index_file = dataset.metadata.maf_index
        if not index_file:
            index_file = dataset.metadata.spec["maf_index"].param.new_file(
                dataset=dataset, metadata_tmp_files_dir=metadata_tmp_files_dir
            )
        indexes.write(open(index_file.get_file_name(), "wb"))
        dataset.metadata.maf_index = index_file

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            # The file must exist on disk for the get_file_peek() method
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            if dataset.metadata.blocks:
                dataset.blurb = f"{util.commaify(str(dataset.metadata.blocks))} blocks"
            else:
                # Number of blocks is not known ( this should not happen ), and auto-detect is
                # needed to set metadata
                dataset.blurb = "? blocks"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset)

    def make_html_table(self, dataset: DatasetProtocol, skipchars: Optional[List] = None) -> str:
        """Create HTML table, used for displaying peek"""
        skipchars = skipchars or []
        try:
            out = ['<table cellspacing="0" cellpadding="3">']
            out.append("<tr><th>Species:&nbsp;")
            for species in dataset.metadata.species:
                out.append(f"{species}&nbsp;")
            out.append("</th></tr>")
            if not dataset.peek:
                dataset.set_peek()
            data = dataset.peek
            lines = data.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                out.append(f"<tr><td>{escape(line)}</td></tr>")
            out.append("</table>")
            return "".join(out)
        except Exception as exc:
            return f"Can't create peek {exc}"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines wether the file is in maf format

        The .maf format is line-oriented. Each multiple alignment ends with a blank line.
        Each sequence in an alignment is on a single line, which can get quite long, but
        there is no length limit. Words in a line are delimited by any white space.
        Lines starting with # are considered to be comments. Lines starting with ## can
        be ignored by most programs, but contain meta-data of one form or another.

        The first line of a .maf file begins with ##maf. This word is followed by white-space-separated
        variable=value pairs. There should be no white space surrounding the "=".

        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format5

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Maf().sniff( fname )
        True
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> Maf().sniff( fname )
        False
        """
        headers = get_headers(file_prefix, None)
        try:
            if len(headers) > 1 and headers[0][0] and headers[0][0] == "##maf":
                return True
            else:
                return False
        except Exception:
            return False


class MafCustomTrack(data.Text):
    file_ext = "mafcustomtrack"

    MetadataElement(
        name="vp_chromosome",
        default="chr1",
        desc="Viewport Chromosome",
        readonly=True,
        optional=True,
        visible=False,
        no_value="",
    )
    MetadataElement(
        name="vp_start", default="1", desc="Viewport Start", readonly=True, optional=True, visible=False, no_value=""
    )
    MetadataElement(
        name="vp_end", default="100", desc="Viewport End", readonly=True, optional=True, visible=False, no_value=""
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Parses and sets viewport metadata from MAF file.
        """
        max_block_check = 10
        chrom = None
        forward_strand_start = math.inf
        forward_strand_end = 0
        try:
            maf_file = open(dataset.get_file_name())
            maf_file.readline()  # move past track line
            for i, block in enumerate(bx.align.maf.Reader(maf_file)):
                ref_comp = block.get_component_by_src_start(dataset.metadata.dbkey)
                if ref_comp:
                    ref_chrom = bx.align.maf.src_split(ref_comp.src)[-1]
                    if chrom is None:
                        chrom = ref_chrom
                    if chrom == ref_chrom:
                        forward_strand_start = min(forward_strand_start, ref_comp.forward_strand_start)
                        forward_strand_end = max(forward_strand_end, ref_comp.forward_strand_end)
                if i > max_block_check:
                    break

            if forward_strand_end > forward_strand_start:
                dataset.metadata.vp_chromosome = chrom
                dataset.metadata.vp_start = forward_strand_start
                dataset.metadata.vp_end = forward_strand_end
        except Exception:
            pass


@build_sniff_from_prefix
class Axt(data.Text):
    """Class describing an axt alignment"""

    # gvk- 11/19/09 - This is really an alignment, but we no longer have tools that use this data type, and it is
    # here simply for backward compatibility ( although it is still in the datatypes registry ).  Subclassing
    # from data.Text eliminates managing metadata elements inherited from the Alignemnt class.

    edam_data = "data_0863"
    edam_format = "format_3013"
    file_ext = "axt"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in axt format

        axt alignment files are produced from Blastz, an alignment tool available from Webb Miller's lab
        at Penn State University.

        Each alignment block in an axt file contains three lines: a summary line and 2 sequence lines.
        Blocks are separated from one another by blank lines.

        The summary line contains chromosomal position and size information about the alignment. It
        consists of 9 required fields.

        The sequence lines contain the sequence of the primary assembly (line 2) and aligning assembly
        (line 3) with inserts.  Repeats are indicated by lower-case letters.

        For complete details see http://genome.ucsc.edu/goldenPath/help/axt.html

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'alignment.axt' )
        >>> Axt().sniff( fname )
        True
        >>> fname = get_test_fname( 'alignment.lav' )
        >>> Axt().sniff( fname )
        False
        >>> fname = get_test_fname( '2.chain' )
        >>> Axt().sniff( fname )
        False
        """
        headers = get_headers(file_prefix, None, count=4, comment_designator="#")
        if not (
            len(headers) >= 3
            and len(headers[0]) == 9
            and headers[0][0] == "0"
            and headers[0][2].isdecimal()
            and headers[0][3].isdecimal()
            and headers[0][5].isdecimal()
            and headers[0][6].isdecimal()
            and headers[0][7] in data.valid_strand
            and headers[0][8].isdecimal()
            and len(headers[1]) == 1
            and len(headers[2]) == 1
        ):
            return False
        # the optional fourth non-comment line has to be empty
        if len(headers) == 4 and not headers[3] == []:
            return False
        else:
            return True


@build_sniff_from_prefix
class Lav(data.Text):
    """Class describing a LAV alignment"""

    # gvk- 11/19/09 - This is really an alignment, but we no longer have tools that use this data type, and it is
    # here simply for backward compatibility ( although it is still in the datatypes registry ).  Subclassing
    # from data.Text eliminates managing metadata elements inherited from the Alignment class.

    edam_data = "data_0863"
    edam_format = "format_3014"
    file_ext = "lav"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in lav format

        LAV is an alignment format developed by Webb Miller's group. It is the primary output format for BLASTZ.
        The first line of a .lav file begins with #:lav.

        For complete details see http://www.bioperl.org/wiki/LAV_alignment_format

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'alignment.lav' )
        >>> Lav().sniff( fname )
        True
        >>> fname = get_test_fname( 'alignment.axt' )
        >>> Lav().sniff( fname )
        False
        """
        headers = get_headers(file_prefix, None)
        try:
            if len(headers) > 1 and headers[0][0] and headers[0][0].startswith("#:lav"):
                return True
            else:
                return False
        except Exception:
            return False


class RNADotPlotMatrix(data.Data):
    edam_format = "format_3466"
    file_ext = "rna_eps"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "RNA Dot Plot format (Postscript derivative)"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff(self, filename: str) -> bool:
        """Determine if the file is in RNA dot plot format."""
        if check_image_type(filename, ["EPS"]):
            seq = False
            coor = False
            pairs = False
            with open(filename) as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        if line.startswith("/sequence"):
                            seq = True
                        elif line.startswith("/coor"):
                            coor = True
                        elif line.startswith("/pairs"):
                            pairs = True
                    if seq and coor and pairs:
                        return True
        return False


@build_sniff_from_prefix
class DotBracket(Sequence):
    edam_data = "data_0880"
    edam_format = "format_1457"
    file_ext = "dbn"

    sequence_regexp = re.compile(r"^[ACGTURYKMSWBDHVN]+$", re.I)
    structure_regexp = re.compile(r"^[\(\)\.\[\]{}]+$")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of sequences and the number of data lines
        in dataset.
        """
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            dataset.metadata.data_lines = None
            dataset.metadata.sequences = None
            dataset.metadata.seconday_structures = None
            return

        data_lines = 0
        sequences = 0

        for line in open(dataset.get_file_name()):
            line = line.strip()
            data_lines += 1

            if line and line.startswith(">"):
                sequences += 1

        dataset.metadata.data_lines = data_lines
        dataset.metadata.sequences = sequences

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Galaxy Dbn (Dot-Bracket notation) rules:

        * The first non-empty line is a header line: no comment lines are allowed.

          * A header line starts with a '>' symbol and continues with 0 or multiple symbols until the line ends.

        * The second non-empty line is a sequence line.

          * A sequence line may only include chars that match the FASTA format (https://en.wikipedia.org/wiki/FASTA_format#Sequence_representation) symbols for nucleotides: ACGTURYKMSWBDHVN, and may thus not include whitespaces.
          * A sequence line has no prefix and no suffix.
          * A sequence line is case insensitive.

        * The third non-empty line is a structure (Dot-Bracket) line and only describes the 2D structure of the sequence above it.

          * A structure line must consist of the following chars: '.{}[]()'.
          * A structure line must be of the same length as the sequence line, and each char represents the structure of the nucleotide above it.
          * A structure line has no prefix and no suffix.
          * A nucleotide pairs with only 1 or 0 other nucleotides.

            * In a structure line, the number of '(' symbols equals the number of ')' symbols, the number of '[' symbols equals the number of ']' symbols and the number of '{' symbols equals the number of '}' symbols.

        * The format accepts multiple entries per file, given that each entry is provided as three lines: the header, sequence and structure line.

            * Sniffing is only applied on the first entry.

        * Empty lines are allowed.
        """

        state = 0

        for line in file_prefix.line_iterator():
            line = line.strip()

            if line:
                # header line
                if state == 0:
                    if line[0] != ">":
                        return False
                    else:
                        state = 1

                # sequence line
                elif state == 1:
                    if not self.sequence_regexp.match(line):
                        return False
                    else:
                        sequence_size = len(line)
                        state = 2

                # dot-bracket structure line
                elif state == 2:
                    if (
                        sequence_size != len(line)
                        or not self.structure_regexp.match(line)
                        or line.count("(") != line.count(")")
                        or line.count("[") != line.count("]")
                        or line.count("{") != line.count("}")
                    ):
                        return False
                    else:
                        return True

        # Number of lines is less than 3
        return False


@build_sniff_from_prefix
class Genbank(data.Text):
    """Class representing a Genbank sequence"""

    edam_format = "format_1936"
    edam_data = "data_0849"
    file_ext = "genbank"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determine whether the file is in genbank format.
        Works for compressed files.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( '1.genbank' )
        >>> Genbank().sniff( fname )
        True
        """
        compressed = file_prefix.compressed_format
        if compressed and not isinstance(self, Binary):
            return False
        return "LOCUS " == file_prefix.contents_header[0:6]


@build_sniff_from_prefix
class MemePsp(Sequence):
    """Class representing MEME Position Specific Priors"""

    file_ext = "memepsp"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        The format of an entry in a PSP file is:

        >ID WIDTH
        PRIORS

        For complete details see http://meme-suite.org/doc/psp-format.html

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('1.memepsp')
        >>> MemePsp().sniff(fname)
        True
        >>> fname = get_test_fname('sequence.fasta')
        >>> MemePsp().sniff(fname)
        False
        """

        def floats_verified(line):
            for item in line.split():
                try:
                    float(item)
                except ValueError:
                    return False
                try:
                    int(item)
                except ValueError:
                    return True
            return False

        num_lines = 0
        fh = file_prefix.string_io()
        got_header = False
        got_priors = False
        while num_lines < 100:
            line = fh.readline()
            if not line:
                # EOF.
                break
            num_lines += 1
            line = line.strip()
            if line:
                if line.startswith(">"):
                    got_header = True
                    # The line must not be blank, nor start with '>'
                    line = fh.readline().strip()
                    if line == "" or line.startswith(">"):
                        return False
                    # All items within the line must be floats.
                    if not floats_verified(line):
                        return False
                    else:
                        got_priors = True
                    # If there is a second line within the ID section,
                    # all items within the line must be floats.
                    line = fh.readline().strip()
                    if line:
                        if not floats_verified(line):
                            return False
        # We've checked the first 100 lines and they are compatible with the memepsp format
        # and contain at least one valid entry
        return got_header and got_priors
