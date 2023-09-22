"""
Data providers for genome visualizations.
"""

import abc
import itertools
import math
import os
import random
import re
import sys
from contextlib import contextmanager
from json import loads
from typing import (
    Any,
    Dict,
    IO,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)

import pysam
from bx.bbi.bigbed_file import BigBedFile
from bx.bbi.bigwig_file import BigWigFile
from bx.interval_index_file import Indexes

from galaxy.datatypes.interval import (
    Bed,
    Gff,
    Gtf,
)
from galaxy.datatypes.util.gff_util import (
    convert_gff_coords_to_bed,
    GFFFeature,
    GFFInterval,
    GFFReaderWrapper,
    parse_gff_attributes,
)
from galaxy.model import DatasetInstance
from galaxy.visualization.data_providers.basic import BaseDataProvider
from galaxy.visualization.data_providers.cigar import get_ref_based_read_seq_and_cigar

#
# Utility functions.
#

# pysam 0.16.0.1 emits logs containing the word 'Error', this can confuse the stdout/stderr checkers.
# Can be be removed once https://github.com/pysam-developers/pysam/issues/939 is resolved.
pysam.set_verbosity(0)

PAYLOAD_LIST_TYPE = List[Optional[Union[str, int, float, List[Tuple[int, int]]]]]


def float_nan(n):
    """
    Return None instead of NaN to pass jQuery 1.4's strict JSON
    """
    if n != n:  # NaN != NaN
        return None
    else:
        return float(n)


def get_bounds(reads, start_pos_index, end_pos_index):
    """
    Returns the minimum and maximum position for a set of reads.
    """
    max_low = sys.maxsize
    max_high = -sys.maxsize
    for read in reads:
        if read[start_pos_index] < max_low:
            max_low = read[start_pos_index]
        if read[end_pos_index] > max_high:
            max_high = read[end_pos_index]
    return max_low, max_high


def _convert_between_ucsc_and_ensemble_naming(chrom):
    """
    Convert between UCSC chromosome ('chr1') naming conventions and Ensembl
    naming conventions ('1')
    """
    if chrom.startswith("chr"):
        # Convert from UCSC to Ensembl
        return chrom[3:]
    else:
        # Convert from Ensembl to UCSC
        return "chr" + chrom


def _chrom_naming_matches(chrom1, chrom2):
    return (chrom1.startswith("chr") and chrom2.startswith("chr")) or (
        not chrom1.startswith("chr") and not chrom2.startswith("chr")
    )


class FeatureLocationIndexDataProvider(BaseDataProvider):
    """
    Reads/writes/queries feature location index (FLI) datasets.
    """

    def __init__(self, converted_dataset):
        self.converted_dataset = converted_dataset

    def get_data(self, query):
        # Init.
        textloc_file = open(self.converted_dataset.file_name)
        line_len = int(textloc_file.readline())
        file_len = os.path.getsize(self.converted_dataset.file_name)
        query = query.lower()

        # Find query in file using binary search.
        low = 0
        high = int(file_len / line_len)
        while low < high:
            mid: int = (low + high) // 2
            position = mid * line_len
            textloc_file.seek(position)

            # Compare line with query and update low, high.
            line = textloc_file.readline()
            if line < query:
                low = mid + 1
            else:
                high = mid

        # Need to move back one line because last line read may be included in
        # results.
        position = low * line_len
        textloc_file.seek(position)

        # At right point in file, generate hits.
        result = []
        while True:
            line = textloc_file.readline()
            if not line.startswith(query):
                break
            if line[-1:] == "\n":
                line = line[:-1]
            result.append(line.split()[1:])

        textloc_file.close()
        return result


class GenomeDataProvider(BaseDataProvider):
    """
    Base class for genome data providers. All genome providers use BED coordinate
    format (0-based, half-open coordinates) for both queries and returned data.
    """

    dataset_type: str

    # Mapping from column name to payload data; this mapping is used to create
    # filters. Key is column name, value is a dict with mandatory key 'index'
    # and optional key 'name'. E.g. this defines column 4:
    # col_name_data_attr_mapping = {4 : { index: 5, name: 'Score' } }
    col_name_data_attr_mapping: Dict[Union[str, int], Dict] = {}

    def __init__(
        self,
        converted_dataset=None,
        original_dataset=None,
        dependencies=None,
        error_max_vals="Only the first %i %s in this region are displayed.",
    ):
        super().__init__(
            converted_dataset=converted_dataset,
            original_dataset=original_dataset,
            dependencies=dependencies,
            error_max_vals=error_max_vals,
        )

    def write_data_to_file(self, regions, filename):
        """
        Write data in region defined by chrom, start, and end to a file.
        """
        raise Exception("Unimplemented Function")

    def valid_chroms(self):
        """
        Returns chroms/contigs that the dataset contains
        """
        return None  # by default

    def has_data(self, chrom, start, end, **kwargs):
        """
        Returns true if dataset has data in the specified genome window, false
        otherwise.
        """
        raise Exception("Unimplemented Function")

    @contextmanager
    def open_data_file(self):
        """
        Open data file for reading data.
        """
        raise Exception("Unimplemented Function")

    def get_iterator(self, data_file, chrom, start, end, **kwargs) -> Iterator[str]:
        """
        Returns an iterator that provides data in the region chrom:start-end
        """
        raise Exception("Unimplemented Function")

    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        """
        Process data from an iterator to a format that can be provided to client.
        """
        raise Exception("Unimplemented Function")

    def get_data(self, chrom=None, low=None, high=None, start_val=0, max_vals=sys.maxsize, **kwargs):
        """
        Returns data in region defined by chrom, start, and end. start_val and
        max_vals are used to denote the data to return: start_val is the first element to
        return and max_vals indicates the number of values to return.

        Return value must be a dictionary with the following attributes:
            dataset_type, data
        """
        start, end = int(low), int(high)
        with self.open_data_file() as data_file:
            iterator = self.get_iterator(data_file, chrom, start, end, **kwargs)
            data = self.process_data(iterator, start_val, max_vals, start=start, end=end, **kwargs)
        return data

    def get_genome_data(self, chroms_info, **kwargs):
        """
        Returns data for complete genome.
        """
        genome_data = []
        for chrom_info in chroms_info["chrom_info"]:
            chrom = chrom_info["chrom"]
            chrom_len = chrom_info["len"]
            chrom_data = self.get_data(chrom, 0, chrom_len, **kwargs)
            # FIXME: data providers probably should never return None.
            # Some data providers return None when there's no data, so
            # create a dummy dict if necessary.
            if not chrom_data:
                chrom_data = {"data": None}
            chrom_data["region"] = "%s:%i-%i" % (chrom, 0, chrom_len)
            genome_data.append(chrom_data)

        return {"data": genome_data, "dataset_type": self.dataset_type}

    def get_filters(self):
        """
        Returns filters for provider's data. Return value is a list of
        filters; each filter is a dictionary with the keys 'name', 'index', 'type'.
        NOTE: This method uses the original dataset's datatype and metadata to
        create the filters.
        """
        # Get column names.
        try:
            column_names = self.original_dataset.datatype.column_names  # type: ignore[attr-defined]
        except AttributeError:
            try:
                column_names = list(range(self.original_dataset.metadata.columns))
            except Exception:  # Give up
                return []

        # Dataset must have column types; if not, cannot create filters.
        try:
            column_types = self.original_dataset.metadata.column_types
        except AttributeError:
            return []

        # Create and return filters.
        filters = []
        if self.original_dataset.metadata.viz_filter_cols:
            for viz_col_index in self.original_dataset.metadata.viz_filter_cols:
                # Some columns are optional, so can't assume that a filter
                # column is in dataset.
                if viz_col_index >= len(column_names):
                    continue
                col_name = column_names[viz_col_index]
                # Make sure that column has a mapped index. If not, do not add filter.
                try:
                    attrs = self.col_name_data_attr_mapping[col_name]
                except KeyError:
                    continue
                filters.append({"name": attrs["name"], "type": column_types[viz_col_index], "index": attrs["index"]})
        return filters

    def get_default_max_vals(self):
        return 5000


