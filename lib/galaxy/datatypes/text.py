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

from galaxy.datatypes.data import get_file_peek, Text
from galaxy.datatypes.metadata import MetadataElement, MetadataParameter
from galaxy.datatypes.sniff import get_headers
from galaxy.util import nice_size, string_as_bool

log = logging.getLogger(__name__)


class Html( Text ):
    """Class describing an html file"""
    edam_format = "format_2331"
    file_ext = "html"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = "HTML file"
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/html'

    def sniff( self, filename ):
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
        headers = get_headers( filename, None )
        try:
            for i, hdr in enumerate(headers):
                if hdr and hdr[0].lower().find( '<html>' ) >= 0:
                    return True
            return False
        except:
            return True


class Json( Text ):
    edam_format = "format_3464"
    file_ext = "json"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = "JavaScript Object Notation (JSON)"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff( self, filename ):
        """
            Try to load the string with the json module. If successful it's a json file.
        """
        return self._looks_like_json( filename )

    def _looks_like_json( self, filename ):
        # Pattern used by SequenceSplitLocations
        if os.path.getsize(filename) < 50000:
            # If the file is small enough - don't guess just check.
            try:
                json.load( open(filename, "r") )
                return True
            except Exception:
                return False
        else:
            with open(filename, "r") as fh:
                while True:
                    # Grab first chunk of file and see if it looks like json.
                    start = fh.read(100).strip()
                    if start:
                        # simple types are valid JSON as well - but would such a file
                        # be interesting as JSON in Galaxy?
                        return start.startswith("[") or start.startswith("{")
            return False

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "JSON file (%s)" % ( nice_size( dataset.get_size() ) )


class Ipynb( Json ):
    file_ext = "ipynb"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = "Jupyter Notebook"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff( self, filename ):
        """
            Try to load the string with the json module. If successful it's a json file.
        """
        if self._looks_like_json( filename ):
            try:
                ipynb = json.load( open(filename) )
                if ipynb.get('nbformat', False) is not False and ipynb.get('metadata', False):
                    return True
                else:
                    return False
            except:
                return False

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, **kwd):
        config = trans.app.config
        trust = getattr( config, 'trust_jupyter_notebook_conversion', False )
        if trust:
            return self._display_data_trusted(trans, dataset, preview=preview, filename=filename, to_ext=to_ext, **kwd)
        else:
            return super(Ipynb, self).display_data( trans, dataset, preview=preview, filename=filename, to_ext=to_ext, **kwd )

    def _display_data_trusted(self, trans, dataset, preview=False, filename=None, to_ext=None, **kwd):
        preview = string_as_bool( preview )
        if to_ext or not preview:
            return self._serve_raw(trans, dataset, to_ext)
        else:
            ofile_handle = tempfile.NamedTemporaryFile(delete=False)
            ofilename = ofile_handle.name
            ofile_handle.close()
            try:
                cmd = 'jupyter nbconvert --to html --template full %s --output %s' % (dataset.file_name, ofilename)
                log.info("Calling command %s" % cmd)
                subprocess.call(cmd, shell=True)
                ofilename = '%s.html' % ofilename
            except:
                ofilename = dataset.file_name
                log.exception( 'Command "%s" failed. Could not convert the Jupyter Notebook to HTML, defaulting to plain text.' % cmd )
            return open( ofilename )

    def set_meta( self, dataset, **kwd ):
        """
        Set the number of models in dataset.
        """
        pass


