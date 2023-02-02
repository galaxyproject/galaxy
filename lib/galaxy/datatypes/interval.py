"""
Interval datatypes
"""
import logging
import sys
import tempfile
from typing import (
    cast,
    List,
    Optional,
    Tuple,
    Union,
)
from urllib.parse import quote_plus

import pysam
from bx.intervals.io import (
    GenomicIntervalReader,
    ParseError,
)

from galaxy import util
from galaxy.datatypes import metadata
from galaxy.datatypes.data import DatatypeValidation
from galaxy.datatypes.dataproviders.dataset import (
    DatasetDataProvider,
    GenomicRegionDataProvider,
    IntervalDataProvider,
    WiggleDataProvider,
)
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import (
    DatasetProtocol,
    HasId,
    HasMetadata,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    get_headers,
    iter_headers,
)
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.util.gff_util import (
    parse_gff3_attributes,
    parse_gff_attributes,
)
from galaxy.util import compression_utils
from galaxy.util.compression_utils import FileObjType
from . import (
    data,
    dataproviders,
)

log = logging.getLogger(__name__)

# Contains the meta columns and the words that map to it; list aliases on the
# right side of the : in decreasing order of priority
alias_spec = {
    "chromCol": ["chrom", "CHROMOSOME", "CHROM", "Chromosome Name"],
    "startCol": ["start", "START", "chromStart", "txStart", "Start Position (bp)"],
    "endCol": ["end", "END", "STOP", "chromEnd", "txEnd", "End Position (bp)"],
    "strandCol": ["strand", "STRAND", "Strand"],
    "nameCol": [
        "name",
        "NAME",
        "Name",
        "name2",
        "NAME2",
        "Name2",
        "Ensembl Gene ID",
        "Ensembl Transcript ID",
        "Ensembl Peptide ID",
    ],
}

# a little faster lookup
alias_helper = {}
for key, value in alias_spec.items():
    for elem in value:
        alias_helper[elem] = key

# Constants for configuring viewport generation: If a line is greater than
# VIEWPORT_MAX_READS_PER_LINE * VIEWPORT_READLINE_BUFFER_SIZE bytes in size,
# then we will not generate a viewport for that dataset
VIEWPORT_READLINE_BUFFER_SIZE = 1048576  # 1MB
VIEWPORT_MAX_READS_PER_LINE = 10