#
# -- Base mixins and providers --
#


class FilterableMixin:
    original_dataset: DatasetInstance

    def get_filters(self):
        """Returns a dataset's filters."""
        # Get filters.
        # TODOs:
        # (a) might be useful to move this into each datatype's set_meta method;
        # (b) could look at first N lines to ensure GTF attribute types are consistent.
        #
        filters = []
        # HACK: first 8 fields are for drawing, so start filter column index at 9.
        filter_col = 8
        if isinstance(self.original_dataset.datatype, Gff):
            # Can filter by score and GTF attributes.
            filters = [
                {"name": "Score", "type": "number", "index": filter_col, "tool_id": "Filter1", "tool_exp_name": "c6"}
            ]
            filter_col += 1
            if isinstance(self.original_dataset.datatype, Gtf):
                # Create filters based on dataset metadata.
                for name, a_type in self.original_dataset.metadata.attribute_types.items():
                    if a_type in ["int", "float"]:
                        filters.append(
                            {
                                "name": name,
                                "type": "number",
                                "index": filter_col,
                                "tool_id": "gff_filter_by_attribute",
                                "tool_exp_name": name,
                            }
                        )
                        filter_col += 1
        elif isinstance(self.original_dataset.datatype, Bed):
            # Can filter by score column only.
            filters = [
                {"name": "Score", "type": "number", "index": filter_col, "tool_id": "Filter1", "tool_exp_name": "c5"}
            ]

        return filters


class TabixDataProvider(GenomeDataProvider, FilterableMixin):
    """
    Tabix index data provider for the Galaxy track browser.
    """

    dataset_type = "tabix"

    col_name_data_attr_mapping: Dict[Union[str, int], Dict] = {4: {"index": 4, "name": "Score"}}

    @contextmanager
    def open_data_file(self):
        # We create a symlink to the index file. This is
        # required until https://github.com/pysam-developers/pysam/pull/586 is merged.
        index_path = self.converted_dataset.file_name
        with pysam.TabixFile(self.dependencies["bgzip"].file_name, index=index_path) as f:
            yield f

    def get_iterator(self, data_file, chrom, start, end, **kwargs) -> Iterator[str]:
        # chrom must be a string, start/end integers.
        # in previous versions of pysam, unicode was accepted for chrom, but not in 8.4
        chrom = str(chrom)
        start = int(start)
        end = int(end)
        if end >= (2 << 29):
            end = 2 << 29 - 1  # Tabix-enforced maximum
        # Get iterator using either naming scheme.
        iterator: Iterator[str] = iter([])
        if chrom in data_file.contigs:
            iterator = data_file.fetch(reference=chrom, start=start, end=end)
        else:
            # Try alternative naming scheme.
            chrom = _convert_between_ucsc_and_ensemble_naming(chrom)
            if chrom in data_file.contigs:
                iterator = data_file.fetch(reference=chrom, start=start, end=end)

        return iterator

    def write_data_to_file(self, regions, filename):
        with self.open_data_file() as data_file, open(filename, "w") as out:
            for region in regions:
                # Write data in region.
                iterator = self.get_iterator(data_file, region.chrom, region.start, region.end)
                for line in iterator:
                    out.write(f"{line}\n")


#
# -- Interval data providers --
#


class IntervalDataProvider(GenomeDataProvider):
    """
    Processes interval data from native format to payload format.

    Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
    """

    dataset_type = "interval_index"

    def get_iterator(self, data_file, chrom, start, end, **kwargs):
        raise Exception("Unimplemented Function")

    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        """
        Provides
        """
        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <strand> ]
        #
        # First three entries are mandatory, others are optional.
        #
        filter_cols = loads(kwargs.get("filter_cols", "[]"))
        no_detail = "no_detail" in kwargs
        rval = []
        message = None

        # Subtract one b/c columns are 1-based but indices are 0-based.
        def col_fn(col):
            return None if col is None else col - 1

        start_col = self.original_dataset.metadata.startCol - 1
        end_col = self.original_dataset.metadata.endCol - 1
        strand_col = col_fn(self.original_dataset.metadata.strandCol)
        name_col = col_fn(self.original_dataset.metadata.nameCol)
        for count, line in enumerate(iterator):
            if count < start_val:
                continue
            if max_vals and count - start_val >= max_vals:
                message = self.error_max_vals % (max_vals, "features")
                break

            feature = line.split()
            length = len(feature)
            # Unique id is just a hash of the line
            payload: PAYLOAD_LIST_TYPE = [hash(line), int(feature[start_col]), int(feature[end_col])]

            if no_detail:
                rval.append(payload)
                continue

            # Name, strand.
            if name_col:
                payload.append(feature[name_col])
            if strand_col:
                # Put empty name as placeholder.
                if not name_col:
                    payload.append("")
                payload.append(feature[strand_col])

            # Score (filter data)
            if length >= 5 and filter_cols and filter_cols[0] == "Score":
                try:
                    payload.append(float(feature[4]))
                except Exception:
                    payload.append(feature[4])

            rval.append(payload)

        return {"data": rval, "message": message}

    def write_data_to_file(self, regions, filename):
        raise Exception("Unimplemented Function")


