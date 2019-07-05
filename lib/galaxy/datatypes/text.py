# -*- coding: utf-8 -*-
""" Clearing house for generic text datatypes that are not XML or tabular.
"""

import gzip
import json
import logging
import os
import re
import subprocess
import tempfile

from six.moves import shlex_quote

from galaxy.datatypes.data import get_file_peek, Text
from galaxy.datatypes.metadata import MetadataElement, MetadataParameter
from galaxy.datatypes.sniff import build_sniff_from_prefix, iter_headers
from galaxy.util import nice_size, string_as_bool

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class Html(Text):
    """Class describing an html file"""
    edam_format = "format_2331"
    file_ext = "html"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "HTML file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/html'

    def sniff_prefix(self, file_prefix):
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
        for i, hdr in enumerate(headers):
            if hdr and hdr[0].lower().find('<html>') >= 0:
                return True
        return False


@build_sniff_from_prefix
class Json(Text):
    edam_format = "format_3464"
    file_ext = "json"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "JavaScript Object Notation (JSON)"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/json'

    def sniff_prefix(self, file_prefix):
        """
            Try to load the string with the json module. If successful it's a json file.
        """
        return self._looks_like_json(file_prefix)

    def _looks_like_json(self, file_prefix):
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

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "JSON file (%s)" % (nice_size(dataset.get_size()))


@build_sniff_from_prefix
class Ipynb(Json):
    file_ext = "ipynb"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "Jupyter Notebook"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff_prefix(self, file_prefix):
        """
            Try to load the string with the json module. If successful it's a json file.
        """
        if self._looks_like_json(file_prefix):
            try:
                with open(file_prefix.filename) as f:
                    ipynb = json.load(f)
                if ipynb.get('nbformat', False) is not False and ipynb.get('metadata', False):
                    return True
                else:
                    return False
            except Exception:
                return False

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, **kwd):
        config = trans.app.config
        trust = getattr(config, 'trust_jupyter_notebook_conversion', False)
        if trust:
            return self._display_data_trusted(trans, dataset, preview=preview, filename=filename, to_ext=to_ext, **kwd)
        else:
            return super(Ipynb, self).display_data(trans, dataset, preview=preview, filename=filename, to_ext=to_ext, **kwd)

    def _display_data_trusted(self, trans, dataset, preview=False, filename=None, to_ext=None, **kwd):
        preview = string_as_bool(preview)
        if to_ext or not preview:
            return self._serve_raw(trans, dataset, to_ext, **kwd)
        else:
            with tempfile.NamedTemporaryFile(delete=False) as ofile_handle:
                ofilename = ofile_handle.name
            try:
                cmd = ['jupyter', 'nbconvert', '--to', 'html', '--template', 'full', dataset.file_name, '--output', ofilename]
                subprocess.check_call(cmd)
                ofilename = '%s.html' % ofilename
            except subprocess.CalledProcessError:
                ofilename = dataset.file_name
                log.exception('Command "%s" failed. Could not convert the Jupyter Notebook to HTML, defaulting to plain text.', ' '.join(map(shlex_quote, cmd)))
            return open(ofilename, mode='rb')

    def set_meta(self, dataset, **kwd):
        """
        Set the number of models in dataset.
        """
        pass


