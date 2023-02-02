""" Clearing house for generic text datatypes that are not XML or tabular.
"""

import gzip
import json
import logging
import os
import re
import subprocess
import tempfile
from typing import (
    IO,
    Optional,
    Tuple,
)

import yaml

from galaxy.datatypes.data import (
    get_file_peek,
    Headers,
    Text,
)
from galaxy.datatypes.metadata import (
    MetadataElement,
    MetadataParameter,
)
from galaxy.datatypes.protocols import (
    DatasetHasHidProtocol,
    DatasetProtocol,
    HasCreatingJob,
    HasExtraFilesAndMetadata,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    iter_headers,
)
from galaxy.util import (
    nice_size,
    shlex_join,
    string_as_bool,
    unicodify,
)

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class Html(Text):
    """Class describing an html file"""

    edam_format = "format_2331"
    file_ext = "html"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "HTML file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "text/html"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in html format

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'complete.bed' )
        >>> Html().sniff( fname )
        False
        >>> fname = get_test_fname( 'file.html' )
        >>> Html().sniff( fname )
        True
        """
        headers = iter_headers(file_prefix, None)
        for hdr in headers:
            if hdr and hdr[0].lower().find("<html>") >= 0:
                return True
        return False


@build_sniff_from_prefix
class Json(Text):
    edam_format = "format_3464"
    file_ext = "json"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "JavaScript Object Notation (JSON)"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "application/json"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to load the string with the json module. If successful it's a json file.
        """
        return self._looks_like_json(file_prefix)

    def _looks_like_json(self, file_prefix: FilePrefix) -> bool:
        # Pattern used by SequenceSplitLocations
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            # If the file is small enough - don't guess just check.
            try:
                item = json.loads(file_prefix.contents_header)
                # exclude simple types, must set format in these cases
                assert isinstance(item, (list, dict))
                return True
            except Exception:
                return False
        else:
            start = file_prefix.string_io().read(100).strip()
            if start:
                # simple types are valid JSON as well,
                # but if necessary format has to be set explicitly
                return start.startswith("[") or start.startswith("{")
            return False

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return f"JSON file ({nice_size(dataset.get_size())})"