class IntervalTabixDataProvider(TabixDataProvider, IntervalDataProvider):
    """
    Provides data from a BED file indexed via tabix.
    """


#
# -- BED data providers --
#


class BedDataProvider(GenomeDataProvider):
    """
    Processes BED data from native format to payload format.

    Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
    """

    dataset_type = "interval_index"

    def get_iterator(self, data_file, chrom, start, end, **kwargs):
        raise Exception("Unimplemented Method")

    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        """
        Provides
        """
        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <strand>, <thick_start>,
        #   <thick_end>, <blocks> ]
        #
        # First three entries are mandatory, others are optional.
        #
        filter_cols = loads(kwargs.get("filter_cols", "[]"))
        no_detail = "no_detail" in kwargs
        rval = []
        message = None
        for count, line in enumerate(iterator):
            if count < start_val:
                continue
            if max_vals and count - start_val >= max_vals:
                message = self.error_max_vals % (max_vals, "features")
                break
            # TODO: can we use column metadata to fill out payload?
            # TODO: use function to set payload data

            feature = line.split()
            length = len(feature)
            # Unique id is just a hash of the line
            payload: PAYLOAD_LIST_TYPE = [hash(line), int(feature[1]), int(feature[2])]

            if no_detail:
                rval.append(payload)
                continue

            # Name, strand, thick start, thick end.
            if length >= 4:
                payload.append(feature[3])
            if length >= 6:
                payload.append(feature[5])
            if length >= 8:
                payload.append(int(feature[6]))
                payload.append(int(feature[7]))

            # Blocks.
            if length >= 12:
                block_sizes = [int(n) for n in feature[10].split(",") if n != ""]
                block_starts = [int(n) for n in feature[11].split(",") if n != ""]
                blocks = list(zip(block_sizes, block_starts))
                payload.append(
                    [(int(feature[1]) + block[1], int(feature[1]) + block[1] + block[0]) for block in blocks]
                )

            # Score (filter data)
            if length >= 5 and filter_cols and filter_cols[0] == "Score":
                # If dataset doesn't have name/strand/thick start/thick end/blocks,
                # add placeholders. There should be 8 entries if all attributes
                # are present.
                payload.extend([None for i in range(8 - len(payload))])

                try:
                    payload.append(float(feature[4]))
                except Exception:
                    payload.append(feature[4])

            rval.append(payload)

        return {"data": rval, "dataset_type": self.dataset_type, "message": message}

    def write_data_to_file(self, regions, filename):
        with open(filename, "w") as out:
            for region in regions:
                # Write data in region.
                chrom = region.chrom
                start = region.start
                end = region.end
                with self.open_data_file() as data_file:
                    iterator = self.get_iterator(data_file, chrom, start, end)
                    for line in iterator:
                        out.write(f"{line}\n")


class BedTabixDataProvider(TabixDataProvider, BedDataProvider):
    """
    Provides data from a BED file indexed via tabix.
    """


class RawBedDataProvider(BedDataProvider):
    """
    Provide data from BED file.

    NOTE: this data provider does not use indices, and hence will be very slow
    for large datasets.
    """

    def get_iterator(self, data_file, chrom, start, end, **kwargs):
        # Read first line in order to match chrom naming format.
        line = data_file.readline()
        dataset_chrom = line.split()[0]
        if not _chrom_naming_matches(chrom, dataset_chrom):
            chrom = _convert_between_ucsc_and_ensemble_naming(chrom)
        # Undo read.
        data_file.seek(0)

        def line_filter_iter():
            with open(self.original_dataset.file_name) as data_file:
                for line in data_file:
                    if line.startswith("track") or line.startswith("browser"):
                        continue
                    feature = line.split()
                    feature_chrom = feature[0]
                    feature_start = int(feature[1])
                    feature_end = int(feature[2])
                    if (
                        (chrom is not None and feature_chrom != chrom)
                        or (start is not None and feature_start > end)
                        or (end is not None and feature_end < start)
                    ):
                        continue
                    yield line

        return line_filter_iter()


#
# -- VCF data providers --
#