@build_sniff_from_prefix
class Biom1(Json):
    """
        BIOM version 1.0 file format description
        http://biom-format.org/documentation/format_versions/biom-1.0.html
    """
    file_ext = "biom1"
    edam_format = "format_3746"

    MetadataElement(name="table_rows", default=[], desc="table_rows", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[])
    MetadataElement(name="table_matrix_element_type", default="", desc="table_matrix_element_type", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value="")
    MetadataElement(name="table_format", default="", desc="table_format", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value="")
    MetadataElement(name="table_generated_by", default="", desc="table_generated_by", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value="")
    MetadataElement(name="table_matrix_type", default="", desc="table_matrix_type", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value="")
    MetadataElement(name="table_shape", default=[], desc="table_shape", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[])
    MetadataElement(name="table_format_url", default="", desc="table_format_url", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value="")
    MetadataElement(name="table_date", default="", desc="table_date", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value="")
    MetadataElement(name="table_type", default="", desc="table_type", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value="")
    MetadataElement(name="table_id", default=None, desc="table_id", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value=None)
    MetadataElement(name="table_columns", default=[], desc="table_columns", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[])
    MetadataElement(name="table_column_metadata_headers", default=[], desc="table_column_metadata_headers", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value=[])

    def set_peek(self, dataset, is_multi_byte=False):
        super(Biom1, self).set_peek(dataset)
        if not dataset.dataset.purged:
            dataset.blurb = "Biological Observation Matrix v1"

    def sniff_prefix(self, file_prefix):
        is_biom = False
        if self._looks_like_json(file_prefix):
            is_biom = self._looks_like_biom(file_prefix)
        return is_biom

    def _looks_like_biom(self, file_prefix, load_size=50000):
        """
        @param filepath: [str] The path to the evaluated file.
        @param load_size: [int] The size of the file block load in RAM (in
                          bytes).
        """
        is_biom = False
        segment_size = int(load_size / 2)
        try:
            with open(file_prefix.filename, "r") as fh:
                prev_str = ""
                segment_str = fh.read(segment_size)
                if segment_str.strip().startswith('{'):
                    while segment_str:
                        current_str = prev_str + segment_str
                        if '"format"' in current_str:
                            current_str = re.sub(r'\s', '', current_str)
                            if '"format":"BiologicalObservationMatrix' in current_str:
                                is_biom = True
                                break
                        prev_str = segment_str
                        segment_str = fh.read(segment_size)
        except Exception:
            pass
        return is_biom

    def set_meta(self, dataset, **kwd):
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
                        return [x.get('id', None) for x in dict_list]
                    return []

                b_transform = {'rows': _transform_dict_list_ids, 'columns': _transform_dict_list_ids}
                for (m_name, b_name) in [('table_rows', 'rows'),
                                         ('table_matrix_element_type', 'matrix_element_type'),
                                         ('table_format', 'format'),
                                         ('table_generated_by', 'generated_by'),
                                         ('table_matrix_type', 'matrix_type'),
                                         ('table_shape', 'shape'),
                                         ('table_format_url', 'format_url'),
                                         ('table_date', 'date'),
                                         ('table_type', 'type'),
                                         ('table_id', 'id'),
                                         ('table_columns', 'columns')]:
                    try:
                        metadata_value = json_dict.get(b_name, None)
                        if b_name == "columns" and metadata_value:
                            keep_columns = set()
                            for column in metadata_value:
                                for k, v in column['metadata'].items():
                                    if v is not None:
                                        keep_columns.add(k)
                            final_list = sorted(list(keep_columns))
                            dataset.metadata.table_column_metadata_headers = final_list
                        if b_name in b_transform:
                            metadata_value = b_transform[b_name](metadata_value)
                        setattr(dataset.metadata, m_name, metadata_value)
                    except Exception:
                        log.exception("Something in the metadata detection for biom1 went wrong.")
                        pass


@build_sniff_from_prefix
class Obo(Text):
    """
        OBO file format description
        https://owlcollab.github.io/oboformat/doc/GO.format.obo-1_2.html
    """
    edam_data = "data_0582"
    edam_format = "format_2549"
    file_ext = "obo"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "Open Biomedical Ontology (OBO)"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff_prefix(self, file_prefix):
        """
            Try to guess the Obo filetype.
            It usually starts with a "format-version:" string and has several stanzas which starts with "id:".
        """
        stanza = re.compile(r'^\[.*\]$')
        handle = file_prefix.string_io()
        first_line = handle.readline()
        if not first_line.startswith('format-version:'):
            return False

        for line in handle:
            if stanza.match(line.strip()):
                # a stanza needs to begin with an ID tag
                if next(handle).startswith('id:'):
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

    """Add metadata elements"""
    MetadataElement(name="comment_lines", default=0, desc="Number of comment lines", readonly=True, optional=True, no_value=0)
    MetadataElement(name="columns", default=0, desc="Number of columns", readonly=True, visible=True, no_value=0)

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "Attribute-Relation File Format (ARFF)"
            dataset.blurb += ", %s comments, %s attributes" % (dataset.metadata.comment_lines, dataset.metadata.columns)
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff_prefix(self, file_prefix):
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

    def set_meta(self, dataset, **kwd):
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
                    if line.startswith('%') and not first_real_line:
                        comment_lines += 1
                    else:
                        first_real_line = True
                    if data_block:
                        if line.startswith('{'):
                            # Sparse representation
                            """
                                @data
                                0, X, 0, Y, "class A", {5}
                            or
                                @data
                                {1 X, 3 Y, 4 "class A"}, {5}
                            """
                            token = line.split('}', 1)
                            first_part = token[0]
                            last_column = first_part.split(',')[-1].strip()
                            numeric_value = last_column.split()[0]
                            column_count = int(numeric_value)
                            if len(token) > 1:
                                # we have an additional weight
                                column_count -= 1
                        else:
                            columns = line.strip().split(',')
                            column_count = len(columns)
                            if columns[-1].strip().startswith('{'):
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
    MetadataElement(name="genome_version", default=None, desc="Genome Version", readonly=True, visible=True, no_value=None)
    MetadataElement(name="snpeff_version", default="SnpEff4.0", desc="SnpEff Version", readonly=True, visible=True, no_value=None)
    MetadataElement(name="regulation", default=[], desc="Regulation Names", readonly=True, visible=True, no_value=[], optional=True)
    MetadataElement(name="annotation", default=[], desc="Annotation Names", readonly=True, visible=True, no_value=[], optional=True)

    def __init__(self, **kwd):
        Text.__init__(self, **kwd)

    # The SnpEff version line was added in SnpEff version 4.1
    def getSnpeffVersionFromFile(self, path):
        snpeff_version = None
        try:
            with gzip.open(path, 'rb') as fh:
                buf = fh.read(100)
                lines = buf.splitlines()
                m = re.match(r'^(SnpEff)\s+(\d+\.\d+).*$', lines[0].strip())
                if m:
                    snpeff_version = m.groups()[0] + m.groups()[1]
        except Exception:
            pass
        return snpeff_version

    def set_meta(self, dataset, **kwd):
        Text.set_meta(self, dataset, **kwd)
        data_dir = dataset.extra_files_path
        # search data_dir/genome_version for files
        regulation_pattern = 'regulation_(.+).bin'
        #  annotation files that are included in snpEff by a flag
        annotations_dict = {'nextProt.bin': '-nextprot', 'motif.bin': '-motif', 'interactions.bin': '-interaction'}
        regulations = []
        annotations = []
        genome_version = None
        snpeff_version = None
        if data_dir and os.path.isdir(data_dir):
            for root, dirs, files in os.walk(data_dir):
                for fname in files:
                    if fname.startswith('snpEffectPredictor'):
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
                            name = value.lstrip('-')
                            annotations.append(name)
            dataset.metadata.regulation = regulations
            dataset.metadata.annotation = annotations
            try:
                with open(dataset.file_name, 'w') as fh:
                    fh.write("%s\n" % genome_version if genome_version else 'Genome unknown')
                    fh.write("%s\n" % snpeff_version if snpeff_version else 'SnpEff version unknown')
                    if annotations:
                        fh.write("annotations: %s\n" % ','.join(annotations))
                    if regulations:
                        fh.write("regulations: %s\n" % ','.join(regulations))
            except Exception:
                pass


