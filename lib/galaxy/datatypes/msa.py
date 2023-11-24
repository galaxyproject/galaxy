import abc
import logging
import os
import re
from typing import (
    Callable,
    Dict,
    List,
)

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.data import (
    get_file_peek,
    Text,
)
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.util import generic_util
from galaxy.util import (
    nice_size,
    unicodify,
)

log = logging.getLogger(__name__)

STOCKHOLM_SEARCH_PATTERN = re.compile(r"#\s+STOCKHOLM\s+1\.0")


@build_sniff_from_prefix
class InfernalCM(Text):
    file_ext = "cm"

    MetadataElement(
        name="number_of_models",
        default=0,
        desc="Number of covariance models",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    MetadataElement(
        name="cm_version",
        default="1/a",
        desc="Infernal Covariance Model version",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            if dataset.metadata.number_of_models == 1:
                dataset.blurb = "1 model"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_models} models"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'infernal_model.cm' )
        >>> InfernalCM().sniff( fname )
        True
        >>> fname = get_test_fname( '2.txt' )
        >>> InfernalCM().sniff( fname )
        False
        """
        return file_prefix.startswith("INFERNAL")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of models and the version of CM file in dataset.
        """
        dataset.metadata.number_of_models = generic_util.count_special_lines("^INFERNAL", dataset.file_name)
        with open(dataset.file_name) as f:
            first_line = f.readline()
            if first_line.startswith("INFERNAL"):
                dataset.metadata.cm_version = (first_line.split()[0]).replace("INFERNAL", "")


@build_sniff_from_prefix
class Hmmer(Text):
    edam_data = "data_1364"
    edam_format = "format_1370"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "HMMER Database"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return f"HMMER database ({nice_size(dataset.get_size())})"

    @abc.abstractmethod
    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        raise NotImplementedError


class Hmmer2(Hmmer):
    edam_format = "format_3328"
    file_ext = "hmm2"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """HMMER2 files start with HMMER2.0"""
        return file_prefix.startswith("HMMER2.0")


class Hmmer3(Hmmer):
    edam_format = "format_3329"
    file_ext = "hmm3"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """HMMER3 files start with HMMER3/f"""
        return file_prefix.startswith("HMMER3/f")


class HmmerPress(Binary):
    """Class for hmmpress database files."""

    file_ext = "hmmpress"
    composite_type = "basic"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "HMMER Binary database"
            dataset.blurb = "HMMER Binary database"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "HMMER3 database (multiple files)"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        # Binary model
        self.add_composite_file("model.hmm.h3m", is_binary=True)
        # SSI index for binary model
        self.add_composite_file("model.hmm.h3i", is_binary=True)
        # Profiles (MSV part)
        self.add_composite_file("model.hmm.h3f", is_binary=True)
        # Profiles (remained)
        self.add_composite_file("model.hmm.h3p", is_binary=True)


@build_sniff_from_prefix
class Stockholm_1_0(Text):
    edam_data = "data_0863"
    edam_format = "format_1961"
    file_ext = "stockholm"

    MetadataElement(
        name="number_of_models",
        default=0,
        desc="Number of multiple alignments",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            if dataset.metadata.number_of_models == 1:
                dataset.blurb = "1 alignment"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_models} alignments"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        return file_prefix.search(STOCKHOLM_SEARCH_PATTERN)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """

        Set the number of models in dataset.
        """
        dataset.metadata.number_of_models = generic_util.count_special_lines(
            "^#[[:space:]+]STOCKHOLM[[:space:]+]1.0", dataset.file_name
        )

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Dict) -> None:
        """

        Split the input files by model records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("STOCKHOLM-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params["split_mode"] == "number_of_parts":
            raise Exception(
                f"Split mode \"{split_params['split_mode']}\" is currently not implemented for STOCKHOLM-files."
            )
        elif split_params["split_mode"] == "to_size":
            chunk_size = int(split_params["split_size"])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _read_stockholm_records(filename):
            lines = []
            with open(filename) as handle:
                for line in handle:
                    lines.append(line)
                    if line.strip() == "//":
                        yield lines
                        lines = []

        def _write_part_stockholm_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, "w") as part_file:
                part_file.writelines(accumulated_lines)

        try:
            stockholm_records = _read_stockholm_records(input_files[0])
            stockholm_lines_accumulated = []
            for counter, stockholm_record in enumerate(stockholm_records, start=1):
                stockholm_lines_accumulated.extend(stockholm_record)
                if counter % chunk_size == 0:
                    _write_part_stockholm_file(stockholm_lines_accumulated)
                    stockholm_lines_accumulated = []
            if stockholm_lines_accumulated:
                _write_part_stockholm_file(stockholm_lines_accumulated)
        except Exception as e:
            log.error("Unable to split files: %s", unicodify(e))
            raise


@build_sniff_from_prefix
class MauveXmfa(Text):
    file_ext = "xmfa"

    MetadataElement(
        name="number_of_models",
        default=0,
        desc="Number of alignmened sequences",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            if dataset.metadata.number_of_models == 1:
                dataset.blurb = "1 alignment"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_models} alignments"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        return file_prefix.startswith("#FormatVersion Mauve1")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        dataset.metadata.number_of_models = generic_util.count_special_lines(
            "^#Sequence([[:digit:]]+)Entry", dataset.file_name
        )


class Msf(Text):
    """
    Multiple sequence alignment format produced by the Accelrys GCG suite and
    other programs.
    """

    edam_data = "data_0863"
    edam_format = "format_1947"
    file_ext = "msf"