class VcfDataProvider(GenomeDataProvider):
    """
    Abstract class that processes VCF data from native format to payload format.

    Payload format: An array of entries for each locus in the file. Each array
    has the following entries:

        1. GUID (unused)
        2. location (0-based)
        3. reference base(s)
        4. alternative base(s)
        5. quality score
        6. whether variant passed filter
        7. sample genotypes -- a single string with samples separated by commas; empty string
           denotes the reference genotype
        8. allele counts for each alternative

    """

    col_name_data_attr_mapping: Dict[Union[str, int], Dict] = {"Qual": {"index": 6, "name": "Qual"}}

    dataset_type = "variant"

    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        """
        Returns a dict with the following attributes::

            data - a list of variants with the format

            .. raw:: text

                [<guid>, <start>, <end>, <name>, cigar, seq]

            message - error/informative message

        """
        data = []
        message = None

        def get_mapping(ref, alt):
            """
            Returns ( offset, new_seq, cigar ) tuple that defines mapping of
            alt to ref. Cigar format is an array of [ op_index, length ] pairs
            where op_index is the 0-based index into the string "MIDNSHP=X"
            """

            cig_ops = "MIDNSHP=X"

            ref_len = len(ref)
            alt_len = len(alt)

            # Substitutions?
            if ref_len == alt_len:
                return 0, alt, [[cig_ops.find("M"), ref_len]]

            # Deletions?
            alt_in_ref_index = ref.find(alt)
            if alt_in_ref_index != -1:
                return alt_in_ref_index, ref[alt_in_ref_index + 1 :], [[cig_ops.find("D"), ref_len - alt_len]]

            # Insertions?
            ref_in_alt_index = alt.find(ref)
            if ref_in_alt_index != -1:
                return ref_in_alt_index, alt[ref_in_alt_index + 1 :], [[cig_ops.find("I"), alt_len - ref_len]]

        # Pack data.
        genotype_re = re.compile(r"/|\|")
        for count, line in enumerate(iterator):
            if count < start_val:
                continue
            if max_vals and count - start_val >= max_vals:
                message = self.error_max_vals % (max_vals, "features")
                break

            # Split line and aggregate data.
            feature = line.split()
            pos, c_id, ref, alt, qual, c_filter, info = feature[1:8]

            # Format and samples data are optional.
            samples_data = []
            if len(feature) > 8:
                samples_data = feature[9:]

            # VCF is 1-based but provided position is 0-based.
            pos = int(pos) - 1

            # FIXME: OK to skip?
            if alt == ".":
                count -= 1
                continue

            # Set up array to track allele counts.
            allele_counts = [0 for i in range(alt.count(",") + 1)]
            sample_gts = []

            if samples_data:
                # Process and pack samples' genotype and count alleles across samples.
                alleles_seen: Dict[int, bool] = {}
                has_alleles = False

                for sample in samples_data:
                    # Parse and count alleles.
                    genotype = sample.split(":")[0]
                    has_alleles = False
                    alleles_seen.clear()
                    for allele_str in genotype_re.split(genotype):
                        try:
                            # This may throw a ValueError if allele is missing.
                            allele = int(allele_str)

                            # Only count allele if it hasn't been seen yet.
                            if allele != 0 and allele not in alleles_seen:
                                allele_counts[allele - 1] += 1
                                alleles_seen[allele] = True
                                has_alleles = True
                        except ValueError:
                            pass

                    # If no alleles, use empty string as proxy.
                    if not has_alleles:
                        genotype = ""

                    sample_gts.append(genotype)
            else:
                # No samples, so set allele count and sample genotype manually.
                allele_counts = [1]
                sample_gts = ["1/1"]

            # Add locus data.
            locus_data = [-1, pos, c_id, ref, alt, qual, c_filter, ",".join(sample_gts)]
            locus_data.extend(allele_counts)
            data.append(locus_data)

        return {"data": data, "message": message}

    def write_data_to_file(self, regions, filename):
        out = open(filename, "w")
        with self.open_data_file() as data_file:
            for region in regions:
                # Write data in region.
                iterator = self.get_iterator(data_file, region.chrom, region.start, region.end)
                for line in iterator:
                    out.write(f"{line}\n")


class VcfTabixDataProvider(TabixDataProvider, VcfDataProvider):
    """
    Provides data from a VCF file indexed via tabix.
    """

    dataset_type = "variant"


class RawVcfDataProvider(VcfDataProvider):
    """
    Provide data from VCF file.

    NOTE: this data provider does not use indices, and hence will be very slow
    for large datasets.
    """

    @contextmanager
    def open_data_file(self):
        with open(self.original_dataset.file_name) as f:
            yield f

    def get_iterator(self, data_file, chrom, start, end, **kwargs):
        # Skip comments.
        line = None
        for line in data_file:
            if not line.startswith("#"):
                break

        # If last line is a comment, there are no data lines.
        if line.startswith("#"):
            return []

        # Match chrom naming format.
        if line:
            dataset_chrom = line.split()[0]
            if not _chrom_naming_matches(chrom, dataset_chrom):
                chrom = _convert_between_ucsc_and_ensemble_naming(chrom)

        def line_in_region(vcf_line, chrom, start, end):
            """Returns true if line is in region."""
            variant_chrom, variant_start = vcf_line.split()[0:2]
            # VCF format is 1-based.
            variant_start = int(variant_start) - 1
            return variant_chrom == chrom and variant_start >= start and variant_start <= end

        def line_filter_iter():
            """Yields lines in data that are in region chrom:start-end"""
            # Yield data line read above.
            if line_in_region(line, chrom, start, end):
                yield line

            # Search for and yield other data lines.
            for data_line in data_file:
                if line_in_region(data_line, chrom, start, end):
                    yield data_line

        return line_filter_iter()