class Biom1( Json ):
    """
        BIOM version 1.0 file format description
        http://biom-format.org/documentation/format_versions/biom-1.0.html
    """
    file_ext = "biom1"

    MetadataElement( name="table_rows", default=[], desc="table_rows", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[] )
    MetadataElement( name="table_matrix_element_type", default="", desc="table_matrix_element_type", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value="" )
    MetadataElement( name="table_format", default="", desc="table_format", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value="" )
    MetadataElement( name="table_generated_by", default="", desc="table_generated_by", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value="" )
    MetadataElement( name="table_matrix_type", default="", desc="table_matrix_type", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value="" )
    MetadataElement( name="table_shape", default=[], desc="table_shape", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[] )
    MetadataElement( name="table_format_url", default="", desc="table_format_url", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value="" )
    MetadataElement( name="table_date", default="", desc="table_date", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value="" )
    MetadataElement( name="table_type", default="", desc="table_type", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value="" )
    MetadataElement( name="table_id", default=None, desc="table_id", param=MetadataParameter, readonly=True, visible=True, optional=True, no_value=None )
    MetadataElement( name="table_columns", default=[], desc="table_columns", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[] )

    def set_peek( self, dataset, is_multi_byte=False ):
        super( Biom1, self ).set_peek( dataset, is_multi_byte )
        if not dataset.dataset.purged:
            dataset.blurb = "Biological Observation Matrix v1"

    def sniff( self, filename ):
        is_biom = False
        if self._looks_like_json( filename ):
            is_biom = self._looks_like_biom( filename )
        return is_biom

    def _looks_like_biom( self, filepath, load_size=50000 ):
        """
        @param filepath: [str] The path to the evaluated file.
        @param load_size: [int] The size of the file block load in RAM (in
                          bytes).
        """
        is_biom = False
        segment_size = int( load_size / 2 )
        try:
            with open( filepath, "r" ) as fh:
                prev_str = ""
                segment_str = fh.read( segment_size )
                if segment_str.strip().startswith( '{' ):
                    while segment_str:
                        current_str = prev_str + segment_str
                        if '"format"' in current_str:
                            current_str = re.sub( r'\s', '', current_str )
                            if '"format":"BiologicalObservationMatrix' in current_str:
                                is_biom = True
                                break
                        prev_str = segment_str
                        segment_str = fh.read( segment_size )
        except Exception:
            pass
        return is_biom

    def set_meta( self, dataset, **kwd ):
        """
            Store metadata information from the BIOM file.
        """
        if dataset.has_data():
            with open( dataset.file_name ) as fh:
                try:
                    json_dict = json.load( fh )
                except Exception:
                    return

                def _transform_dict_list_ids( dict_list ):
                    if dict_list:
                        return [ x.get( 'id', None ) for x in dict_list ]
                    return []

                b_transform = { 'rows': _transform_dict_list_ids, 'columns': _transform_dict_list_ids }
                for ( m_name, b_name ) in [ ('table_rows', 'rows'),
                                            ('table_matrix_element_type', 'matrix_element_type'),
                                            ('table_format', 'format'),
                                            ('table_generated_by', 'generated_by'),
                                            ('table_matrix_type', 'matrix_type'),
                                            ('table_shape', 'shape'),
                                            ('table_format_url', 'format_url'),
                                            ('table_date', 'date'),
                                            ('table_type', 'type'),
                                            ('table_id', 'id'),
                                            ('table_columns', 'columns') ]:
                    try:
                        metadata_value = json_dict.get( b_name, None )
                        if b_name in b_transform:
                            metadata_value = b_transform[ b_name ]( metadata_value )
                        setattr( dataset.metadata, m_name, metadata_value )
                    except Exception:
                        pass


class Obo( Text ):
    """
        OBO file format description
        http://www.geneontology.org/GO.format.obo-1_2.shtml
    """
    edam_data = "data_0582"
    edam_format = "format_2549"
    file_ext = "obo"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = "Open Biomedical Ontology (OBO)"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff( self, filename ):
        """
            Try to guess the Obo filetype.
            It usually starts with a "format-version:" string and has several stanzas which starts with "id:".
        """
        stanza = re.compile(r'^\[.*\]$')
        with open( filename ) as handle:
            first_line = handle.readline()
            if not first_line.startswith('format-version:'):
                return False

            for line in handle:
                if stanza.match(line.strip()):
                    # a stanza needs to begin with an ID tag
                    if handle.next().startswith('id:'):
                        return True
        return False