@dataproviders.decorators.has_dataproviders
@build_sniff_from_prefix
class Interval(Tabular):
    """Tab delimited data containing interval information"""

    edam_data = "data_3002"
    edam_format = "format_3475"
    file_ext = "interval"
    line_class = "region"
    track_type = "FeatureTrack"
    data_sources = {"data": "tabix", "index": "bigwig"}

    MetadataElement(name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter)
    MetadataElement(name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter)
    MetadataElement(name="endCol", default=3, desc="End column", param=metadata.ColumnParameter)
    MetadataElement(
        name="strandCol",
        default=0,
        desc="Strand column (click box & select)",
        param=metadata.ColumnParameter,
        optional=True,
        no_value=0,
    )
    MetadataElement(
        name="nameCol",
        desc="Name/Identifier column (click box & select)",
        param=metadata.ColumnParameter,
        optional=True,
        no_value=0,
    )
    MetadataElement(name="columns", default=3, desc="Number of columns", readonly=True, visible=False)

    def __init__(self, **kwd):
        """Initialize interval datatype, by adding UCSC display apps"""
        Tabular.__init__(self, **kwd)
        self.add_display_app("ucsc", "display at UCSC", "as_ucsc_display_file", "ucsc_links")

    def init_meta(self, dataset: HasMetadata, copy_from: Optional[HasMetadata] = None) -> None:
        Tabular.init_meta(self, dataset, copy_from=copy_from)

    def set_meta(
        self, dataset: DatasetProtocol, *, overwrite: bool = True, first_line_is_header: bool = False, **kwd
    ) -> None:
        """Tries to guess from the line the location number of the column for the chromosome, region start-end and strand"""
        Tabular.set_meta(self, dataset, overwrite=overwrite, skip=0)
        if dataset.has_data():
            empty_line_count = 0
            num_check_lines = 100  # only check up to this many non empty lines
            with compression_utils.get_fileobj(dataset.file_name) as in_fh:
                for i, line in enumerate(in_fh):
                    line = line.rstrip("\r\n")
                    if line:
                        if first_line_is_header or line[0] == "#":
                            self.init_meta(dataset)
                            line = line.strip("#")
                            elems = line.split("\t")
                            for meta_name, header_list in alias_spec.items():
                                for header_val in header_list:
                                    if header_val in elems:
                                        # found highest priority header to meta_name
                                        setattr(dataset.metadata, meta_name, elems.index(header_val) + 1)
                                        break  # next meta_name
                            break  # Our metadata is set, so break out of the outer loop
                        else:
                            # Header lines in Interval files are optional. For example, BED is Interval but has no header.
                            # We'll make a best guess at the location of the metadata columns.
                            elems = line.split("\t")
                            if len(elems) > 2:
                                if overwrite or not dataset.metadata.element_is_set("chromCol"):
                                    dataset.metadata.chromCol = 1
                                try:
                                    int(elems[1])
                                    if overwrite or not dataset.metadata.element_is_set("startCol"):
                                        dataset.metadata.startCol = 2
                                except Exception:
                                    pass  # Metadata default will be used
                                try:
                                    int(elems[2])
                                    if overwrite or not dataset.metadata.element_is_set("endCol"):
                                        dataset.metadata.endCol = 3
                                except Exception:
                                    pass  # Metadata default will be used
                                # we no longer want to guess that this column is the 'name', name must now be set manually for interval files
                                # we will still guess at the strand, as we can make a more educated guess
                                # if len( elems ) > 3:
                                #    try:
                                #        int( elems[3] )
                                #    except Exception:
                                #        if overwrite or not dataset.metadata.element_is_set( 'nameCol' ):
                                #            dataset.metadata.nameCol = 4
                                if len(elems) < 6 or elems[5] not in data.valid_strand:
                                    if overwrite or not dataset.metadata.element_is_set("strandCol"):
                                        dataset.metadata.strandCol = 0
                                else:
                                    if overwrite or not dataset.metadata.element_is_set("strandCol"):
                                        dataset.metadata.strandCol = 6
                                break
                            if (i - empty_line_count) > num_check_lines:
                                break  # Our metadata is set or we examined 100 non-empty lines, so break out of the outer loop
                    else:
                        empty_line_count += 1

    def displayable(self, dataset: DatasetProtocol) -> bool:
        try:
            return (
                not dataset.dataset.purged
                and dataset.has_data()
                and dataset.state == dataset.states.OK
                and dataset.metadata.columns > 0
                and dataset.metadata.data_lines != 0
                and dataset.metadata.chromCol
                and dataset.metadata.startCol
                and dataset.metadata.endCol
            )
        except Exception:
            return False

    def get_estimated_display_viewport(
        self,
        dataset: DatasetProtocol,
        chrom_col: Optional[int] = None,
        start_col: Optional[int] = None,
        end_col: Optional[int] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Return a chrom, start, stop tuple for viewing a file."""
        viewport_feature_count = 100  # viewport should check at least 100 features; excludes comment lines
        max_line_count = max(viewport_feature_count, 500)  # maximum number of lines to check; includes comment lines
        if not self.displayable(dataset):
            return (None, None, None)
        try:
            # If column indexes were not passwed, determine from metadata
            if chrom_col is None:
                chrom_col = int(dataset.metadata.chromCol) - 1
            if start_col is None:
                start_col = int(dataset.metadata.startCol) - 1
            if end_col is None:
                end_col = int(dataset.metadata.endCol) - 1
            # Scan lines of file to find a reasonable chromosome and range
            chrom = None
            start = sys.maxsize
            end = 0
            max_col = max(chrom_col, start_col, end_col)
            with compression_utils.get_fileobj(dataset.file_name) as fh:
                for line in util.iter_start_of_line(fh, VIEWPORT_READLINE_BUFFER_SIZE):
                    # Skip comment lines
                    if not line.startswith("#"):
                        try:
                            fields = line.rstrip().split("\t")
                            if len(fields) > max_col:
                                if chrom is None or chrom == fields[chrom_col]:
                                    start = min(start, int(fields[start_col]))
                                    end = max(end, int(fields[end_col]))
                                    # Set chrom last, in case start and end are not integers
                                    chrom = fields[chrom_col]
                                viewport_feature_count -= 1
                        except Exception:
                            # Most likely a non-integer field has been encountered
                            # for start / stop. Just ignore and make sure we finish
                            # reading the line and decrementing the counters.
                            pass
                    # Make sure we are at the next new line
                    readline_count = VIEWPORT_MAX_READS_PER_LINE
                    while line.rstrip("\n\r") == line:
                        assert readline_count > 0, Exception(
                            f"Viewport readline count exceeded for dataset {dataset.id}."
                        )
                        line = fh.readline(VIEWPORT_READLINE_BUFFER_SIZE)
                        if not line:
                            break  # EOF
                        readline_count -= 1
                    max_line_count -= 1
                    if not viewport_feature_count or not max_line_count:
                        # exceeded viewport or total line count to check
                        break
            if chrom is not None:
                return (chrom, str(start), str(end))  # Necessary to return strings?
        except Exception:
            # Unexpected error, possibly missing metadata
            log.exception("Exception caught attempting to generate viewport for dataset '%d'", dataset.id)
        return (None, None, None)

    def as_ucsc_display_file(self, dataset: DatasetProtocol, **kwd) -> Union[FileObjType, str]:
        """Returns file contents with only the bed data"""
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as fh:
            c, s, e, t, n = (
                dataset.metadata.chromCol,
                dataset.metadata.startCol,
                dataset.metadata.endCol,
                dataset.metadata.strandCol or 0,
                dataset.metadata.nameCol or 0,
            )
            c, s, e, t, n = int(c) - 1, int(s) - 1, int(e) - 1, int(t) - 1, int(n) - 1
            if t >= 0:  # strand column (should) exists
                for i, elems in enumerate(compression_utils.file_iter(dataset.file_name)):
                    strand = "+"
                    name = "region_%i" % i
                    if n >= 0 and n < len(elems):
                        name = cast(str, elems[n])
                    if t < len(elems):
                        strand = cast(str, elems[t])
                    tmp = [elems[c], elems[s], elems[e], name, "0", strand]
                    fh.write("%s\n" % "\t".join(tmp))
            elif n >= 0:  # name column (should) exists
                for i, elems in enumerate(compression_utils.file_iter(dataset.file_name)):
                    name = "region_%i" % i
                    if n >= 0 and n < len(elems):
                        name = cast(str, elems[n])
                    tmp = [elems[c], elems[s], elems[e], name]
                    fh.write("%s\n" % "\t".join(tmp))
            else:
                for elems in compression_utils.file_iter(dataset.file_name):
                    tmp = [elems[c], elems[s], elems[e]]
                    fh.write("%s\n" % "\t".join(tmp))
            return compression_utils.get_fileobj(fh.name, mode="rb")

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(
            dataset,
            column_parameter_alias={
                "chromCol": "Chrom",
                "startCol": "Start",
                "endCol": "End",
                "strandCol": "Strand",
                "nameCol": "Name",
            },
        )

    def ucsc_links(self, dataset: DatasetProtocol, type: str, app, base_url: str) -> List:
        """
        Generate links to UCSC genome browser sites based on the dbkey
        and content of dataset.
        """
        # Filter UCSC sites to only those that are supported by this build and
        # enabled.
        valid_sites = [
            (name, url)
            for name, url in app.datatypes_registry.get_legacy_sites_by_build("ucsc", dataset.dbkey)
            if name in app.datatypes_registry.get_display_sites("ucsc")
        ]
        if not valid_sites:
            return []
        # If there are any valid sites, we need to generate the estimated
        # viewport
        chrom, start, stop = self.get_estimated_display_viewport(dataset)
        if chrom is None:
            return []
        # Accumulate links for valid sites
        ret_val = []
        for site_name, site_url in valid_sites:
            internal_url = app.url_for(
                controller="dataset", dataset_id=dataset.id, action="display_at", filename="ucsc_" + site_name
            )
            display_url = quote_plus(
                "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at"
                % (base_url, app.url_for(controller="root"), dataset.id, type)
            )
            redirect_url = quote_plus(f"{site_url}db={dataset.dbkey}&position={chrom}:{start}-{stop}&hgt.customText=%s")
            link = f"{internal_url}?redirect_url={redirect_url}&display_url={display_url}"
            ret_val.append((site_name, link))
        return ret_val

    def validate(self, dataset: DatasetProtocol, **kwd) -> DatatypeValidation:
        """Validate an interval file using the bx GenomicIntervalReader"""
        c, s, e, t = (
            dataset.metadata.chromCol,
            dataset.metadata.startCol,
            dataset.metadata.endCol,
            dataset.metadata.strandCol,
        )
        c, s, e, t = int(c) - 1, int(s) - 1, int(e) - 1, int(t) - 1
        with compression_utils.get_fileobj(dataset.file_name, "r") as infile:
            reader = GenomicIntervalReader(infile, chrom_col=c, start_col=s, end_col=e, strand_col=t)

            while True:
                try:
                    next(reader)
                except ParseError as e:
                    return DatatypeValidation.invalid(util.unicodify(e))
                except StopIteration:
                    return DatatypeValidation.validated()

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Checks for 'intervalness'

        This format is mostly used by galaxy itself.  Valid interval files should include
        a valid header comment, but this seems to be loosely regulated.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'test_space.txt' )
        >>> Interval().sniff( fname )
        False
        >>> fname = get_test_fname( 'interval.interval' )
        >>> Interval().sniff( fname )
        True
        """
        found_valid_lines = False
        try:
            headers = iter_headers(file_prefix, "\t", comment_designator="#")
            # If we got here, we already know the file is_column_based and is not bed,
            # so we'll just look for some valid data.
            for hdr in headers:
                if hdr:
                    if len(hdr) < 3:
                        return False
                    # Assume chrom start and end are in column positions 1 and 2
                    # respectively ( for 0 based columns )
                    int(hdr[1])
                    int(hdr[2])
                    found_valid_lines = True
        except Exception:
            return False
        return found_valid_lines

    # ------------- Dataproviders
    @dataproviders.decorators.dataprovider_factory("genomic-region", GenomicRegionDataProvider.settings)
    def genomic_region_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        return GenomicRegionDataProvider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("genomic-region-dict", GenomicRegionDataProvider.settings)
    def genomic_region_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        settings["named_columns"] = True
        return self.genomic_region_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("interval", IntervalDataProvider.settings)
    def interval_dataprovider(self, dataset: DatasetProtocol, **settings) -> IntervalDataProvider:
        return IntervalDataProvider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("interval-dict", IntervalDataProvider.settings)
    def interval_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> IntervalDataProvider:
        settings["named_columns"] = True
        return self.interval_dataprovider(dataset, **settings)


class BedGraph(Interval):
    """Tab delimited chrom/start/end/datavalue dataset"""

    edam_format = "format_3583"
    file_ext = "bedgraph"
    track_type = "LineTrack"
    data_sources = {"data": "bigwig", "index": "bigwig"}

    def as_ucsc_display_file(self, dataset: DatasetProtocol, **kwd) -> Union[FileObjType, str]:
        """
        Returns file contents as is with no modifications.
        TODO: this is a functional stub and will need to be enhanced moving forward to provide additional support for bedgraph.
        """
        return open(dataset.file_name, "rb")

    def get_estimated_display_viewport(
        self,
        dataset: DatasetProtocol,
        chrom_col: Optional[int] = 0,
        start_col: Optional[int] = 1,
        end_col: Optional[int] = 2,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Set viewport based on dataset's first 100 lines.
        """
        return Interval.get_estimated_display_viewport(
            self, dataset, chrom_col=chrom_col, start_col=start_col, end_col=end_col
        )


class Bed(Interval):
    """Tab delimited data in BED format"""

    edam_format = "format_3003"
    file_ext = "bed"
    data_sources = {"data": "tabix", "index": "bigwig", "feature_search": "fli"}
    track_type = Interval.track_type
    check_required_metadata = True

    column_names = [
        "Chrom",
        "Start",
        "End",
        "Name",
        "Score",
        "Strand",
        "ThickStart",
        "ThickEnd",
        "ItemRGB",
        "BlockCount",
        "BlockSizes",
        "BlockStarts",
    ]

    MetadataElement(name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter)
    MetadataElement(name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter)
    MetadataElement(name="endCol", default=3, desc="End column", param=metadata.ColumnParameter)
    MetadataElement(
        name="strandCol",
        default=0,
        desc="Strand column (click box & select)",
        param=metadata.ColumnParameter,
        optional=True,
        no_value=0,
    )
    MetadataElement(name="columns", default=3, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(
        name="viz_filter_cols",
        desc="Score column for visualization",
        default=[4],
        param=metadata.ColumnParameter,
        optional=True,
        multiple=True,
    )
    # do we need to repeat these? they are the same as should be inherited from interval type

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """Sets the metadata information for datasets previously determined to be in bed format."""
        if dataset.has_data():
            i = 0
            for i, line in enumerate(open(dataset.file_name)):  # noqa: B007
                line = line.rstrip("\r\n")
                if line and not line.startswith("#"):
                    elems = line.split("\t")
                    if len(elems) > 2:
                        if len(elems) > 3:
                            if overwrite or not dataset.metadata.element_is_set("nameCol"):
                                dataset.metadata.nameCol = 4
                        if len(elems) < 6:
                            if overwrite or not dataset.metadata.element_is_set("strandCol"):
                                dataset.metadata.strandCol = 0
                        else:
                            if overwrite or not dataset.metadata.element_is_set("strandCol"):
                                dataset.metadata.strandCol = 6
                        break
            Tabular.set_meta(self, dataset, overwrite=overwrite, skip=i)

    def as_ucsc_display_file(self, dataset: DatasetProtocol, **kwd) -> Union[FileObjType, str]:
        """Returns file contents with only the bed data. If bed 6+, treat as interval."""
        for line in open(dataset.file_name):
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            fields = line.split("\t")
            """check to see if this file doesn't conform to strict genome browser accepted bed"""
            try:
                if len(fields) > 12:
                    return Interval.as_ucsc_display_file(self, dataset)  # too many fields
                if len(fields) > 6:
                    int(fields[6])
                    if len(fields) > 7:
                        int(fields[7])
                        if len(fields) > 8:
                            if int(fields[8]) != 0:
                                return Interval.as_ucsc_display_file(self, dataset)
                            if len(fields) > 9:
                                int(fields[9])
                                if len(fields) > 10:
                                    fields2 = (
                                        fields[10].rstrip(",").split(",")
                                    )  # remove trailing comma and split on comma
                                    for field in fields2:
                                        int(field)
                                    if len(fields) > 11:
                                        fields2 = (
                                            fields[11].rstrip(",").split(",")
                                        )  # remove trailing comma and split on comma
                                        for field in fields2:
                                            int(field)
            except Exception:
                return Interval.as_ucsc_display_file(self, dataset)
            # only check first line for proper form
            break

        try:
            return open(dataset.file_name, "rb")
        except Exception:
            return "This item contains no content"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Checks for 'bedness'

        BED lines have three required fields and nine additional optional fields.
        The number of fields per line must be consistent throughout any single set of data in
        an annotation track.  The order of the optional fields is binding: lower-numbered
        fields must always be populated if higher-numbered fields are used.  The data type of
        all 12 columns is:
        1-str, 2-int, 3-int, 4-str, 5-int, 6-str, 7-int, 8-int, 9-int or list, 10-int, 11-list, 12-list

        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format1

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'test_tab.bed' )
        >>> Bed().sniff( fname )
        True
        >>> fname = get_test_fname( 'interv1.bed' )
        >>> Bed().sniff( fname )
        True
        >>> fname = get_test_fname( 'complete.bed' )
        >>> Bed().sniff( fname )
        True
        """
        if not get_headers(file_prefix, "\t", comment_designator="#", count=1):
            return False
        try:
            found_valid_lines = False
            for hdr in iter_headers(file_prefix, "\t", comment_designator="#"):
                if not hdr or hdr == [""]:
                    continue
                if len(hdr) < 3 or len(hdr) > 12:
                    return False
                try:
                    int(hdr[1])
                    int(hdr[2])
                except Exception:
                    return False
                if len(hdr) > 4:
                    # hdr[3] is a string, 'name', which defines the name of the BED line - difficult to test for this.
                    # hdr[4] is an int, 'score', a score between 0 and 1000.
                    try:
                        if int(hdr[4]) < 0 or int(hdr[4]) > 1000:
                            return False
                    except Exception:
                        return False
                if len(hdr) > 5:
                    # hdr[5] is strand
                    if hdr[5] not in data.valid_strand:
                        return False
                if len(hdr) > 6:
                    # hdr[6] is thickStart, the starting position at which the feature is drawn thickly.
                    try:
                        int(hdr[6])
                    except Exception:
                        return False
                if len(hdr) > 7:
                    # hdr[7] is thickEnd, the ending position at which the feature is drawn thickly
                    try:
                        int(hdr[7])
                    except Exception:
                        return False
                if len(hdr) > 8:
                    # hdr[8] is itemRgb, an RGB value of the form R,G,B (e.g. 255,0,0).  However, this could also be an int (e.g., 0)
                    try:
                        int(hdr[8])
                    except Exception:
                        try:
                            hdr[8].split(",")
                        except Exception:
                            return False
                if len(hdr) > 9:
                    # hdr[9] is blockCount, the number of blocks (exons) in the BED line.
                    try:
                        block_count = int(hdr[9])
                    except Exception:
                        return False
                if len(hdr) > 10:
                    # hdr[10] is blockSizes - A comma-separated list of the block sizes.
                    # Sometimes the blosck_sizes and block_starts lists end in extra commas
                    try:
                        block_sizes = hdr[10].rstrip(",").split(",")
                    except Exception:
                        return False
                if len(hdr) > 11:
                    # hdr[11] is blockStarts - A comma-separated list of block starts.
                    try:
                        block_starts = hdr[11].rstrip(",").split(",")
                    except Exception:
                        return False
                    if len(block_sizes) != block_count or len(block_starts) != block_count:
                        return False
                found_valid_lines = True
            return found_valid_lines
        except Exception:
            return False


class ProBed(Bed):
    """Tab delimited data in proBED format - adaptation of BED for proteomics data."""

    edam_format = "format_3827"
    file_ext = "probed"
    column_names = [
        "Chrom",
        "Start",
        "End",
        "Name",
        "Score",
        "Strand",
        "ThickStart",
        "ThickEnd",
        "ItemRGB",
        "BlockCount",
        "BlockSizes",
        "BlockStarts",
        "ProteinAccession",
        "PeptideSequence",
        "Uniqueness",
        "GenomeReferenceVersion",
        "PsmScore",
        "Fdr",
        "Modifications",
        "Charge",
        "ExpMassToCharge",
        "CalcMassToCharge",
        "PsmRank",
        "DatasetID",
        "Uri",
    ]


class BedStrict(Bed):
    """Tab delimited data in strict BED format - no non-standard columns allowed"""

    edam_format = "format_3584"
    file_ext = "bedstrict"

    # no user change of datatype allowed
    allow_datatype_change = False

    # Read only metadata elements
    MetadataElement(name="chromCol", default=1, desc="Chrom column", readonly=True, param=metadata.MetadataParameter)
    MetadataElement(
        name="startCol", default=2, desc="Start column", readonly=True, param=metadata.MetadataParameter
    )  # TODO: start and end should be able to be set to these or the proper thick[start/end]?
    MetadataElement(name="endCol", default=3, desc="End column", readonly=True, param=metadata.MetadataParameter)
    MetadataElement(
        name="strandCol",
        default=0,
        desc="Strand column (click box & select)",
        readonly=True,
        param=metadata.MetadataParameter,
        no_value=0,
        optional=True,
    )
    MetadataElement(
        name="nameCol",
        desc="Name/Identifier column (click box & select)",
        readonly=True,
        param=metadata.MetadataParameter,
        no_value=0,
        optional=True,
    )
    MetadataElement(name="columns", default=3, desc="Number of columns", readonly=True, visible=False)

    def __init__(self, **kwd):
        Tabular.__init__(self, **kwd)
        self.clear_display_apps()  # only new style display applications for this datatype

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        Tabular.set_meta(self, dataset, overwrite=overwrite, **kwd)  # need column count first
        if dataset.metadata.columns >= 4:
            dataset.metadata.nameCol = 4
            if dataset.metadata.columns >= 6:
                dataset.metadata.strandCol = 6

    def sniff(self, filename: str) -> bool:
        return False  # NOTE: This would require aggressively validating the entire file


class Bed6(BedStrict):
    """Tab delimited data in strict BED format - no non-standard columns allowed; column count forced to 6"""

    edam_format = "format_3585"
    file_ext = "bed6"


class Bed12(BedStrict):
    """Tab delimited data in strict BED format - no non-standard columns allowed; column count forced to 12"""

    edam_format = "format_3586"
    file_ext = "bed12"


class _RemoteCallMixin:
    def _get_remote_call_url(
        self, redirect_url: str, site_name: str, dataset: HasId, type: str, app, base_url: str
    ) -> str:
        """Retrieve the URL to call out to an external site and retrieve data.
        This routes our external URL through a local galaxy instance which makes
        the data available, followed by redirecting to the remote site with a
        link back to the available information.
        """
        internal_url = f"{app.url_for(controller='dataset', dataset_id=dataset.id, action='display_at', filename=f'{type}_{site_name}')}"
        base_url = app.config.get("display_at_callback", base_url)
        display_url = quote_plus(
            "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at"
            % (base_url, app.url_for(controller="root"), dataset.id, type)
        )
        link = f"{internal_url}?redirect_url={redirect_url}&display_url={display_url}"
        return link


@dataproviders.decorators.has_dataproviders
@build_sniff_from_prefix
class Gff(Tabular, _RemoteCallMixin):
    """Tab delimited data in Gff format"""

    edam_data = "data_1255"
    edam_format = "format_2305"
    file_ext = "gff"
    valid_gff_frame = [".", "0", "1", "2"]
    column_names = ["Seqname", "Source", "Feature", "Start", "End", "Score", "Strand", "Frame", "Group"]
    data_sources = {"data": "interval_index", "index": "bigwig", "feature_search": "fli"}
    track_type = Interval.track_type

    MetadataElement(name="columns", default=9, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(
        name="column_types",
        default=["str", "str", "str", "int", "int", "int", "str", "str", "str"],
        param=metadata.ColumnTypesParameter,
        desc="Column types",
        readonly=True,
        visible=False,
    )

    MetadataElement(name="attributes", default=0, desc="Number of attributes", readonly=True, visible=False, no_value=0)
    MetadataElement(
        name="attribute_types",
        default={},
        desc="Attribute types",
        param=metadata.DictParameter,
        readonly=True,
        visible=False,
        no_value=[],
    )

    def __init__(self, **kwd):
        """Initialize datatype, by adding GBrowse display app"""
        Tabular.__init__(self, **kwd)
        self.add_display_app("ucsc", "display at UCSC", "as_ucsc_display_file", "ucsc_links")
        self.add_display_app("gbrowse", "display in Gbrowse", "as_gbrowse_display_file", "gbrowse_links")

    def set_attribute_metadata(self, dataset: DatasetProtocol) -> None:
        """
        Sets metadata elements for dataset's attributes.
        """

        # Use first N lines to set metadata for dataset attributes. Attributes
        # not found in the first N lines will not have metadata.
        num_lines = 200
        attribute_types = {}
        with compression_utils.get_fileobj(dataset.file_name) as in_fh:
            for i, line in enumerate(in_fh):
                if line and not line.startswith("#"):
                    elems = line.split("\t")
                    if len(elems) == 9:
                        try:
                            # Loop through attributes to set types.
                            for name, value in parse_gff_attributes(elems[8]).items():
                                # Default type is string.
                                value_type = "str"
                                try:
                                    # Try int.
                                    int(value)
                                    value_type = "int"
                                except ValueError:
                                    try:
                                        # Try float.
                                        float(value)
                                        value_type = "float"
                                    except ValueError:
                                        pass
                                attribute_types[name] = value_type
                        except Exception:
                            pass
                    if i + 1 == num_lines:
                        break

        # Set attribute metadata and then set additional metadata.
        dataset.metadata.attribute_types = attribute_types
        dataset.metadata.attributes = len(attribute_types)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        self.set_attribute_metadata(dataset)

        i = 0
        with compression_utils.get_fileobj(dataset.file_name) as in_fh:
            for i, line in enumerate(in_fh):  # noqa: B007
                line = line.rstrip("\r\n")
                if line and not line.startswith("#"):
                    elems = line.split("\t")
                    if len(elems) == 9:
                        try:
                            int(elems[3])
                            int(elems[4])
                            break
                        except Exception:
                            pass
        Tabular.set_meta(self, dataset, overwrite=overwrite, skip=i)

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)

    def get_estimated_display_viewport(
        self, dataset: DatasetProtocol
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Return a chrom, start, stop tuple for viewing a file.  There are slight differences between gff 2 and gff 3
        formats.  This function should correctly handle both...
        """
        viewport_feature_count = 100  # viewport should check at least 100 features; excludes comment lines
        max_line_count = max(viewport_feature_count, 500)  # maximum number of lines to check; includes comment lines
        if self.displayable(dataset):
            try:
                seqid = None
                start = sys.maxsize
                stop = 0
                with compression_utils.get_fileobj(dataset.file_name) as fh:
                    for line in util.iter_start_of_line(fh, VIEWPORT_READLINE_BUFFER_SIZE):
                        try:
                            if line.startswith("##sequence-region"):  # ##sequence-region IV 6000000 6030000
                                elems = line.rstrip("\n\r").split()
                                if len(elems) > 3:
                                    # line looks like:
                                    # sequence-region   ctg123 1 1497228
                                    seqid = elems[1]  # IV
                                    start = int(elems[2])  # 6000000
                                    stop = int(elems[3])  # 6030000
                                    break  # use location declared in file
                                elif len(elems) == 2 and elems[1].find("..") > 0:
                                    # line looks like this:
                                    # sequence-region X:120000..140000
                                    elems = elems[1].split(":")
                                    seqid = elems[0]
                                    start = int(elems[1].split("..")[0])
                                    stop = int(elems[1].split("..")[1])
                                    break  # use location declared in file
                                else:
                                    log.debug(f"line ({line}) uses an unsupported ##sequence-region definition.")
                                    # break #no break, if bad definition, we try another line
                            elif line.startswith("browser position"):
                                # Allow UCSC style browser and track info in the GFF file
                                pos_info = line.split()[-1]
                                seqid, startend = pos_info.split(":")
                                start, stop = map(int, startend.split("-"))
                                break  # use location declared in file
                            elif not line.startswith(("#", "track", "browser")):
                                viewport_feature_count -= 1
                                elems = line.rstrip("\n\r").split("\t")
                                if len(elems) > 3:
                                    if not seqid:
                                        # We can only set the viewport for a single chromosome
                                        seqid = elems[0]
                                    if seqid == elems[0]:
                                        # Make sure we have not spanned chromosomes
                                        start = min(start, int(elems[3]))
                                        stop = max(stop, int(elems[4]))
                        except Exception:
                            # most likely start/stop is not an int or not enough fields
                            pass
                        # make sure we are at the next new line
                        readline_count = VIEWPORT_MAX_READS_PER_LINE
                        while line.rstrip("\n\r") == line:
                            assert readline_count > 0, Exception(
                                f"Viewport readline count exceeded for dataset {dataset.id}."
                            )
                            line = fh.readline(VIEWPORT_READLINE_BUFFER_SIZE)
                            if not line:
                                break  # EOF
                            readline_count -= 1
                        max_line_count -= 1
                        if not viewport_feature_count or not max_line_count:
                            # exceeded viewport or total line count to check
                            break
                    if seqid is not None:
                        return (seqid, str(start), str(stop))  # Necessary to return strings?
            except Exception:
                log.exception("Unexpected error")
        return (None, None, None)  # could not determine viewport

    def ucsc_links(self, dataset: DatasetProtocol, type: str, app, base_url: str) -> List:
        ret_val = []
        seqid, start, stop = self.get_estimated_display_viewport(dataset)
        if seqid is not None:
            for site_name, site_url in app.datatypes_registry.get_legacy_sites_by_build("ucsc", dataset.dbkey):
                if site_name in app.datatypes_registry.get_display_sites("ucsc"):
                    redirect_url = quote_plus(
                        f"{site_url}db={dataset.dbkey}&position={seqid}:{start}-{stop}&hgt.customText=%s"
                    )
                    link = self._get_remote_call_url(redirect_url, site_name, dataset, type, app, base_url)
                    ret_val.append((site_name, link))
        return ret_val

    def gbrowse_links(self, dataset: DatasetProtocol, type: str, app, base_url: str) -> List:
        ret_val = []
        seqid, start, stop = self.get_estimated_display_viewport(dataset)
        if seqid is not None:
            for site_name, site_url in app.datatypes_registry.get_legacy_sites_by_build("gbrowse", dataset.dbkey):
                if site_name in app.datatypes_registry.get_display_sites("gbrowse"):
                    if seqid.startswith("chr") and len(seqid) > 3:
                        seqid = seqid[3:]
                    redirect_url = quote_plus(f"{site_url}/?q={seqid}:{start}..{stop}&eurl=%s")
                    link = self._get_remote_call_url(redirect_url, site_name, dataset, type, app, base_url)
                    ret_val.append((site_name, link))
        return ret_val

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in gff format

        GFF lines have nine required fields that must be tab-separated.

        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format3

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('gff.gff3')
        >>> Gff().sniff( fname )
        False
        >>> fname = get_test_fname('test.gff')
        >>> Gff().sniff( fname )
        True
        """
        if len(get_headers(file_prefix, "\t", count=2)) < 2:
            return False
        try:
            found_valid_lines = False
            for hdr in iter_headers(file_prefix, "\t"):
                if not hdr or hdr == [""]:
                    continue
                hdr0_parts = hdr[0].split()
                if hdr0_parts[0] == "##gff-version":
                    return hdr0_parts[1].startswith("2")
                # The gff-version header comment may have been stripped, so inspect the data
                if hdr[0].startswith("#"):
                    continue
                if len(hdr) != 9:
                    return False
                try:
                    int(hdr[3])
                    int(hdr[4])
                except Exception:
                    return False
                if hdr[5] != ".":
                    try:
                        float(hdr[5])
                    except Exception:
                        return False
                if hdr[6] not in data.valid_strand:
                    return False
                if hdr[7] not in self.valid_gff_frame:
                    return False
                found_valid_lines = True
            return found_valid_lines
        except Exception:
            return False

    # ------------- Dataproviders
    # redefine bc super is Tabular
    @dataproviders.decorators.dataprovider_factory("genomic-region", GenomicRegionDataProvider.settings)
    def genomic_region_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        return GenomicRegionDataProvider(dataset, 0, 3, 4, **settings)

    @dataproviders.decorators.dataprovider_factory("genomic-region-dict", GenomicRegionDataProvider.settings)
    def genomic_region_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> GenomicRegionDataProvider:
        settings["named_columns"] = True
        return self.genomic_region_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory("interval", IntervalDataProvider.settings)
    def interval_dataprovider(self, dataset: DatasetProtocol, **settings):
        return IntervalDataProvider(dataset, 0, 3, 4, 6, 2, **settings)

    @dataproviders.decorators.dataprovider_factory("interval-dict", IntervalDataProvider.settings)
    def interval_dict_dataprovider(self, dataset: DatasetProtocol, **settings):
        settings["named_columns"] = True
        return self.interval_dataprovider(dataset, **settings)


class Gff3(Gff):
    """Tab delimited data in Gff3 format"""

    edam_format = "format_1975"
    file_ext = "gff3"
    valid_gff3_strand = ["+", "-", ".", "?"]
    valid_gff3_phase = Gff.valid_gff_frame
    column_names = ["Seqid", "Source", "Type", "Start", "End", "Score", "Strand", "Phase", "Attributes"]
    track_type = Interval.track_type

    MetadataElement(
        name="column_types",
        default=["str", "str", "str", "int", "int", "float", "str", "int", "list"],
        param=metadata.ColumnTypesParameter,
        desc="Column types",
        readonly=True,
        visible=False,
    )

    def __init__(self, **kwd):
        """Initialize datatype, by adding GBrowse display app"""
        Gff.__init__(self, **kwd)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        self.set_attribute_metadata(dataset)
        i = 0
        with compression_utils.get_fileobj(dataset.file_name) as in_fh:
            for i, line in enumerate(in_fh):  # noqa: B007
                line = line.rstrip("\r\n")
                if line and not line.startswith("#"):
                    elems = line.split("\t")
                    valid_start = False
                    valid_end = False
                    if len(elems) == 9:
                        try:
                            start = int(elems[3])
                            valid_start = True
                        except Exception:
                            if elems[3] == ".":
                                valid_start = True
                        try:
                            end = int(elems[4])
                            valid_end = True
                        except Exception:
                            if elems[4] == ".":
                                valid_end = True
                        strand = elems[6]
                        phase = elems[7]
                        if (
                            valid_start
                            and valid_end
                            and start < end
                            and strand in self.valid_gff3_strand
                            and phase in self.valid_gff3_phase
                        ):
                            break
        Tabular.set_meta(self, dataset, overwrite=overwrite, skip=i)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in GFF version 3 format

        GFF 3 format:

        1) adds a mechanism for representing more than one level
           of hierarchical grouping of features and subfeatures.
        2) separates the ideas of group membership and feature name/id
        3) constrains the feature type field to be taken from a controlled
           vocabulary.
        4) allows a single feature, such as an exon, to belong to more than
           one group at a time.
        5) provides an explicit convention for pairwise alignments
        6) provides an explicit convention for features that occupy disjunct regions

        The format consists of 9 columns, separated by tabs (NOT spaces).

        Undefined fields are replaced with the "." character, as described in the original GFF spec.

        For complete details see http://song.sourceforge.net/gff3.shtml

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'test.gff' )
        >>> Gff3().sniff( fname )
        False
        >>> fname = get_test_fname( 'test.gtf' )
        >>> Gff3().sniff( fname )
        False
        >>> fname = get_test_fname('gff.gff3')
        >>> Gff3().sniff( fname )
        True
        >>> fname = get_test_fname( 'grch37.75.gtf' )
        >>> Gff3().sniff( fname )
        False
        """
        if len(get_headers(file_prefix, "\t", count=2)) < 2:
            return False
        try:
            found_valid_lines = False
            for hdr in iter_headers(file_prefix, "\t"):
                if not hdr or hdr == [""]:
                    continue
                hdr0_parts = hdr[0].split()
                if hdr0_parts[0] == "##gff-version":
                    return hdr0_parts[1].startswith("3")
                # The gff-version header comment may have been stripped, so inspect the data
                if hdr[0].startswith("#"):
                    continue
                if len(hdr) != 9:
                    return False
                try:
                    int(hdr[3])
                except Exception:
                    if hdr[3] != ".":
                        return False
                try:
                    int(hdr[4])
                except Exception:
                    if hdr[4] != ".":
                        return False
                if hdr[5] != ".":
                    try:
                        float(hdr[5])
                    except Exception:
                        return False
                if hdr[6] not in self.valid_gff3_strand:
                    return False
                if hdr[7] not in self.valid_gff3_phase:
                    return False
                parse_gff3_attributes(hdr[8])
                found_valid_lines = True
            return found_valid_lines
        except Exception:
            return False


class Gtf(Gff):
    """Tab delimited data in Gtf format"""

    edam_format = "format_2306"
    file_ext = "gtf"
    column_names = ["Seqname", "Source", "Feature", "Start", "End", "Score", "Strand", "Frame", "Attributes"]
    track_type = Interval.track_type

    MetadataElement(name="columns", default=9, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(
        name="column_types",
        default=["str", "str", "str", "int", "int", "float", "str", "int", "list"],
        param=metadata.ColumnTypesParameter,
        desc="Column types",
        readonly=True,
        visible=False,
    )

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in gtf format

        GTF lines have nine required fields that must be tab-separated. The first eight GTF fields are the same as GFF.
        The group field has been expanded into a list of attributes. Each attribute consists of a type/value pair.
        Attributes must end in a semi-colon, and be separated from any following attribute by exactly one space.
        The attribute list must begin with the two mandatory attributes:

            gene_id value - A globally unique identifier for the genomic source of the sequence.
            transcript_id value - A globally unique identifier for the predicted transcript.

        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format4

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( '1.bed' )
        >>> Gtf().sniff( fname )
        False
        >>> fname = get_test_fname( 'test.gff' )
        >>> Gtf().sniff( fname )
        False
        >>> fname = get_test_fname( 'test.gtf' )
        >>> Gtf().sniff( fname )
        True
        >>> fname = get_test_fname( 'grch37.75.gtf' )
        >>> Gtf().sniff( fname )
        True
        """
        if len(get_headers(file_prefix, "\t", count=2)) < 2:
            return False
        try:
            found_valid_lines = False
            for hdr in iter_headers(file_prefix, "\t"):
                if not hdr or hdr == [""]:
                    continue
                hdr0_parts = hdr[0].split()
                if hdr0_parts[0] == "##gff-version" and not hdr0_parts[1].startswith("2"):
                    return False
                # The gff-version header comment may have been stripped, so inspect the data
                if hdr[0].startswith("#"):
                    continue
                if len(hdr) != 9:
                    return False
                try:
                    int(hdr[3])
                    int(hdr[4])
                except Exception:
                    return False
                if hdr[5] != ".":
                    try:
                        float(hdr[5])
                    except Exception:
                        return False
                if hdr[6] not in data.valid_strand:
                    return False
                if hdr[7] not in self.valid_gff_frame:
                    return False
                # Check attributes for gene_id (transcript_id is also mandatory
                # but not for genes)
                attributes = parse_gff_attributes(hdr[8])
                if "gene_id" not in attributes:
                    return False
                found_valid_lines = True
            return found_valid_lines
        except Exception:
            return False


@dataproviders.decorators.has_dataproviders
@build_sniff_from_prefix
class Wiggle(Tabular, _RemoteCallMixin):
    """Tab delimited data in wiggle format"""

    edam_format = "format_3005"
    file_ext = "wig"
    track_type = "LineTrack"
    data_sources = {"data": "bigwig", "index": "bigwig"}

    MetadataElement(name="columns", default=3, desc="Number of columns", readonly=True, visible=False)

    def __init__(self, **kwd):
        Tabular.__init__(self, **kwd)
        self.add_display_app("ucsc", "display at UCSC", "as_ucsc_display_file", "ucsc_links")
        self.add_display_app("gbrowse", "display in Gbrowse", "as_gbrowse_display_file", "gbrowse_links")

    def get_estimated_display_viewport(
        self, dataset: DatasetProtocol
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Return a chrom, start, stop tuple for viewing a file."""
        viewport_feature_count = 100  # viewport should check at least 100 features; excludes comment lines
        max_line_count = max(viewport_feature_count, 500)  # maximum number of lines to check; includes comment lines
        if self.displayable(dataset):
            try:
                chrom = None
                start = sys.maxsize
                end = 0
                span = 1
                step = None
                with open(dataset.file_name) as fh:
                    for line in util.iter_start_of_line(fh, VIEWPORT_READLINE_BUFFER_SIZE):
                        try:
                            if line.startswith("browser"):
                                chr_info = line.rstrip("\n\r").split()[-1]
                                chrom, coords = chr_info.split(":")
                                start, end = map(int, coords.split("-"))
                                break  # use the browser line
                            # variableStep chrom=chr20
                            if line and (
                                line.lower().startswith("variablestep") or line.lower().startswith("fixedstep")
                            ):
                                if chrom is not None:
                                    break  # different chrom or different section of the chrom
                                chrom = line.rstrip("\n\r").split("chrom=")[1].split()[0]
                                if "span=" in line:
                                    span = int(line.rstrip("\n\r").split("span=")[1].split()[0])
                                if "step=" in line:
                                    step = int(line.rstrip("\n\r").split("step=")[1].split()[0])
                                    start = int(line.rstrip("\n\r").split("start=")[1].split()[0])
                            else:
                                fields = line.rstrip("\n\r").split()
                                if fields:
                                    if step is not None:
                                        if not end:
                                            end = start + span
                                        else:
                                            end += step
                                    else:
                                        start = min(int(fields[0]), start)
                                        end = max(end, int(fields[0]) + span)
                                    viewport_feature_count -= 1
                        except Exception:
                            pass
                        # make sure we are at the next new line
                        readline_count = VIEWPORT_MAX_READS_PER_LINE
                        while line.rstrip("\n\r") == line:
                            assert readline_count > 0, Exception(
                                f"Viewport readline count exceeded for dataset {dataset.id}."
                            )
                            line = fh.readline(VIEWPORT_READLINE_BUFFER_SIZE)
                            if not line:
                                break  # EOF
                            readline_count -= 1
                        max_line_count -= 1
                        if not viewport_feature_count or not max_line_count:
                            # exceeded viewport or total line count to check
                            break
                if chrom is not None:
                    return (chrom, str(start), str(end))  # Necessary to return strings?
            except Exception:
                log.exception("Unexpected error")
        return (None, None, None)  # could not determine viewport

    def gbrowse_links(self, dataset: DatasetProtocol, type: str, app, base_url: str) -> List:
        ret_val = []
        chrom, start, stop = self.get_estimated_display_viewport(dataset)
        if chrom is not None:
            for site_name, site_url in app.datatypes_registry.get_legacy_sites_by_build("gbrowse", dataset.dbkey):
                if site_name in app.datatypes_registry.get_display_sites("gbrowse"):
                    if chrom.startswith("chr") and len(chrom) > 3:
                        chrom = chrom[3:]
                    redirect_url = quote_plus(f"{site_url}/?q={chrom}:{start}..{stop}&eurl=%s")
                    link = self._get_remote_call_url(redirect_url, site_name, dataset, type, app, base_url)
                    ret_val.append((site_name, link))
        return ret_val

    def ucsc_links(self, dataset: DatasetProtocol, type: str, app, base_url: str) -> List:
        ret_val = []
        chrom, start, stop = self.get_estimated_display_viewport(dataset)
        if chrom is not None:
            for site_name, site_url in app.datatypes_registry.get_legacy_sites_by_build("ucsc", dataset.dbkey):
                if site_name in app.datatypes_registry.get_display_sites("ucsc"):
                    redirect_url = quote_plus(
                        f"{site_url}db={dataset.dbkey}&position={chrom}:{start}-{stop}&hgt.customText=%s"
                    )
                    link = self._get_remote_call_url(redirect_url, site_name, dataset, type, app, base_url)
                    ret_val.append((site_name, link))
        return ret_val

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, skipchars=["track", "#"])

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        max_data_lines = None
        i = 0
        for i, line in enumerate(open(dataset.file_name)):  # noqa: B007
            line = line.rstrip("\r\n")
            if line and not line.startswith("#"):
                elems = line.split("\t")
                try:
                    # variableStep format is nucleotide position\tvalue\n,
                    # fixedStep is value\n
                    # "Wiggle track data values can be integer or real, positive or negative values"
                    float(elems[0])
                    break
                except Exception:
                    # We are either in the track definition line or in a declaration line
                    pass
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            # we'll arbitrarily only use the first 100 data lines in this wig file to calculate tabular attributes (column types)
            # this should be sufficient, except when we have mixed wig track types (bed, variable, fixed),
            #    but those cases are not a single table that would have consistant column definitions
            # optional metadata values set in Tabular class will be 'None'
            max_data_lines = 100
        Tabular.set_meta(self, dataset, overwrite=overwrite, skip=i, max_data_lines=max_data_lines)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines wether the file is in wiggle format

        The .wig format is line-oriented. Wiggle data is preceeded by a track definition line,
        which adds a number of options for controlling the default display of this track.
        Following the track definition line is the track data, which can be entered in several
        different formats.

        The track definition line begins with the word 'track' followed by the track type.
        The track type with version is REQUIRED, and it currently must be wiggle_0.  For example,
        track type=wiggle_0...

        For complete details see http://genome.ucsc.edu/goldenPath/help/wiggle.html

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'interv1.bed' )
        >>> Wiggle().sniff( fname )
        False
        >>> fname = get_test_fname( 'wiggle.wig' )
        >>> Wiggle().sniff( fname )
        True
        """
        try:
            headers = iter_headers(file_prefix, None)
            for hdr in headers:
                if len(hdr) > 1 and hdr[0] == "track" and hdr[1].startswith("type=wiggle"):
                    return True
            return False
        except Exception:
            return False

    # ------------- Dataproviders
    @dataproviders.decorators.dataprovider_factory("wiggle", WiggleDataProvider.settings)
    def wiggle_dataprovider(self, dataset: DatasetProtocol, **settings) -> WiggleDataProvider:
        dataset_source = DatasetDataProvider(dataset)
        return WiggleDataProvider(dataset_source, **settings)

    @dataproviders.decorators.dataprovider_factory("wiggle-dict", WiggleDataProvider.settings)
    def wiggle_dict_dataprovider(self, dataset: DatasetProtocol, **settings) -> WiggleDataProvider:
        dataset_source = DatasetDataProvider(dataset)
        settings["named_columns"] = True
        return WiggleDataProvider(dataset_source, **settings)


@build_sniff_from_prefix
class CustomTrack(Tabular):
    """UCSC CustomTrack"""

    edam_format = "format_3588"
    file_ext = "customtrack"

    def __init__(self, **kwd):
        """Initialize interval datatype, by adding UCSC display app"""
        Tabular.__init__(self, **kwd)
        self.add_display_app("ucsc", "display at UCSC", "as_ucsc_display_file", "ucsc_links")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        Tabular.set_meta(self, dataset, overwrite=overwrite, skip=1)

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, skipchars=["track", "#"])

    def get_estimated_display_viewport(
        self,
        dataset: DatasetProtocol,
        chrom_col: Optional[int] = None,
        start_col: Optional[int] = None,
        end_col: Optional[int] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Return a chrom, start, stop tuple for viewing a file."""
        # FIXME: only BED and WIG custom tracks are currently supported
        # As per previously existing behavior, viewport will only be over the first intervals
        max_line_count = 100  # maximum number of lines to check; includes comment lines
        variable_step_wig = False
        chrom = None
        span = 1
        if self.displayable(dataset):
            try:
                with open(dataset.file_name) as fh:
                    for line in util.iter_start_of_line(fh, VIEWPORT_READLINE_BUFFER_SIZE):
                        if not line.startswith("#"):
                            try:
                                if variable_step_wig:
                                    fields = line.rstrip().split()
                                    if len(fields) == 2:
                                        start = int(fields[0])
                                        return (chrom, str(start), str(start + span))
                                elif line and (
                                    line.lower().startswith("variablestep") or line.lower().startswith("fixedstep")
                                ):
                                    chrom = line.rstrip("\n\r").split("chrom=")[1].split()[0]
                                    if "span=" in line:
                                        span = int(line.rstrip("\n\r").split("span=")[1].split()[0])
                                    if "start=" in line:
                                        start = int(line.rstrip("\n\r").split("start=")[1].split()[0])
                                        return (chrom, str(start), str(start + span))
                                    else:
                                        variable_step_wig = True
                                else:
                                    fields = line.rstrip().split("\t")
                                    if len(fields) >= 3:
                                        chrom = fields[0]
                                        start = int(fields[1])
                                        end = int(fields[2])
                                        return (chrom, str(start), str(end))
                            except Exception:
                                # most likely a non-integer field has been encountered for start / stop
                                continue
                        # make sure we are at the next new line
                        readline_count = VIEWPORT_MAX_READS_PER_LINE
                        while line.rstrip("\n\r") == line:
                            assert readline_count > 0, Exception(
                                f"Viewport readline count exceeded for dataset {dataset.id}."
                            )
                            line = fh.readline(VIEWPORT_READLINE_BUFFER_SIZE)
                            if not line:
                                break  # EOF
                            readline_count -= 1
                        max_line_count -= 1
                        if not max_line_count:
                            # exceeded viewport or total line count to check
                            break
            except Exception:
                log.exception("Unexpected error")
        return (None, None, None)  # could not determine viewport

    def ucsc_links(self, dataset: DatasetProtocol, type: str, app, base_url: str) -> List:
        ret_val = []
        chrom, start, stop = self.get_estimated_display_viewport(dataset)
        if chrom is not None:
            for site_name, site_url in app.datatypes_registry.get_legacy_sites_by_build("ucsc", dataset.dbkey):
                if site_name in app.datatypes_registry.get_display_sites("ucsc"):
                    internal_url = f"{app.url_for(controller='dataset', dataset_id=dataset.id, action='display_at', filename='ucsc_' + site_name)}"
                    display_url = quote_plus(
                        "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at"
                        % (base_url, app.url_for(controller="root"), dataset.id, type)
                    )
                    redirect_url = quote_plus(
                        f"{site_url}db={dataset.dbkey}&position={chrom}:{start}-{stop}&hgt.customText=%s"
                    )
                    link = f"{internal_url}?redirect_url={redirect_url}&display_url={display_url}"
                    ret_val.append((site_name, link))
        return ret_val

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in customtrack format.

        CustomTrack files are built within Galaxy and are basically bed or interval files with the first line looking
        something like this.

        track name="User Track" description="User Supplied Track (from Galaxy)" color=0,0,0 visibility=1

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'complete.bed' )
        >>> CustomTrack().sniff( fname )
        False
        >>> fname = get_test_fname( 'ucsc.customtrack' )
        >>> CustomTrack().sniff( fname )
        True
        """
        headers = iter_headers(file_prefix, None)
        found_at_least_one_track = False
        first_line = True
        for hdr in headers:
            if first_line:
                first_line = False
                try:
                    if hdr[0].startswith("track"):
                        color_found = False
                        visibility_found = False
                        for elem in hdr[1:]:
                            if elem.startswith("color"):
                                color_found = True
                            if elem.startswith("visibility"):
                                visibility_found = True
                            if color_found and visibility_found:
                                break
                        if not color_found or not visibility_found:
                            return False
                    else:
                        return False
                except Exception:
                    return False
            else:
                try:
                    if hdr[0] and not hdr[0].startswith("#"):
                        if len(hdr) < 3:
                            return False
                        try:
                            int(hdr[1])
                            int(hdr[2])
                        except Exception:
                            return False
                        found_at_least_one_track = True
                except Exception:
                    return False
        return found_at_least_one_track


class ENCODEPeak(Interval):
    """
    Human ENCODE peak format. There are both broad and narrow peak formats.
    Formats are very similar; narrow peak has an additional column, though.

    Broad peak ( http://genome.ucsc.edu/FAQ/FAQformat#format13 ):
    This format is used to provide called regions of signal enrichment based
    on pooled, normalized (interpreted) data. It is a BED 6+3 format.

    Narrow peak http://genome.ucsc.edu/FAQ/FAQformat#format12 and :
    This format is used to provide called peaks of signal enrichment based on
    pooled, normalized (interpreted) data. It is a BED6+4 format.
    """

    edam_format = "format_3612"
    file_ext = "encodepeak"
    column_names = ["Chrom", "Start", "End", "Name", "Score", "Strand", "SignalValue", "pValue", "qValue", "Peak"]
    data_sources = {"data": "tabix", "index": "bigwig"}

    MetadataElement(name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter)
    MetadataElement(name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter)
    MetadataElement(name="endCol", default=3, desc="End column", param=metadata.ColumnParameter)
    MetadataElement(
        name="strandCol",
        default=0,
        desc="Strand column (click box & select)",
        param=metadata.ColumnParameter,
        optional=True,
        no_value=0,
    )
    MetadataElement(name="columns", default=3, desc="Number of columns", readonly=True, visible=False)

    def sniff(self, filename: str) -> bool:
        return False


class ChromatinInteractions(Interval):
    """
    Chromatin interactions obtained from 3C/5C/Hi-C experiments.
    """

    file_ext = "chrint"
    track_type = "DiagonalHeatmapTrack"
    data_sources = {"data": "tabix", "index": "bigwig"}
    column_names = ["Chrom1", "Start1", "End1", "Chrom2", "Start2", "End2", "Value"]

    MetadataElement(name="chrom1Col", default=1, desc="Chrom1 column", param=metadata.ColumnParameter)
    MetadataElement(name="start1Col", default=2, desc="Start1 column", param=metadata.ColumnParameter)
    MetadataElement(name="end1Col", default=3, desc="End1 column", param=metadata.ColumnParameter)
    MetadataElement(name="chrom2Col", default=4, desc="Chrom2 column", param=metadata.ColumnParameter)
    MetadataElement(name="start2Col", default=5, desc="Start2 column", param=metadata.ColumnParameter)
    MetadataElement(name="end2Col", default=6, desc="End2 column", param=metadata.ColumnParameter)
    MetadataElement(name="valueCol", default=7, desc="Value column", param=metadata.ColumnParameter)

    MetadataElement(name="columns", default=7, desc="Number of columns", readonly=True, visible=False)

    def sniff(self, filename: str) -> bool:
        return False


@build_sniff_from_prefix
class ScIdx(Tabular):
    """
    ScIdx files are 1-based and consist of strand-specific coordinate counts.
    They always have 5 columns, and the first row is the column labels:
    'chrom', 'index', 'forward', 'reverse', 'value'.
    Each line following the first consists of data:
    chromosome name (type str), peak index (type int), Forward strand peak
    count (type int), Reverse strand peak count (type int) and value (type int).
    The value of the 5th 'value' column is the sum of the forward and reverse
    peak count values.

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('cntrl_hg19.scidx')
    >>> ScIdx().sniff(fname)
    True
    >>> Bed().sniff(fname)
    False
    >>> fname = get_test_fname('empty.txt')
    >>> ScIdx().sniff(fname)
    False
    """

    file_ext = "scidx"

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

    def __init__(self, **kwd):
        """
        Initialize scidx datatype.
        """
        Tabular.__init__(self, **kwd)
        # Don't set column names since the first
        # line of the dataset displays them.
        self.column_names = ["chrom", "index", "forward", "reverse", "value"]

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Checks for 'scidx-ness.'
        """
        count = 0
        for count, line in enumerate(iter_headers(file_prefix, "\t")):
            # The first line is always a comment like this:
            # 2015-11-23 20:18:56.51;input.bam;READ1
            if count == 0:
                if not line[0].startswith("#"):
                    return False
            # The 2nd line is always a specific header
            elif count == 1:
                if line != ["chrom", "index", "forward", "reverse", "value"]:
                    return False
            # data line columns 2:5 need to be integers and
            # the fwd and rev column need to sum to value
            else:
                if len(line) != 5:
                    return False
                if not line[1].isdigit():
                    return False
                if int(line[2]) + int(line[3]) != int(line[4]):
                    return False
                # just check one data line
                break
        # at least the comment and header are required
        if count >= 1:
            return True
        return False


class IntervalTabix(Interval):
    """
    Class describing the bgzip format (http://samtools.github.io/hts-specs/SAMv1.pdf)
    As tabix is just a bgzip sorted for chr,start,end with an index
    """

    file_ext = "interval_tabix.gz"
    edam_format = "format_3616"
    compressed = True
    compressed_format = "gzip"

    # The MetadataElements are readonly so the user cannot change them (as the index is generated only once)
    MetadataElement(name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter, readonly=True)
    MetadataElement(name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter, readonly=True)
    MetadataElement(name="endCol", default=3, desc="End column", param=metadata.ColumnParameter, readonly=True)

    # Add metadata elements
    MetadataElement(
        name="tabix_index",
        desc="Tabix Index File",
        param=metadata.FileParameter,
        file_ext="tbi",
        readonly=True,
        visible=False,
        optional=True,
    )

    # We don't want to have a good sniff as the index would be created before the metadata on columns is set.
    def sniff_prefix(self, file_prefix: FilePrefix):
        return False

    # Ideally the tabix_index would be regenerated when the metadataElements are updated
    def set_meta(
        self,
        dataset: DatasetProtocol,
        overwrite: bool = True,
        first_line_is_header: bool = False,
        metadata_tmp_files_dir: Optional[str] = None,
        **kwd,
    ) -> None:
        # We don't use the method Interval.set_meta as we don't want to guess the columns for chr start end
        Tabular.set_meta(self, dataset, overwrite=overwrite, skip=0)
        # Try to create the index for the Tabix file.
        # These metadata values are not accessible by users, always overwrite
        index_file = dataset.metadata.tabix_index
        if not index_file:
            index_file = dataset.metadata.spec["tabix_index"].param.new_file(
                dataset=dataset, metadata_tmp_files_dir=metadata_tmp_files_dir
            )

        try:
            # tabix_index columns are 0-based while in the command line it is 1-based
            pysam.tabix_index(
                dataset.file_name,
                index=index_file.file_name,
                seq_col=dataset.metadata.chromCol - 1,
                start_col=dataset.metadata.startCol - 1,
                end_col=dataset.metadata.endCol - 1,
                keep_original=True,
                force=True,
            )
        except Exception as e:
            raise Exception(f"Error setting tabix metadata: {util.unicodify(e)}")
        else:
            dataset.metadata.tabix_index = index_file


class JuicerMediumTabix(IntervalTabix):
    """
    Class describing a tabix file built from a juicer medium format:
    https://github.com/aidenlab/juicer/wiki/Pre#medium-format
    <readname> <str1> <chr1> <pos1> <frag1> <str2> <chr2> <pos2> <frag2> <mapq1> <mapq2>

    str = strand (0 for forward, anything else for reverse)
    chr = chromosome (must be a chromosome in the genome)
    pos = position
    frag = restriction site fragment
    mapq = mapping quality score
    """

    file_ext = "juicer_medium_tabix.gz"

    # The MetadataElements are readonly so the user cannot change them (as the index is generated only once)
    MetadataElement(name="chromCol", default=3, desc="Chrom column", param=metadata.ColumnParameter, readonly=True)
    MetadataElement(name="startCol", default=4, desc="Start column", param=metadata.ColumnParameter, readonly=True)
    MetadataElement(name="endCol", default=4, desc="End column", param=metadata.ColumnParameter, readonly=True)


class BedTabix(IntervalTabix):
    """
    Class describing a tabix file built from a bed file
    """

    file_ext = "bed_tabix.gz"


class GffTabix(IntervalTabix):
    """
    Class describing a tabix file built from a bed file
    """

    file_ext = "gff_tabix.gz"

    # The MetadataElements are readonly so the user cannot change them (as the index is generated only once)
    MetadataElement(name="startCol", default=4, desc="Start column", param=metadata.ColumnParameter, readonly=True)
    MetadataElement(name="endCol", default=5, desc="End column", param=metadata.ColumnParameter, readonly=True)