class BamDataProvider(GenomeDataProvider, FilterableMixin):
    """
    Provides access to intervals from a sorted indexed BAM file. Coordinate
    data is reported in BED format: 0-based, half-open.
    """

    dataset_type = "bai"

    def get_filters(self):
        """
        Returns filters for dataset.
        """
        # HACK: first 7 fields are for drawing, so start filter column index at 7.
        filter_col = 7
        filters = []
        filters.append({"name": "Mapping Quality", "type": "number", "index": filter_col})
        return filters

    def write_data_to_file(self, regions, filename):
        """
        Write reads in regions to file.
        """

        # Open current BAM file using index.
        bamfile = pysam.AlignmentFile(
            self.original_dataset.file_name, mode="rb", index_filename=self.converted_dataset.file_name
        )

        # TODO: write headers as well?
        new_bamfile = pysam.AlignmentFile(filename, template=bamfile, mode="wb")

        for region in regions:
            # Write data from region.
            chrom = region.chrom
            start = region.start
            end = region.end

            try:
                data = bamfile.fetch(start=start, end=end, reference=chrom)
            except ValueError:
                # Try alternative chrom naming.
                chrom = _convert_between_ucsc_and_ensemble_naming(chrom)
                try:
                    data = bamfile.fetch(start=start, end=end, reference=chrom)
                except ValueError:
                    return None

            # Write reads in region.
            for read in data:
                new_bamfile.write(read)

        # Cleanup.
        new_bamfile.close()
        bamfile.close()

    @contextmanager
    def open_data_file(self):
        # Attempt to open the BAM file with index
        with pysam.AlignmentFile(
            self.original_dataset.file_name, mode="rb", index_filename=self.converted_dataset.file_name
        ) as f:
            yield f

    def get_iterator(self, data_file, chrom, start, end, **kwargs) -> Iterator[str]:
        """
        Returns an iterator that provides data in the region chrom:start-end
        """

        # Fetch and return data.
        chrom = str(chrom)
        start = int(start)
        end = int(end)
        try:
            data = data_file.fetch(start=start, end=end, reference=chrom)
        except ValueError:
            # Try alternative chrom naming.
            chrom = _convert_between_ucsc_and_ensemble_naming(chrom)
            try:
                data = data_file.fetch(start=start, end=end, reference=chrom)
            except ValueError:
                return iter([])
        return data

    def process_data(
        self,
        iterator,
        start_val=0,
        max_vals=None,
        ref_seq=None,
        iterator_type="nth",
        mean_depth=None,
        start=0,
        end=0,
        **kwargs,
    ):
        """
        Returns a dict with the following attributes::

            data - a list of reads with the format
                [<guid>, <start>, <end>, <name>, <read_1>, <read_2>, [empty], <mapq_scores>]

                where <read_1> has the format
                    [<start>, <end>, <cigar>, <strand>, <read_seq>]

                and <read_2> has the format
                    [<start>, <end>, <cigar>, <strand>, <read_seq>]

                Field 7 is empty so that mapq scores' location matches that in single-end reads.
                For single-end reads, read has format:
                    [<guid>, <start>, <end>, <name>, <cigar>, <strand>, <seq>, <mapq_score>]

                NOTE: read end and sequence data are not valid for reads outside of
                requested region and should not be used.

            max_low - lowest coordinate for the returned reads
            max_high - highest coordinate for the returned reads
            message - error/informative message
        """
        # No iterator indicates no reads.
        if iterator is None:
            return {"data": [], "message": None}

        #
        # Helper functions.
        #

        def decode_strand(read_flag, mask):
            """Decode strand from read flag."""

            strand_flag = read_flag & mask == 0
            if strand_flag:
                return "+"
            else:
                return "-"

        def _random_read_iterator(read_iterator, threshold):
            """
            An iterator that returns a random stream of reads from the read_iterator
            as well as corresponding pairs for returned reads.
            threshold is a value in [0,1] that denotes the percentage of reads
            to return.
            """
            for e in read_iterator:
                if e.qname in paired_pending or random.uniform(0, 1) <= threshold:
                    yield e

        def _nth_read_iterator(read_iterator, threshold):
            """
            An iterator that returns every nth read.
            """

            # Convert threshold to N for stepping through iterator.
            n = int(1 / threshold)
            return itertools.islice(read_iterator, None, None, n)

        # -- Choose iterator. --

        # Calculate threshold for non-sequential iterators based on mean_depth and read length.
        try:
            first_read = next(iterator)
        except StopIteration:
            # no reads.
            return {"data": [], "message": None, "max_low": start, "max_high": start}

        read_len = len(first_read.seq)
        num_reads = max((end - start) * mean_depth / float(read_len), 1)
        threshold = float(max_vals) / num_reads
        iterator = itertools.chain(iter([first_read]), iterator)

        # Use specified iterator type, save for when threshold is >= 1.
        # A threshold of >= 1 indicates all reads are to be returned, so no
        # sampling needed and seqential iterator will be used.
        if iterator_type == "sequential" or threshold >= 1:
            read_iterator = iterator
        elif iterator_type == "random":
            read_iterator = _random_read_iterator(iterator, threshold)
        elif iterator_type == "nth":
            read_iterator = _nth_read_iterator(iterator, threshold)

        #
        # Encode reads as list of lists.
        #
        results = []
        paired_pending: Dict[str, Dict[str, Any]] = {}
        unmapped = 0
        message = None
        count = 0
        for read in read_iterator:
            if count < start_val:
                continue
            if (count - start_val - unmapped) >= max_vals:
                message = self.error_max_vals % (max_vals, "reads")
                break

            # If not mapped, skip read.
            is_mapped = read.flag & 0x0004 == 0
            if not is_mapped:
                unmapped += 1
                continue

            qname = read.qname
            seq = read.seq
            strand = decode_strand(read.flag, 0x0010)
            if read.cigar is not None:
                read_len = sum(cig[1] for cig in read.cigar)  # Use cigar to determine length
            else:
                read_len = len(seq)  # If no cigar, just use sequence length

            if read.is_proper_pair:
                if qname in paired_pending:
                    # Found pair.
                    pair = paired_pending[qname]
                    results.append(
                        [
                            hash("%i_%s" % (pair["start"], qname)),
                            pair["start"],
                            read.pos + read_len,
                            qname,
                            [pair["start"], pair["end"], pair["cigar"], pair["strand"], pair["seq"]],
                            [read.pos, read.pos + read_len, read.cigar, strand, seq],
                            None,
                            [pair["mapq"], read.mapq],
                        ]
                    )
                    del paired_pending[qname]
                else:
                    # Insert first of pair.
                    paired_pending[qname] = {
                        "start": read.pos,
                        "end": read.pos + read_len,
                        "seq": seq,
                        "mate_start": read.mpos,
                        "rlen": read_len,
                        "strand": strand,
                        "cigar": read.cigar,
                        "mapq": read.mapq,
                    }
                    count += 1
            else:
                results.append(
                    [
                        hash("%i_%s" % (read.pos, qname)),
                        read.pos,
                        read.pos + read_len,
                        qname,
                        read.cigar,
                        strand,
                        read.seq,
                        read.mapq,
                    ]
                )
                count += 1

        # Take care of reads whose mates are out of range.
        for qname, read in paired_pending.items():
            if read["mate_start"] < read["start"]:
                # Mate is before read.
                read_start = read["mate_start"]
                read_end = read["end"]
                # Make read_1 start=end so that length is 0 b/c we don't know
                # read length.
                r1 = [read["mate_start"], read["mate_start"]]
                r2 = [read["start"], read["end"], read["cigar"], read["strand"], read["seq"]]
            else:
                # Mate is after read.
                read_start = read["start"]
                # Make read_2 start=end so that length is 0 b/c we don't know
                # read length. Hence, end of read is start of read_2.
                read_end = read["mate_start"]
                r1 = [read["start"], read["end"], read["cigar"], read["strand"], read["seq"]]
                r2 = [read["mate_start"], read["mate_start"]]

            results.append(
                [hash("%i_%s" % (read_start, qname)), read_start, read_end, qname, r1, r2, [read["mapq"], 125]]
            )

        # Clean up. TODO: is this needed? If so, we'll need a cleanup function after processing the data.
        # bamfile.close()

        def compress_seq_and_cigar(read, start_field, cigar_field, seq_field):
            """
            Use reference-based compression to compress read sequence and cigar.
            """
            read_seq, read_cigar = get_ref_based_read_seq_and_cigar(
                read[seq_field].upper(), read[start_field], ref_seq.sequence, ref_seq.start, read[cigar_field]
            )
            read[seq_field] = read_seq
            read[cigar_field] = read_cigar

        def convert_cigar(read, start_field, cigar_field, seq_field):
            """
            Convert read cigar from pysam format to string format.
            """
            cigar_ops = "MIDNSHP=X"
            read_cigar = ""
            for op_tuple in read[cigar_field]:
                read_cigar += "%i%s" % (op_tuple[1], cigar_ops[op_tuple[0]])
            read[cigar_field] = read_cigar

        # Choose method for processing reads. Use reference-based compression
        # if possible. Otherwise, convert cigar.
        if ref_seq:
            # Uppercase for easy comparison.
            ref_seq.sequence = ref_seq.sequence.upper()
            process_read = compress_seq_and_cigar
        else:
            process_read = convert_cigar

        # Process reads.
        for read in results:
            if isinstance(read[5], list):
                # Paired-end read.
                if len(read[4]) > 2:
                    process_read(read[4], 0, 2, 4)
                if len(read[5]) > 2:
                    process_read(read[5], 0, 2, 4)
            else:
                # Single-end read.
                process_read(read, 1, 4, 6)

        max_low, max_high = get_bounds(results, 1, 2)

        return {"data": results, "message": message, "max_low": max_low, "max_high": max_high}