class Arff( Text ):
    """
        An ARFF (Attribute-Relation File Format) file is an ASCII text file that describes a list of instances sharing a set of attributes.
        http://weka.wikispaces.com/ARFF
    """
    edam_format = "format_3581"
    file_ext = "arff"

    """Add metadata elements"""
    MetadataElement( name="comment_lines", default=0, desc="Number of comment lines", readonly=True, optional=True, no_value=0 )
    MetadataElement( name="columns", default=0, desc="Number of columns", readonly=True, visible=True, no_value=0 )

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = "Attribute-Relation File Format (ARFF)"
            dataset.blurb += ", %s comments, %s attributes" % ( dataset.metadata.comment_lines, dataset.metadata.columns )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff( self, filename ):
        """
            Try to guess the Arff filetype.
            It usually starts with a "format-version:" string and has several stanzas which starts with "id:".
        """
        with open( filename ) as handle:
            relation_found = False
            attribute_found = False
            for line_count, line in enumerate( handle ):
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

    def set_meta( self, dataset, **kwd ):
        """
            Trying to count the comment lines and the number of columns included.
            A typical ARFF data block looks like this:
            @DATA
            5.1,3.5,1.4,0.2,Iris-setosa
            4.9,3.0,1.4,0.2,Iris-setosa
        """
        if dataset.has_data():
            comment_lines = 0
            first_real_line = False
            data_block = False
            with open( dataset.file_name ) as handle:
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


class SnpEffDb( Text ):
    """Class describing a SnpEff genome build"""
    edam_format = "format_3624"
    file_ext = "snpeffdb"
    MetadataElement( name="genome_version", default=None, desc="Genome Version", readonly=True, visible=True, no_value=None )
    MetadataElement( name="snpeff_version", default="SnpEff4.0", desc="SnpEff Version", readonly=True, visible=True, no_value=None )
    MetadataElement( name="regulation", default=[], desc="Regulation Names", readonly=True, visible=True, no_value=[], optional=True)
    MetadataElement( name="annotation", default=[], desc="Annotation Names", readonly=True, visible=True, no_value=[], optional=True)

    def __init__( self, **kwd ):
        Text.__init__( self, **kwd )

    # The SnpEff version line was added in SnpEff version 4.1
    def getSnpeffVersionFromFile(self, path):
        snpeff_version = None
        try:
            fh = gzip.open(path, 'rb')
            buf = fh.read(100)
            lines = buf.splitlines()
            m = re.match('^(SnpEff)\s+(\d+\.\d+).*$', lines[0].strip())
            if m:
                snpeff_version = m.groups()[0] + m.groups()[1]
            fh.close()
        except:
            pass
        return snpeff_version

    def set_meta( self, dataset, **kwd ):
        Text.set_meta(self, dataset, **kwd )
        data_dir = dataset.extra_files_path
        # search data_dir/genome_version for files
        regulation_pattern = 'regulation_(.+).bin'
        #  annotation files that are included in snpEff by a flag
        annotations_dict = {'nextProt.bin': '-nextprot', 'motif.bin': '-motif'}
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
            except:
                pass


class SnpSiftDbNSFP( Text ):
    """Class describing a dbNSFP database prepared fpr use by SnpSift dbnsfp """
    MetadataElement( name='reference_name', default='dbSNFP', desc='Reference Name', readonly=True, visible=True, set_in_upload=True, no_value='dbSNFP' )
    MetadataElement( name="bgzip", default=None, desc="dbNSFP bgzip", readonly=True, visible=True, no_value=None )
    MetadataElement( name="index", default=None, desc="Tabix Index File", readonly=True, visible=True, no_value=None)
    MetadataElement( name="annotation", default=[], desc="Annotation Names", readonly=True, visible=True, no_value=[] )
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
    def __init__( self, **kwd ):
        Text.__init__( self, **kwd )
        self.add_composite_file( '%s.gz', description='dbNSFP bgzip', substitute_name_with_metadata='reference_name', is_binary=True )
        self.add_composite_file( '%s.gz.tbi', description='Tabix Index File', substitute_name_with_metadata='reference_name', is_binary=True )

    def init_meta( self, dataset, copy_from=None ):
        Text.init_meta( self, dataset, copy_from=copy_from )

    def generate_primary_file( self, dataset=None ):
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        self.regenerate_primary_file( dataset )

    def regenerate_primary_file(self, dataset):
        """
        cannot do this until we are setting metadata
        """
        annotations = "dbNSFP Annotations: %s\n" % ','.join(dataset.metadata.annotation)
        f = open(dataset.file_name, 'a')
        if dataset.metadata.bgzip:
            bn = dataset.metadata.bgzip
            f.write(bn)
            f.write('\n')
        f.write(annotations)
        f.close()

    def set_meta( self, dataset, overwrite=True, **kwd ):
        try:
            efp = dataset.extra_files_path
            if os.path.exists(efp):
                flist = os.listdir(efp)
                for i, fname in enumerate(flist):
                    if fname.endswith('.gz'):
                        dataset.metadata.bgzip = fname
                        try:
                            fh = gzip.open(os.path.join(efp, fname), 'r')
                            buf = fh.read(5000)
                            lines = buf.splitlines()
                            headers = lines[0].split('\t')
                            dataset.metadata.annotation = headers[4:]
                        except Exception as e:
                            log.warning("set_meta fname: %s  %s" % (fname, str(e)))
                        finally:
                            fh.close()
                    if fname.endswith('.tbi'):
                        dataset.metadata.index = fname
            self.regenerate_primary_file(dataset)
        except Exception as e:
            log.warning("set_meta fname: %s  %s" % (dataset.file_name if dataset and dataset.file_name else 'Unkwown', str(e)))

        def set_peek( self, dataset, is_multi_byte=False ):
            if not dataset.dataset.purged:
                dataset.peek = '%s :  %s' % (dataset.metadata.reference_name, ','.join(dataset.metadata.annotation))
                dataset.blurb = '%s' % dataset.metadata.reference_name
            else:
                dataset.peek = 'file does not exist'
                dataset.blurb = 'file purged from disc'