class ExpressionJson(Json):
    """Represents the non-data input or output to a tool or workflow."""

    file_ext = "json"
    MetadataElement(
        name="json_type", default=None, desc="JavaScript or JSON type of expression", readonly=True, visible=True
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """ """
        if dataset.has_data():
            json_type = "null"
            file_path = dataset.file_name
            try:
                with open(file_path) as f:
                    obj = json.load(f)
                    if isinstance(obj, int):
                        json_type = "int"
                    elif isinstance(obj, float):
                        json_type = "float"
                    elif isinstance(obj, list):
                        json_type = "list"
                    elif isinstance(obj, dict):
                        json_type = "object"
            except json.decoder.JSONDecodeError:
                with open(file_path) as f:
                    contents = f.read(512)
                raise Exception(f"Invalid JSON encountered {contents}")
            dataset.metadata.json_type = json_type


@build_sniff_from_prefix
class Ipynb(Json):
    file_ext = "ipynb"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "Jupyter Notebook"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to load the string with the json module. If successful it's a json file.
        """
        if self._looks_like_json(file_prefix):
            try:
                with open(file_prefix.filename) as f:
                    ipynb = json.load(f)
                if ipynb.get("nbformat", False) is not False and ipynb.get("metadata", False):
                    return True
                else:
                    return False
            except Exception:
                return False
        return False

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
        config = trans.app.config
        trust = getattr(config, "trust_jupyter_notebook_conversion", False)
        if trust:
            return self._display_data_trusted(
                trans, dataset, preview=preview, filename=filename, to_ext=to_ext, headers=headers, **kwd
            )
        else:
            return super().display_data(
                trans, dataset, preview=preview, filename=filename, to_ext=to_ext, headers=headers, **kwd
            )

    def _display_data_trusted(
        self,
        trans,
        dataset: DatasetHasHidProtocol,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        **kwd,
    ) -> Tuple[IO, Headers]:
        headers = kwd.get("headers", {})
        preview = string_as_bool(preview)
        if to_ext or not preview:
            return self._serve_raw(dataset, to_ext, headers, **kwd)
        else:
            with tempfile.NamedTemporaryFile(delete=False) as ofile_handle:
                ofilename = ofile_handle.name
            try:
                cmd = [
                    "jupyter",
                    "nbconvert",
                    "--to",
                    "html",
                    "--template",
                    "full",
                    dataset.file_name,
                    "--output",
                    ofilename,
                ]
                subprocess.check_call(cmd)
                ofilename = f"{ofilename}.html"
            except subprocess.CalledProcessError:
                ofilename = dataset.file_name
                log.exception(
                    'Command "%s" failed. Could not convert the Jupyter Notebook to HTML, defaulting to plain text.',
                    shlex_join(cmd),
                )
            return open(ofilename, mode="rb"), headers

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of models in dataset.
        """


@build_sniff_from_prefix
class Biom1(Json):
    """
    BIOM version 1.0 file format description
    http://biom-format.org/documentation/format_versions/biom-1.0.html
    """

    file_ext = "biom1"
    edam_format = "format_3746"

    MetadataElement(
        name="table_rows",
        default=[],
        desc="table_rows",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="table_matrix_element_type",
        default="",
        desc="table_matrix_element_type",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value="",
    )
    MetadataElement(
        name="table_format",
        default="",
        desc="table_format",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value="",
    )
    MetadataElement(
        name="table_generated_by",
        default="",
        desc="table_generated_by",
        param=MetadataParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value="",
    )
    MetadataElement(
        name="table_matrix_type",
        default="",
        desc="table_matrix_type",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value="",
    )
    MetadataElement(
        name="table_shape",
        default=[],
        desc="table_shape",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="table_format_url",
        default="",
        desc="table_format_url",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value="",
    )
    MetadataElement(
        name="table_date",
        default="",
        desc="table_date",
        param=MetadataParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value="",
    )
    MetadataElement(
        name="table_type",
        default="",
        desc="table_type",
        param=MetadataParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value="",
    )
    MetadataElement(
        name="table_id",
        default=None,
        desc="table_id",
        param=MetadataParameter,
        readonly=True,
        visible=True,
        optional=True,
    )
    MetadataElement(
        name="table_columns",
        default=[],
        desc="table_columns",
        param=MetadataParameter,
        readonly=True,
        visible=False,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="table_column_metadata_headers",
        default=[],
        desc="table_column_metadata_headers",
        param=MetadataParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        super().set_peek(dataset)
        if not dataset.dataset.purged:
            dataset.blurb = "Biological Observation Matrix v1"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        is_biom = False
        if self._looks_like_json(file_prefix):
            is_biom = self._looks_like_biom(file_prefix)
        return is_biom

    def _looks_like_biom(self, file_prefix: FilePrefix, load_size: int = 50000) -> bool:
        """
        @param filepath: [str] The path to the evaluated file.
        @param load_size: [int] The size of the file block load in RAM (in
                          bytes).
        """
        is_biom = False
        segment_size = int(load_size / 2)
        try:
            with open(file_prefix.filename) as fh:
                prev_str = ""
                segment_str = fh.read(segment_size)
                if segment_str.strip().startswith("{"):
                    while segment_str:
                        current_str = prev_str + segment_str
                        if '"format"' in current_str:
                            current_str = re.sub(r"\s", "", current_str)
                            if '"format":"BiologicalObservationMatrix' in current_str:
                                is_biom = True
                                break
                        prev_str = segment_str
                        segment_str = fh.read(segment_size)
        except Exception:
            pass
        return is_biom

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Store metadata information from the BIOM file.
        """
        if dataset.has_data():
            with open(dataset.file_name) as fh:
                try:
                    json_dict = json.load(fh)
                except Exception:
                    return

                def _transform_dict_list_ids(dict_list):
                    if dict_list:
                        return [x.get("id", None) for x in dict_list]
                    return []

                b_transform = {"rows": _transform_dict_list_ids, "columns": _transform_dict_list_ids}
                for m_name, b_name in [
                    ("table_rows", "rows"),
                    ("table_matrix_element_type", "matrix_element_type"),
                    ("table_format", "format"),
                    ("table_generated_by", "generated_by"),
                    ("table_matrix_type", "matrix_type"),
                    ("table_shape", "shape"),
                    ("table_format_url", "format_url"),
                    ("table_date", "date"),
                    ("table_type", "type"),
                    ("table_id", "id"),
                    ("table_columns", "columns"),
                ]:
                    try:
                        metadata_value = json_dict.get(b_name, None)
                        if b_name == "columns" and metadata_value:
                            keep_columns = set()
                            for column in metadata_value:
                                if column["metadata"] is not None:
                                    for k, v in column["metadata"].items():
                                        if v is not None:
                                            keep_columns.add(k)
                            final_list = sorted(list(keep_columns))
                            dataset.metadata.table_column_metadata_headers = final_list
                        if b_name in b_transform:
                            metadata_value = b_transform[b_name](metadata_value)
                        setattr(dataset.metadata, m_name, metadata_value)
                    except Exception:
                        log.exception("Something in the metadata detection for biom1 went wrong.")


@build_sniff_from_prefix
class ImgtJson(Json):
    """
    https://github.com/repseqio/library-imgt/releases
    Data coming from IMGT server may be used for academic research only,
    provided that it is referred to IMGT®, and cited as:
    "IMGT®, the international ImMunoGeneTics information system®
    http://www.imgt.org (founder and director: Marie-Paule Lefranc, Montpellier, France)."
    """

    file_ext = "imgt.json"

    MetadataElement(name="taxon_names", default=[], desc="taxonID: names", readonly=True, visible=True, no_value=[])

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        super().set_peek(dataset)
        if not dataset.dataset.purged:
            dataset.blurb = "IMGT Library"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in json format with imgt elements

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( '1.json' )
        >>> ImgtJson().sniff( fname )
        False
        >>> fname = get_test_fname( 'imgt.json' )
        >>> ImgtJson().sniff( fname )
        True
        """
        is_imgt = False
        if self._looks_like_json(file_prefix):
            is_imgt = self._looks_like_imgt(file_prefix)
        return is_imgt

    def _looks_like_imgt(self, file_prefix: FilePrefix, load_size: int = 5000) -> bool:
        """
        @param filepath: [str] The path to the evaluated file.
        @param load_size: [int] The size of the file block load in RAM (in
                          bytes).
        """
        is_imgt = False
        try:
            with open(file_prefix.filename) as fh:
                segment_str = fh.read(load_size)
                if segment_str.strip().startswith("["):
                    if '"taxonId"' in segment_str and '"anchorPoints"' in segment_str:
                        is_imgt = True
        except Exception:
            pass
        return is_imgt

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Store metadata information from the imgt file.
        """
        if dataset.has_data():
            with open(dataset.file_name) as fh:
                try:
                    json_dict = json.load(fh)
                    tax_names = []
                    for entry in json_dict:
                        if "taxonId" in entry:
                            names = "%d: %s" % (entry["taxonId"], ",".join(entry["speciesNames"]))
                            tax_names.append(names)
                    dataset.metadata.taxon_names = tax_names
                except Exception:
                    return


@build_sniff_from_prefix
class GeoJson(Json):
    """
    GeoJSON is a geospatial data interchange format based on JavaScript Object Notation (JSON).
    https://tools.ietf.org/html/rfc7946
    """

    file_ext = "geojson"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        super().set_peek(dataset)
        if not dataset.dataset.purged:
            dataset.blurb = "GeoJSON"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in json format with imgt elements

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( '1.json' )
        >>> GeoJson().sniff( fname )
        False
        >>> fname = get_test_fname( 'gis.geojson' )
        >>> GeoJson().sniff( fname )
        True
        """
        is_geojson = False
        if self._looks_like_json(file_prefix):
            is_geojson = self._looks_like_geojson(file_prefix)
        return is_geojson

    def _looks_like_geojson(self, file_prefix: FilePrefix, load_size: int = 5000) -> bool:
        """
        One of "Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon", and "GeometryCollection" needs to be present.
        All of "type", "geometry", and "coordinates" needs to be present.
        """
        is_geojson = False
        try:
            with open(file_prefix.filename) as fh:
                segment_str = fh.read(load_size)
                if any(
                    x in segment_str
                    for x in [
                        "Point",
                        "MultiPoint",
                        "LineString",
                        "MultiLineString",
                        "Polygon",
                        "MultiPolygon",
                        "GeometryCollection",
                    ]
                ):
                    if all(x in segment_str for x in ["type", "geometry", "coordinates"]):
                        return True
        except Exception:
            pass
        return is_geojson


@build_sniff_from_prefix
class Obo(Text):
    """
    OBO file format description
    https://owlcollab.github.io/oboformat/doc/GO.format.obo-1_2.html
    """

    edam_data = "data_0582"
    edam_format = "format_2549"
    file_ext = "obo"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "Open Biomedical Ontology (OBO)"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess the Obo filetype.
        It usually starts with a "format-version:" string and has several stanzas which starts with "id:".
        """
        stanza = re.compile(r"^\[.*\]$")
        handle = file_prefix.string_io()
        first_line = handle.readline()
        if not first_line.startswith("format-version:"):
            return False

        for line in handle:
            if stanza.match(line.strip()):
                # a stanza needs to begin with an ID tag
                if next(handle).startswith("id:"):
                    return True
        return False


@build_sniff_from_prefix
class Arff(Text):
    """
    An ARFF (Attribute-Relation File Format) file is an ASCII text file that describes a list of instances sharing a set of attributes.
    http://weka.wikispaces.com/ARFF
    """

    edam_format = "format_3581"
    file_ext = "arff"

    MetadataElement(
        name="comment_lines", default=0, desc="Number of comment lines", readonly=True, optional=True, no_value=0
    )
    MetadataElement(name="columns", default=0, desc="Number of columns", readonly=True, visible=True, no_value=0)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "Attribute-Relation File Format (ARFF)"
            dataset.blurb += f", {dataset.metadata.comment_lines} comments, {dataset.metadata.columns} attributes"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess the Arff filetype.
        It usually starts with a "format-version:" string and has several stanzas which starts with "id:".
        """
        handle = file_prefix.string_io()
        relation_found = False
        attribute_found = False
        for line_count, line in enumerate(handle):
            if line_count > 1000:
                # only investigate the first 1000 lines
                return False
            line = line.strip()
            if not line:
                continue

            start_string = line[:20].upper()
            if start_string.startswith("@RELATION"):
                relation_found = True
            elif start_string.startswith("@ATTRIBUTE"):
                attribute_found = True
            elif start_string.startswith("@DATA"):
                # @DATA should be the last data block
                if relation_found and attribute_found:
                    return True
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Trying to count the comment lines and the number of columns included.
        A typical ARFF data block looks like this:
        @DATA
        5.1,3.5,1.4,0.2,Iris-setosa
        4.9,3.0,1.4,0.2,Iris-setosa
        """
        comment_lines = column_count = 0
        if dataset.has_data():
            first_real_line = False
            data_block = False
            with open(dataset.file_name) as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("%") and not first_real_line:
                        comment_lines += 1
                    else:
                        first_real_line = True
                    if data_block:
                        if line.startswith("{"):
                            # Sparse representation
                            """
                                @data
                                0, X, 0, Y, "class A", {5}
                            or
                                @data
                                {1 X, 3 Y, 4 "class A"}, {5}
                            """
                            token = line.split("}", 1)
                            first_part = token[0]
                            last_column = first_part.split(",")[-1].strip()
                            numeric_value = last_column.split()[0]
                            column_count = int(numeric_value)
                            if len(token) > 1:
                                # we have an additional weight
                                column_count -= 1
                        else:
                            columns = line.strip().split(",")
                            column_count = len(columns)
                            if columns[-1].strip().startswith("{"):
                                # we have an additional weight at the end
                                column_count -= 1

                        # We have now the column_count and we know the initial comment lines. So we can terminate here.
                        break
                    if line[:5].upper() == "@DATA":
                        data_block = True
        dataset.metadata.comment_lines = comment_lines
        dataset.metadata.columns = column_count


class SnpEffDb(Text):
    """Class describing a SnpEff genome build"""

    edam_format = "format_3624"
    file_ext = "snpeffdb"
    MetadataElement(name="genome_version", default=None, desc="Genome Version", readonly=True, visible=True)
    MetadataElement(name="snpeff_version", default="SnpEff4.0", desc="SnpEff Version", readonly=True, visible=True)
    MetadataElement(
        name="regulation", default=[], desc="Regulation Names", readonly=True, visible=True, no_value=[], optional=True
    )
    MetadataElement(
        name="annotation", default=[], desc="Annotation Names", readonly=True, visible=True, no_value=[], optional=True
    )

    def __init__(self, **kwd):
        super().__init__(**kwd)

    # The SnpEff version line was added in SnpEff version 4.1
    def getSnpeffVersionFromFile(self, path: str) -> Optional[str]:
        snpeff_version = None
        try:
            with gzip.open(path, "rt") as fh:
                buf = fh.read(100)
                lines = buf.splitlines()
                m = re.match(r"^(SnpEff)\s+(\d+\.\d+).*$", lines[0].strip())
                if m:
                    snpeff_version = m.groups()[0] + m.groups()[1]
        except Exception:
            pass
        return snpeff_version

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        data_dir = dataset.extra_files_path
        # search data_dir/genome_version for files
        regulation_pattern = "regulation_(.+).bin"
        #  annotation files that are included in snpEff by a flag
        annotations_dict = {"nextProt.bin": "-nextprot", "motif.bin": "-motif", "interactions.bin": "-interaction"}
        regulations = []
        annotations = []
        genome_version = None
        snpeff_version = None
        if data_dir and os.path.isdir(data_dir):
            for root, _, files in os.walk(data_dir):
                for fname in files:
                    if fname.startswith("snpEffectPredictor"):
                        # if snpEffectPredictor.bin download succeeded
                        genome_version = os.path.basename(root)
                        dataset.metadata.genome_version = genome_version
                        # read the first line of the gzipped snpEffectPredictor.bin file to get the SnpEff version
                        snpeff_version = self.getSnpeffVersionFromFile(os.path.join(root, fname))
                        if snpeff_version:
                            dataset.metadata.snpeff_version = snpeff_version
                    else:
                        m = re.match(regulation_pattern, fname)
                        if m:
                            name = m.groups()[0]
                            regulations.append(name)
                        elif fname in annotations_dict:
                            value = annotations_dict[fname]
                            name = value.lstrip("-")
                            annotations.append(name)
            dataset.metadata.regulation = regulations
            dataset.metadata.annotation = annotations
            try:
                with open(dataset.file_name, "w") as fh:
                    fh.write(f"{genome_version}\n" if genome_version else "Genome unknown")
                    fh.write(f"{snpeff_version}\n" if snpeff_version else "SnpEff version unknown")
                    if annotations:
                        fh.write(f"annotations: {','.join(annotations)}\n")
                    if regulations:
                        fh.write(f"regulations: {','.join(regulations)}\n")
            except Exception:
                pass


class SnpSiftDbNSFP(Text):
    """
    Class describing a dbNSFP database prepared fpr use by SnpSift dbnsfp

    The dbNSFP file is a tabular file with 1 header line.
    The first 4 columns are required to be: chrom	pos	ref	alt
    These match columns 1,2,4,5 of the VCF file
    SnpSift requires the file to be block-gzipped and the indexed with samtools tabix

    Example:
    - Compress using block-gzip algorithm:
    $ bgzip dbNSFP2.3.txt
    - Create tabix index
    $ tabix -s 1 -b 2 -e 2 dbNSFP2.3.txt.gz
    """

    file_ext = "snpsiftdbnsfp"
    composite_type = "auto_primary_file"

    MetadataElement(
        name="reference_name",
        default="dbSNFP",
        desc="Reference Name",
        readonly=True,
        visible=True,
        set_in_upload=True,
        no_value="dbSNFP",
    )
    MetadataElement(name="bgzip", default=None, desc="dbNSFP bgzip", readonly=True, visible=True)
    MetadataElement(name="index", default=None, desc="Tabix Index File", readonly=True, visible=True)
    MetadataElement(name="annotation", default=[], desc="Annotation Names", readonly=True, visible=True, no_value=[])

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.gz", description="dbNSFP bgzip", substitute_name_with_metadata="reference_name", is_binary=True
        )
        self.add_composite_file(
            "%s.gz.tbi", description="Tabix Index File", substitute_name_with_metadata="reference_name", is_binary=True
        )

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        return "<html><head><title>SnpSiftDbNSFP Composite Dataset</title></head></html>"

    def regenerate_primary_file(self, dataset: DatasetProtocol) -> None:
        """
        cannot do this until we are setting metadata
        """
        annotations = f"dbNSFP Annotations: {','.join(dataset.metadata.annotation)}\n"
        with open(dataset.file_name, "a") as f:
            if dataset.metadata.bgzip:
                bn = dataset.metadata.bgzip
                f.write(bn)
                f.write("\n")
            f.write(annotations)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        try:
            efp = dataset.extra_files_path
            if os.path.exists(efp):
                flist = os.listdir(efp)
                for fname in flist:
                    if fname.endswith(".gz"):
                        dataset.metadata.bgzip = fname
                        try:
                            with gzip.open(os.path.join(efp, fname), "rt") as fh:
                                buf = fh.read(5000)
                                lines = buf.splitlines()
                                headers = lines[0].split("\t")
                                dataset.metadata.annotation = headers[4:]
                        except Exception as e:
                            log.warning("set_meta fname: %s  %s", fname, unicodify(e))
                    if fname.endswith(".tbi"):
                        dataset.metadata.index = fname
            self.regenerate_primary_file(dataset)
        except Exception as e:
            log.warning(
                "set_meta fname: %s  %s",
                dataset.file_name if dataset and dataset.file_name else "Unkwown",
                unicodify(e),
            )

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = f"{dataset.metadata.reference_name} :  {','.join(dataset.metadata.annotation)}"
            dataset.blurb = f"{dataset.metadata.reference_name}"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"


@build_sniff_from_prefix
class IQTree(Text):
    """IQ-TREE format"""

    file_ext = "iqtree"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Detect the IQTree file

        Scattered text file containing various headers and data
        types.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('example.iqtree')
        >>> IQTree().sniff(fname)
        True

        >>> fname = get_test_fname('temp.txt')
        >>> IQTree().sniff(fname)
        False

        >>> fname = get_test_fname('test_tab1.tabular')
        >>> IQTree().sniff(fname)
        False
        """
        return file_prefix.startswith("IQ-TREE")


@build_sniff_from_prefix
class Paf(Text):
    """
    PAF: a Pairwise mApping Format

    https://github.com/lh3/miniasm/blob/master/PAF.md
    """

    file_ext = "paf"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('A-3105.paf')
        >>> Paf().sniff(fname)
        True
        """
        found_valid_lines = False
        for line in iter_headers(file_prefix, "\t"):
            if len(line) < 12:
                return False
            for i in (1, 2, 3, 6, 7, 8, 9, 10, 11):
                int(line[i])
            if line[4] not in ("+", "-"):
                return False
            if not (0 <= int(line[11]) <= 255):
                return False
            # Check that the optional columns after the 12th contain SAM-like typed key-value pairs
            for i in range(12, len(line)):
                if len(line[i].split(":")) != 3:
                    return False
            found_valid_lines = True
        return found_valid_lines


@build_sniff_from_prefix
class Gfa1(Text):
    """
    Graphical Fragment Assembly (GFA) 1.0

    http://gfa-spec.github.io/GFA-spec/GFA1.html
    """

    file_ext = "gfa1"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('big.gfa1')
        >>> Gfa1().sniff(fname)
        True
        >>> Gfa2().sniff(fname)
        False
        """
        found_valid_lines = False
        for line in iter_headers(file_prefix, "\t"):
            if line[0].startswith("#"):
                continue
            if line[0] == "H":
                return len(line) == 2 and line[1] == "VN:Z:1.0"
            elif line[0] == "S":
                if len(line) < 3:
                    return False
            elif line[0] == "L":
                if len(line) < 6:
                    return False
                for i in (2, 4):
                    if line[i] not in ("+", "-"):
                        return False
            elif line[0] == "C":
                if len(line) < 7:
                    return False
                for i in (2, 4):
                    if line[i] not in ("+", "-"):
                        return False
                int(line[5])
            elif line[0] == "P":
                if len(line) < 4:
                    return False
            else:
                return False
            found_valid_lines = True
        return found_valid_lines


@build_sniff_from_prefix
class Gfa2(Text):
    """
    Graphical Fragment Assembly (GFA) 2.0

    https://github.com/GFA-spec/GFA-spec/blob/master/GFA2.md
    """

    file_ext = "gfa2"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('sample.gfa2')
        >>> Gfa2().sniff(fname)
        True
        >>> Gfa1().sniff(fname)
        False
        """
        found_valid_lines = False
        for line in iter_headers(file_prefix, "\t"):
            if line[0].startswith("#"):
                continue
            if line[0] == "H":
                return len(line) >= 2 and line[1] == "VN:Z:2.0"
            elif line[0] == "S":
                if len(line) < 3:
                    return False
            elif line[0] == "F":
                if len(line) < 8:
                    return False
            elif line[0] == "E":
                if len(line) < 9:
                    return False
            elif line[0] == "G":
                if len(line) < 6:
                    return False
            elif line[0] == "O" or line[0] == "U":
                if len(line) < 3:
                    return False
            else:
                return False
            found_valid_lines = True
        return found_valid_lines


@build_sniff_from_prefix
class Yaml(Text):
    """Yaml files"""

    file_ext = "yaml"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to load the string with the yaml module. If successful it's a yaml file.
        """
        return self._looks_like_yaml(file_prefix)

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "application/yaml"

    def _yield_user_file_content(self, trans, from_dataset: HasCreatingJob, filename: str, headers: Headers) -> IO:
        # Override non-standard application/yaml mediatype with
        # text/plain, so preview is shown in preview iframe,
        # instead of downloading the file.
        headers["content-type"] = "text/plain"
        return super()._yield_user_file_content(trans, from_dataset, filename, headers)

    def _looks_like_yaml(self, file_prefix: FilePrefix) -> bool:
        # Pattern used by SequenceSplitLocations
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            # If the file is small enough - don't guess just check.
            try:
                item = yaml.safe_load(file_prefix.contents_header)
                assert isinstance(item, (list, dict))
                return True
            except yaml.YAMLError:
                return False
        else:
            # If file is too big, load the first part. Trim the current line, in case it cut off in the middle of a key.
            file_start = file_prefix.string_io().read(50000).strip().rsplit("\n", 1)[0]
            try:
                item = yaml.safe_load(file_start)
                assert isinstance(item, (list, dict))
                return True
            except yaml.YAMLError:
                return False
            return False


@build_sniff_from_prefix
class BCSLmodel(Text):
    """BioChemical Space Language model file"""

    file_ext = "bcsl.model"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in .bcsl.model format
        """
        reg = r"^#! rules|^#! inits|^#! definitions"
        return re.search(reg, file_prefix.contents_header, re.MULTILINE) is not None


@build_sniff_from_prefix
class BCSLts(Json):
    """BioChemical Space Language transition system file"""

    file_ext = "bcsl.ts"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in .bcsl.ts format
        """
        is_bcsl_ts = False
        if self._looks_like_json(file_prefix):
            is_bcsl_ts = self._looks_like_bcsl_ts(file_prefix)
        return is_bcsl_ts

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            lines = "States: {}\nTransitions: {}\nUnique agents: {}\nInitial state: {}"
            ts = json.load(open(dataset.file_name))
            dataset.peek = lines.format(len(ts["nodes"]), len(ts["edges"]), len(ts["ordering"]), ts["initial"])
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def _looks_like_bcsl_ts(self, file_prefix: FilePrefix) -> bool:
        content = open(file_prefix.filename).read()
        keywords = ['"edges":', '"nodes":', '"ordering":', '"initial":']
        if all(keyword in content for keyword in keywords):
            return self._looks_like_json(file_prefix)
        return False


@build_sniff_from_prefix
class StormSample(Text):
    """
    Storm PCTL parameter synthesis result file
    containing probability function of parameters.
    """

    file_ext = "storm.sample"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in .storm.sample format
        """
        keywords = ["Storm-pars", "Result (initial states)"]
        return all(keyword in file_prefix.contents_header for keyword in keywords)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "Storm-pars sample results."
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class StormCheck(Text):
    """
    Storm PCTL model checking result file
    containing boolean or numerical result.
    """

    file_ext = "storm.check"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in .storm.check format
        """
        keywords = ["Storm ", "Result (for initial states)"]
        return all(keyword in file_prefix.contents_header for keyword in keywords)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            with open(dataset.file_name) as result:
                answer = ""
                for line in result:
                    if "Result (for initial states):" in line:
                        answer = line.split()[-1]
                        break
            dataset.peek = f"Model checking result: {answer}"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class CTLresult(Text):
    """CTL model checking result"""

    file_ext = "ctl.result"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in .ctl.result format
        """
        keywords = ["Result:", "Number of satisfying states:"]
        return all(keyword in file_prefix.contents_header for keyword in keywords)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            with open(dataset.file_name) as result:
                answer = ""
                for line in result:
                    if "Result:" in line:
                        answer = line.split()[-1]
            dataset.peek = f"Model checking result: {answer}"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class PithyaProperty(Text):
    """Pithya CTL property format"""

    file_ext = "pithya.property"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in .pithya.property format
        """
        return re.search(r":\?[a-zA-Z0-9_]+[ ]*=", file_prefix.contents_header) is not None


@build_sniff_from_prefix
class PithyaModel(Text):
    """Pithya model format"""

    file_ext = "pithya.model"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in .pithya.model format
        """
        keywords = ["VARS", "EQ", "THRES"]
        return all(keyword in file_prefix.contents_header for keyword in keywords)


@build_sniff_from_prefix
class PithyaResult(Json):
    """Pithya result format"""

    file_ext = "pithya.result"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in .pithya.result format
        """
        is_pithya_result = False
        if self._looks_like_json(file_prefix):
            is_pithya_result = self._looks_like_pithya_result(file_prefix)
        return is_pithya_result

    def _looks_like_pithya_result(self, file_prefix: FilePrefix) -> bool:
        content = open(file_prefix.filename).read()
        keywords = ['"variables":', '"states":', '"parameter_values":', '"results":']
        if all(keyword in content for keyword in keywords):
            return self._looks_like_json(file_prefix)
        return False


@build_sniff_from_prefix
class Castep(Text):
    """Report on a CASTEP calculation"""

    file_ext = "castep"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file is a CASTEP log

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.castep')
        >>> Castep().sniff(fname)
        True
        >>> fname = get_test_fname('Si.param')
        >>> Castep().sniff(fname)
        False
        """
        castep_header = [
            "+-------------------------------------------------+",
            "|                                                 |",
            "|      CCC   AA    SSS  TTTTT  EEEEE  PPPP        |",
            "|     C     A  A  S       T    E      P   P       |",
            "|     C     AAAA   SS     T    EEE    PPPP        |",
            "|     C     A  A     S    T    E      P           |",
            "|      CCC  A  A  SSS     T    EEEEE  P           |",
            "|                                                 |",
            "+-------------------------------------------------+",
        ]
        handle = file_prefix.string_io()
        for header_line in castep_header:
            if handle.readline().strip() != header_line:
                return False
        return True


@build_sniff_from_prefix
class Param(Yaml):
    """CASTEP parameter input file"""

    file_ext = "param"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Modified version of the normal Yaml sniff that also checks
        for a valid CASTEP task key-value pair, which is not case
        sensitive

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.param')
        >>> Param().sniff(fname)
        True
        >>> fname = get_test_fname('Si.castep')
        >>> Param().sniff(fname)
        False
        """
        valid_tasks = [
            "SINGLEPOINT",
            "BANDSTRUCTURE",
            "GEOMETRYOPTIMIZATION",
            "GEOMETRYOPTIMISATION",
            "MOLECULARDYNAMICS",
            "OPTICS",
            "PHONON",
            "EFIELD",
            "PHONON+EFIELD",
            "TRANSITIONSTATESEARCH",
            "MAGRES",
            "ELNES",
            "ELECTRONICSPECTROSCOPY",
        ]

        # check it looks like YAML
        if not super().sniff_prefix(file_prefix):
            return False

        # check the TASK keyword is present
        # and that it is set to a valid CASTEP task
        pattern = re.compile(r"^TASK ?: ?([A-Z\+]*)$", flags=re.IGNORECASE | re.MULTILINE)
        task = file_prefix.search(pattern)
        return task and task.group(1).upper() in valid_tasks


@build_sniff_from_prefix
class FormattedDensity(Text):
    """Final electron density from a CASTEP calculation written to an ASCII file"""

    file_ext = "den_fmt"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file contains electron densities in the CASTEP den_fmt format

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.den_fmt')
        >>> FormattedDensity().sniff(fname)
        True
        >>> fname = get_test_fname('Si.param')
        >>> FormattedDensity().sniff(fname)
        False
        """
        begin_header = "BEGIN header"
        end_header = 'END header: data is "<a b c> charge" in units of electrons/grid_point * number'
        grid_points = "of grid_points"
        handle = file_prefix.string_io()
        lines = handle.readlines()
        return lines[0].strip() == begin_header and lines[9].strip() == end_header and lines[10].strip() == grid_points