class SamDataProvider(BamDataProvider):
    dataset_type = "bai"

    def __init__(self, converted_dataset=None, original_dataset=None, dependencies=None):
        """Create SamDataProvider."""
        super().__init__(
            converted_dataset=converted_dataset, original_dataset=original_dataset, dependencies=dependencies
        )

        # To use BamDataProvider, original dataset must be BAM and
        # converted dataset must be BAI. Use BAI from BAM metadata.
        if converted_dataset:
            self.original_dataset = converted_dataset
            self.converted_dataset = converted_dataset.metadata.bam_index


class BBIDataProvider(GenomeDataProvider):
    """
    BBI data provider for the Galaxy track browser.
    """

    dataset_type = "bigwig"

    @abc.abstractmethod
    def _get_dataset(self) -> Tuple[IO[bytes], Union[BigBedFile, BigWigFile]]:
        ...

    def valid_chroms(self):
        # No way to return this info as of now
        return None

    def has_data(self, chrom):
        f, bbi = self._get_dataset()
        all_dat = bbi.query(chrom, 0, 2147483647, 1) or bbi.query(
            _convert_between_ucsc_and_ensemble_naming(chrom), 0, 2147483647, 1
        )
        f.close()
        return all_dat is not None

    def get_data(self, chrom, start, end, start_val=0, max_vals=None, num_samples=1000, **kwargs):
        start = int(start)
        end = int(end)

        # Helper function for getting summary data regardless of chromosome
        # naming convention.
        def _summarize_bbi(bbi, chrom, start, end, num_points):
            return bbi.summarize(chrom, start, end, num_points) or bbi.summarize(
                _convert_between_ucsc_and_ensemble_naming(chrom), start, end, num_points
            )

        # Bigwig can be a standalone bigwig file, in which case we use
        # original_dataset, or coming from wig->bigwig conversion in
        # which we use converted_dataset
        f, bbi = self._get_dataset()

        # If stats requested, compute overall summary data for the range
        # start:endbut no reduced data. This is currently used by client
        # to determine the default range.
        if "stats" in kwargs:
            summary = _summarize_bbi(bbi, chrom, start, end, 1)
            f.close()

            min_val = 0
            max_val = 0
            mean = 0
            sd = 0.0
            if summary is not None:
                # Does the summary contain any defined values?
                valid_count = summary.valid_count[0]
                if summary.valid_count > 0:
                    # Compute $\mu \pm 2\sigma$ to provide an estimate for upper and lower
                    # bounds that contain ~95% of the data.
                    mean = summary.sum_data[0] / valid_count
                    var = max(summary.sum_squares[0] - mean, 0)  # Prevent variance underflow.
                    if valid_count > 1:
                        var /= valid_count - 1
                    sd = math.sqrt(var)
                    min_val = summary.min_val[0]
                    max_val = summary.max_val[0]

            return dict(data=dict(min=min_val, max=max_val, mean=mean, sd=sd))

        def summarize_region(bbi, chrom, start, end, num_points):
            """
            Returns results from summarizing a region using num_points.
            NOTE: num_points cannot be greater than end - start or BBI
            will return None for all positions.
            """
            result = []

            # Get summary; this samples at intervals of length
            # (end - start)/num_points -- i.e. drops any fractional component
            # of interval length.
            summary = _summarize_bbi(bbi, chrom, start, end, num_points)
            if summary:
                # mean = summary.sum_data / summary.valid_count

                # Standard deviation by bin, not yet used
                # var = summary.sum_squares - mean
                # var /= minimum( valid_count - 1, 1 )
                # sd = sqrt( var )

                pos = start
                step_size = (end - start) / num_points

                for i in range(num_points):
                    result.append((pos, float_nan(summary.sum_data[i] / summary.valid_count[i])))
                    pos += step_size

            return result

        # Approach is different depending on region size.
        num_samples = int(num_samples)
        if end - start < num_samples:
            # Get values for individual bases in region, including start and end.
            # To do this, need to increase end to next base and request number of points.
            num_points = end - start + 1
            end += 1
        else:
            #
            # The goal is to sample the region between start and end uniformly
            # using ~N (num_samples) data points. The challenge is that the size of
            # sampled intervals rarely is full bases, so sampling using N points
            # will leave the end of the region unsampled due to remainders for
            # each interval. To recitify this, a new N is calculated based on the
            # step size that covers as much of the region as possible.
            #
            # However, this still leaves some of the region unsampled. This
            # could be addressed by repeatedly sampling remainder using a
            # smaller and smaller step_size, but that would require iteratively
            # going to BBI, which could be time consuming.
            #

            # Start with N samples.
            num_points = num_samples
            step_size = (end - start) // num_points
            # Add additional points to sample in the remainder not covered by
            # the initial N samples.
            remainder_start = start + step_size * num_points
            additional_points = (end - remainder_start) // step_size
            num_points += additional_points

        result = summarize_region(bbi, chrom, start, end, num_points)

        # Cleanup and return.
        f.close()
        return {"data": result, "dataset_type": self.dataset_type}


class BigBedDataProvider(BBIDataProvider):
    def _get_dataset(self):
        # Nothing converts to bigBed so we don't consider converted dataset
        f = open(self.original_dataset.file_name, "rb")
        return f, BigBedFile(file=f)


class BigWigDataProvider(BBIDataProvider):
    """
    Provides data from BigWig files; position data is reported in 1-based
    coordinate system, i.e. wiggle format.
    """

    def _get_dataset(self):
        if self.converted_dataset is not None:
            f = open(self.converted_dataset.file_name, "rb")
        else:
            f = open(self.original_dataset.file_name, "rb")
        return f, BigWigFile(file=f)