class Smat(Text):
    file_ext = "smat"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "ESTScan scores matrices (%s)" % (nice_size(dataset.get_size()))

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name, is_multi_byte=is_multi_byte)
            dataset.blurb = "ESTScan scores matrices"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff(self, filename):
        """
        The use of ESTScan implies the creation of scores matrices which
        reflect the codons preferences in the studied organisms.  The
        ESTScan package includes scripts for generating these files.  The
        output of these scripts consists of the matrices, one for each
        isochor, and which look like this:

        FORMAT: hse_4is.conf CODING REGION 6 3 1 s C+G: 0 44
        -1 0 2 -2
        2 1 -8 0

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test_space.txt')
        >>> Smat().sniff(fname)
        False
        >>> fname = get_test_fname('test_tab.bed')
        >>> Smat().sniff(fname)
        False
        >>> fname = get_test_fname('1.smat')
        >>> Smat().sniff(fname)
        True
        """
        line_no = 0
        with open(filename, "r") as fh:
            line_no += 1
            if line_no > 10000:
                return True
            line = fh.readline(500)
            if line_no == 1 and not line.startswith('FORMAT'):
                # The first line is always the start of a format section.
                return False
            if not line.startswith('FORMAT'):
                if line.find('\t') >= 0:
                    # Smat files are not tabular.
                    return False
                items = line.split()
                if len(items) != 4:
                    return False
                for item in items:
                    # Make sure each item is an integer.
                    if re.match(r"[-+]?\d+$", item) is None:
                        return False
        return True


class PlantTribesOrtho(Html):
    """
    PlantTribes sequences classified into precomputed, orthologous gene family
    clusters.
    """
    file_ext = "ptortho"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesOrtho, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "PlantTribes gene family clusters: %d files" % dataset.metadata.data_lines


class PlantTribesOrthoCodingSequence(Html):
    """
    PlantTribes sequences classified into precomputed, orthologous gene family
    clusters and corresponding coding sequences.
    """
    file_ext = "ptorthocs"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesOrthoCodingSequence, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "PlantTribes gene family clusters with corresponding coding sequences: %d files" % dataset.metadata.data_lines


class PlantTribesPhylogeneticTree(Html):
    """
    PlantTribes multiple sequence alignments and inferred maximum likelihood
    phylogenies for orthogroups.
    """
    file_ext = "pttree"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesPhylogeneticTree, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "PlantTribes phylogenetic trees: %d files" % dataset.metadata.data_lines


class PlantTribesMultipleSequenceAlignment(Html):
    """
    PlantTribes multiple sequence alignments for orthogroups.
    """
    file_ext = "ptalign"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesMultipleSequenceAlignment, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "PlantTribes multiple sequence alignments: %d files" % dataset.metadata.data_lines