class SnpSiftDbNSFP(Text):
    """Class describing a dbNSFP database prepared fpr use by SnpSift dbnsfp """
    MetadataElement(name='reference_name', default='dbSNFP', desc='Reference Name', readonly=True, visible=True, set_in_upload=True, no_value='dbSNFP')
    MetadataElement(name="bgzip", default=None, desc="dbNSFP bgzip", readonly=True, visible=True, no_value=None)
    MetadataElement(name="index", default=None, desc="Tabix Index File", readonly=True, visible=True, no_value=None)
    MetadataElement(name="annotation", default=[], desc="Annotation Names", readonly=True, visible=True, no_value=[])
    file_ext = "snpsiftdbnsfp"
    composite_type = 'auto_primary_file'
    allow_datatype_change = False
    """
    ## The dbNSFP file is a tabular file with 1 header line
    ## The first 4 columns are required to be: chrom	pos	ref	alt
    ## These match columns 1,2,4,5 of the VCF file
    ## SnpSift requires the file to be block-gzipped and the indexed with samtools tabix
    ## Example:
    ## Compress using block-gzip algorithm
    bgzip dbNSFP2.3.txt
    ## Create tabix index
    tabix -s 1 -b 2 -e 2 dbNSFP2.3.txt.gz
    """

    def __init__(self, **kwd):
        Text.__init__(self, **kwd)
        self.add_composite_file('%s.gz', description='dbNSFP bgzip', substitute_name_with_metadata='reference_name', is_binary=True)
        self.add_composite_file('%s.gz.tbi', description='Tabix Index File', substitute_name_with_metadata='reference_name', is_binary=True)

    def init_meta(self, dataset, copy_from=None):
        Text.init_meta(self, dataset, copy_from=copy_from)

    def generate_primary_file(self, dataset=None):
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        return '<html><head><title>SnpSiftDbNSFP Composite Dataset</title></head></html>'

    def regenerate_primary_file(self, dataset):
        """
        cannot do this until we are setting metadata
        """
        annotations = "dbNSFP Annotations: %s\n" % ','.join(dataset.metadata.annotation)
        with open(dataset.file_name, 'a') as f:
            if dataset.metadata.bgzip:
                bn = dataset.metadata.bgzip
                f.write(bn)
                f.write('\n')
            f.write(annotations)

    def set_meta(self, dataset, overwrite=True, **kwd):
        try:
            efp = dataset.extra_files_path
            if os.path.exists(efp):
                flist = os.listdir(efp)
                for i, fname in enumerate(flist):
                    if fname.endswith('.gz'):
                        dataset.metadata.bgzip = fname
                        try:
                            with gzip.open(os.path.join(efp, fname), 'r') as fh:
                                buf = fh.read(5000)
                                lines = buf.splitlines()
                                headers = lines[0].split('\t')
                                dataset.metadata.annotation = headers[4:]
                        except Exception as e:
                            log.warning("set_meta fname: %s  %s" % (fname, str(e)))
                    if fname.endswith('.tbi'):
                        dataset.metadata.index = fname
            self.regenerate_primary_file(dataset)
        except Exception as e:
            log.warning("set_meta fname: %s  %s" % (dataset.file_name if dataset and dataset.file_name else 'Unkwown', str(e)))

        def set_peek(self, dataset, is_multi_byte=False):
            if not dataset.dataset.purged:
                dataset.peek = '%s :  %s' % (dataset.metadata.reference_name, ','.join(dataset.metadata.annotation))
                dataset.blurb = '%s' % dataset.metadata.reference_name
            else:
                dataset.peek = 'file does not exist'
                dataset.blurb = 'file purged from disc'


@build_sniff_from_prefix
class IQTree(Text):
    """IQ-TREE format"""
    file_ext = 'iqtree'

    def sniff_prefix(self, file_prefix):
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