class IntervalIndexDataProvider(GenomeDataProvider, FilterableMixin):
    """
    Interval index files used for GFF, Pileup files.
    """

    col_name_data_attr_mapping = {4: {"index": 4, "name": "Score"}}

    dataset_type = "interval_index"

    def write_data_to_file(self, regions, filename):
        index = Indexes(self.converted_dataset.file_name)
        with open(self.original_dataset.file_name) as source, open(filename, "w") as out:
            for region in regions:
                # Write data from region.
                chrom = region.chrom
                start = region.start
                end = region.end
                for _start, _end, offset in index.find(chrom, start, end):
                    source.seek(offset)

                    # HACK: write differently depending on original dataset format.
                    if self.original_dataset.ext not in ["gff", "gff3", "gtf"]:
                        line = source.readline()
                        out.write(line)
                    else:
                        reader = GFFReaderWrapper(source, fix_strand=True)
                        feature = next(reader)
                        for interval in feature.intervals:
                            out.write("\t".join(interval.fields) + "\n")

    @contextmanager
    def open_data_file(self):
        i = Indexes(self.converted_dataset.file_name)
        yield i

    def get_iterator(self, data_file, chrom, start, end, **kwargs) -> Iterator[str]:
        """
        Returns an iterator for data in data_file in chrom:start-end
        """
        if chrom not in data_file.indexes:
            # Try alternative naming.
            chrom = _convert_between_ucsc_and_ensemble_naming(chrom)

        return data_file.find(chrom, start, end)

    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        results = []
        message = None
        with open(self.original_dataset.file_name) as source:
            # Build data to return. Payload format is:
            # [ <guid/offset>, <start>, <end>, <name>, <score>, <strand>, <thick_start>,
            #   <thick_end>, <blocks> ]
            #
            # First three entries are mandatory, others are optional.
            filter_cols = loads(kwargs.get("filter_cols", "[]"))
            no_detail = "no_detail" in kwargs
            for count, val in enumerate(iterator):
                offset = val[2]
                if count < start_val:
                    continue
                if count - start_val >= max_vals:
                    message = self.error_max_vals % (max_vals, "features")
                    break
                source.seek(offset)
                # TODO: can we use column metadata to fill out payload?

                # GFF dataset.
                reader = GFFReaderWrapper(source, fix_strand=True)
                feature = next(reader)
                payload = package_gff_feature(feature, no_detail, filter_cols)
                payload.insert(0, offset)

                results.append(payload)

        return {"data": results, "message": message}


class RawGFFDataProvider(GenomeDataProvider):
    """
    Provide data from GFF file that has not been indexed.

    NOTE: this data provider does not use indices, and hence will be very slow
    for large datasets.
    """

    dataset_type = "interval_index"

    def get_iterator(self, data_file, chrom, start, end, **kwargs):
        """
        Returns an iterator that provides data in the region chrom:start-end as well as
        a file offset.
        """
        source = open(self.original_dataset.file_name)

        # Read first line in order to match chrom naming format.
        line = source.readline()

        # If line empty, assume file is empty and return empty iterator.
        if len(line) == 0:
            return iter([])

        # Determine chromosome naming format.
        dataset_chrom = line.split()[0]
        if not _chrom_naming_matches(chrom, dataset_chrom):
            chrom = _convert_between_ucsc_and_ensemble_naming(chrom)
        # Undo read.
        source.seek(0)

        def features_in_region_iter():
            offset = 0
            for feature in GFFReaderWrapper(source, fix_strand=True):
                # Only provide features that are in region.
                feature_start, feature_end = convert_gff_coords_to_bed([feature.start, feature.end])
                if feature.chrom == chrom and feature_end > start and feature_start < end:
                    yield feature, offset
                offset += feature.raw_size

        return features_in_region_iter()

    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        """
        Process data from an iterator to a format that can be provided to client.
        """
        filter_cols = loads(kwargs.get("filter_cols", "[]"))
        no_detail = "no_detail" in kwargs
        results = []
        message = None

        for count, (feature, offset) in enumerate(iterator):
            if count < start_val:
                continue
            if count - start_val >= max_vals:
                message = self.error_max_vals % (max_vals, "reads")
                break

            payload = package_gff_feature(feature, no_detail=no_detail, filter_cols=filter_cols)
            payload.insert(0, offset)
            results.append(payload)

        return {"data": results, "dataset_type": self.dataset_type, "message": message}


class GtfTabixDataProvider(TabixDataProvider):
    """
    Returns data from GTF datasets that are indexed via tabix.
    """

    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        # Loop through lines and group by transcript_id; each group is a feature.

        # TODO: extend this code or use code in gff_util to process GFF/3 as well
        # and then create a generic GFFDataProvider that can be used with both
        # raw and tabix datasets.
        features: Dict[str, List[GFFInterval]] = {}

        for line in iterator:
            line_attrs = parse_gff_attributes(line.split("\t")[8])
            transcript_id = line_attrs["transcript_id"]
            feature_list: List[GFFInterval]
            if transcript_id in features:
                feature_list = features[transcript_id]
            else:
                feature_list = []
                features[transcript_id] = feature_list
            feature_list.append(GFFInterval(None, line.split("\t")))

        # Process data.
        filter_cols = loads(kwargs.get("filter_cols", "[]"))
        no_detail = "no_detail" in kwargs
        results = []
        message = None

        for count, intervals in enumerate(features.values()):
            if count < start_val:
                continue
            if count - start_val >= max_vals:
                message = self.error_max_vals % (max_vals, "reads")
                break

            feature = GFFFeature(None, intervals=intervals)
            payload = package_gff_feature(feature, no_detail=no_detail, filter_cols=filter_cols)
            payload.insert(0, feature.intervals[0].attributes["transcript_id"])
            results.append(payload)

        return {"data": results, "message": message}


#
# -- ENCODE Peak data providers.
#


class ENCODEPeakDataProvider(GenomeDataProvider):
    """
    Abstract class that processes ENCODEPeak data from native format to payload format.

    Payload format: [ uid (offset), start, end, name, strand, thick_start, thick_end, blocks ]
    """

    def get_iterator(self, data_file, chrom, start, end, **kwargs):
        raise Exception("Unimplemented Method")

    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        """
        Provides
        """

        # FIXMEs:
        # (1) should be able to unify some of this code with BedDataProvider.process_data
        # (2) are optional number of parameters supported?

        # Build data to return. Payload format is:
        # [ <guid/offset>, <start>, <end>, <name>, <strand>, <thick_start>,
        #   <thick_end>, <blocks> ]
        #
        # First three entries are mandatory, others are optional.
        #
        no_detail = "no_detail" in kwargs
        rval = []
        message = None
        for count, line in enumerate(iterator):
            if count < start_val:
                continue
            if max_vals and count - start_val >= max_vals:
                message = self.error_max_vals % (max_vals, "features")
                break

            feature = line.split()

            # Feature initialization.
            payload: PAYLOAD_LIST_TYPE = [
                # GUID is just a hash of the line
                hash(line),
                # Add start, end.
                int(feature[1]),
                int(feature[2]),
            ]

            if no_detail:
                rval.append(payload)
                continue

            # Extend with additional data.
            payload.extend(
                [
                    # Add name, strand.
                    feature[3],
                    feature[5],
                    # Thick start, end are feature start, end for now.
                    int(feature[1]),
                    int(feature[2]),
                    # No blocks.
                    None,
                    # Filtering data: Score, signalValue, pValue, qValue.
                    float(feature[4]),
                    float(feature[6]),
                    float(feature[7]),
                    float(feature[8]),
                ]
            )

            rval.append(payload)

        return {"data": rval, "message": message}


class ENCODEPeakTabixDataProvider(TabixDataProvider, ENCODEPeakDataProvider):
    """
    Provides data from an ENCODEPeak dataset indexed via tabix.
    """

    def get_filters(self):
        """
        Returns filters for dataset.
        """
        # HACK: first 8 fields are for drawing, so start filter column index at 9.
        filter_col = 8
        filters = []
        filters.append(
            {"name": "Score", "type": "number", "index": filter_col, "tool_id": "Filter1", "tool_exp_name": "c6"}
        )
        filter_col += 1
        filters.append(
            {"name": "Signal Value", "type": "number", "index": filter_col, "tool_id": "Filter1", "tool_exp_name": "c7"}
        )
        filter_col += 1
        filters.append(
            {"name": "pValue", "type": "number", "index": filter_col, "tool_id": "Filter1", "tool_exp_name": "c8"}
        )
        filter_col += 1
        filters.append(
            {"name": "qValue", "type": "number", "index": filter_col, "tool_id": "Filter1", "tool_exp_name": "c9"}
        )
        return filters


#
# -- ChromatinInteraction data providers --
#


class ChromatinInteractionsDataProvider(GenomeDataProvider):
    def process_data(self, iterator, start_val=0, max_vals=None, **kwargs):
        """
        Provides
        """

        rval = []
        message = None
        for count, line in enumerate(iterator):
            if count < start_val:
                continue
            if max_vals and count - start_val >= max_vals:
                message = self.error_max_vals % (max_vals, "interactions")
                break

            feature = line.split()

            s1 = int(feature[1])
            e1 = int(feature[2])
            c = feature[3]
            s2 = int(feature[4])
            e2 = int(feature[5])
            v = float(feature[6])

            # Feature initialization.
            payload = [
                # GUID is just a hash of the line
                hash(line),
                # Add start1, end1, chr2, start2, end2, value.
                s1,
                e1,
                c,
                s2,
                e2,
                v,
            ]

            rval.append(payload)

        return {"data": rval, "message": message}

    def get_default_max_vals(self):
        return 100000


class ChromatinInteractionsTabixDataProvider(TabixDataProvider, ChromatinInteractionsDataProvider):
    def get_iterator(
        self, data_file, chrom, start=0, end=sys.maxsize, interchromosomal=False, **kwargs
    ) -> Iterator[str]:
        """ """
        # Modify start as needed to get earlier interactions with start region.
        span = int(end) - int(start)
        filter_start = max(0, int(start) - span - span / 2)

        def filter(iter):
            for line in iter:
                feature = line.split()
                s1 = int(feature[1])
                e1 = int(feature[2])
                c = feature[3]
                s2 = int(feature[4])
                e2 = int(feature[5])
                # Check for intrachromosal interactions.
                if ((s1 + s2) / 2 <= end) and ((e1 + e2) / 2 >= start) and (c == chrom):
                    yield line
                # Check for interchromosal interactions.
                if interchromosomal and c != chrom:
                    yield line

        return filter(TabixDataProvider.get_iterator(self, data_file, chrom, filter_start, end))


#
# -- Helper methods. --
#


def package_gff_feature(feature, no_detail=False, filter_cols=None) -> PAYLOAD_LIST_TYPE:
    """Package a GFF feature in an array for data providers."""
    filter_cols = filter_cols or []
    feature = convert_gff_coords_to_bed(feature)

    # No detail means only start, end.
    if no_detail:
        return [feature.start, feature.end]

    # Return full feature.
    payload = [
        feature.start,
        feature.end,
        feature.name(),
        feature.strand,
        # No notion of thick start, end in GFF, so make everything
        # thick.
        feature.start,
        feature.end,
    ]

    # HACK: ignore interval with name 'transcript' from feature.
    # Cufflinks puts this interval in each of its transcripts,
    # and they mess up trackster by covering the feature's blocks.
    # This interval will always be a feature's first interval,
    # and the GFF's third column is its feature name.
    feature_intervals = feature.intervals
    if feature.intervals[0].fields[2] == "transcript":
        feature_intervals = feature.intervals[1:]
    # Add blocks.
    block_sizes = [(interval.end - interval.start) for interval in feature_intervals]
    block_starts = [(interval.start - feature.start) for interval in feature_intervals]
    blocks = list(zip(block_sizes, block_starts))
    payload.append([(feature.start + block[1], feature.start + block[1] + block[0]) for block in blocks])

    # Add filter data to payload.
    for col in filter_cols:
        if col == "Score":
            if feature.score == "nan":
                payload.append(feature.score)
            else:
                try:
                    f = float(feature.score)
                    payload.append(f)
                except Exception:
                    payload.append(feature.score)
        elif col in feature.attributes:
            if feature.attributes[col] == "nan":
                payload.append(feature.attributes[col])
            else:
                try:
                    f = float(feature.attributes[col])
                    payload.append(f)
                except Exception:
                    payload.append(feature.attributes[col])
        else:
            # Dummy value.
            payload.append(0)
    return payload
