"""
Tabular datatype
"""
from __future__ import absolute_import

import abc
import csv
import logging
import os
import re
import subprocess
import sys
import tempfile
from cgi import escape
from json import dumps

from galaxy import util
from galaxy.datatypes import data, metadata
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.sniff import get_headers
from galaxy.util import compression_utils

from . import dataproviders

if sys.version_info > (3,):
    long = int

log = logging.getLogger(__name__)


@dataproviders.decorators.has_dataproviders
class TabularData( data.Text ):
    """Generic tabular data"""
    edam_format = "format_3475"
    # All tabular data is chunkable.
    CHUNKABLE = True

    """Add metadata elements"""
    MetadataElement( name="comment_lines", default=0, desc="Number of comment lines", readonly=False, optional=True, no_value=0 )
    MetadataElement( name="data_lines", default=0, desc="Number of data lines", readonly=True, visible=False, optional=True, no_value=0 )
    MetadataElement( name="columns", default=0, desc="Number of columns", readonly=True, visible=False, no_value=0 )
    MetadataElement( name="column_types", default=[], desc="Column types", param=metadata.ColumnTypesParameter, readonly=True, visible=False, no_value=[] )
    MetadataElement( name="column_names", default=[], desc="Column names", readonly=True, visible=False, optional=True, no_value=[] )
    MetadataElement( name="delimiter", default='\t', desc="Data delimiter", readonly=True, visible=False, optional=True, no_value=[] )

    @abc.abstractmethod
    def set_meta( self, dataset, **kwd ):
        raise NotImplementedError

    def set_peek( self, dataset, line_count=None, is_multi_byte=False, WIDTH=256, skipchars=None ):
        super(TabularData, self).set_peek( dataset, line_count=line_count, is_multi_byte=is_multi_byte, WIDTH=WIDTH, skipchars=skipchars, line_wrap=False )
        if dataset.metadata.comment_lines:
            dataset.blurb = "%s, %s comments" % ( dataset.blurb, util.commaify( str( dataset.metadata.comment_lines ) ) )

    def displayable( self, dataset ):
        try:
            return dataset.has_data() \
                and dataset.state == dataset.states.OK \
                and dataset.metadata.columns > 0 \
                and dataset.metadata.data_lines != 0
        except:
            return False

    def get_chunk(self, trans, dataset, offset=0, ck_size=None):
        with open(dataset.file_name) as f:
            f.seek(offset)
            ck_data = f.read(ck_size or trans.app.config.display_chunk_size)
            if ck_data and ck_data[-1] != '\n':
                cursor = f.read(1)
                while cursor and cursor != '\n':
                    ck_data += cursor
                    cursor = f.read(1)
            last_read = f.tell()
        return dumps( { 'ck_data': util.unicodify( ck_data ),
                        'offset': last_read } )

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, offset=None, ck_size=None, **kwd):
        preview = util.string_as_bool( preview )
        if offset is not None:
            return self.get_chunk(trans, dataset, offset, ck_size)
        elif to_ext or not preview:
            to_ext = to_ext or dataset.extension
            return self._serve_raw(trans, dataset, to_ext)
        elif dataset.metadata.columns > 50:
            # Fancy tabular display is only suitable for datasets without an incredibly large number of columns.
            # We should add a new datatype 'matrix', with its own draw method, suitable for this kind of data.
            # For now, default to the old behavior, ugly as it is.  Remove this after adding 'matrix'.
            max_peek_size = 1000000  # 1 MB
            if os.stat( dataset.file_name ).st_size < max_peek_size:
                self._clean_and_set_mime_type( trans, dataset.get_mime() )
                return open( dataset.file_name )
            else:
                trans.response.set_content_type( "text/html" )
                return trans.stream_template_mako( "/dataset/large_file.mako",
                                                   truncated_data=open( dataset.file_name ).read(max_peek_size),
                                                   data=dataset)
        else:
            column_names = 'null'
            if dataset.metadata.column_names:
                column_names = dataset.metadata.column_names
            elif hasattr(dataset.datatype, 'column_names'):
                column_names = dataset.datatype.column_names
            column_types = dataset.metadata.column_types
            if not column_types:
                column_types = []
            column_number = dataset.metadata.columns
            if column_number is None:
                column_number = 'null'
            return trans.fill_template( "/dataset/tabular_chunked.mako",
                                        dataset=dataset,
                                        chunk=self.get_chunk(trans, dataset, 0),
                                        column_number=column_number,
                                        column_names=column_names,
                                        column_types=column_types )

    def make_html_table( self, dataset, **kwargs ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        try:
            out.append( self.make_html_peek_header( dataset, **kwargs ) )
            out.append( self.make_html_peek_rows( dataset, **kwargs ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception as exc:
            out = "Can't create peek %s" % str( exc )
        return out

    def make_html_peek_header( self, dataset, skipchars=None, column_names=None, column_number_format='%s', column_parameter_alias=None, **kwargs ):
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
            column_headers = [None] * columns

            # fill in empty headers with data from column_names
            for i in range( min( columns, len( column_names ) ) ):
                if column_headers[i] is None and column_names[i] is not None:
                    column_headers[i] = column_names[i]

            # fill in empty headers from ColumnParameters set in the metadata
            for name, spec in dataset.metadata.spec.items():
                if isinstance( spec.param, metadata.ColumnParameter ):
                    try:
                        i = int( getattr( dataset.metadata, name ) ) - 1
                    except:
                        i = -1
                    if 0 <= i < columns and column_headers[i] is None:
                        column_headers[i] = column_parameter_alias.get(name, name)

            out.append( '<tr>' )
            for i, header in enumerate( column_headers ):
                out.append( '<th>' )
                if header is None:
                    out.append( column_number_format % str( i + 1 ) )
                else:
                    out.append( '%s.%s' % ( str( i + 1 ), escape( header ) ) )
                out.append( '</th>' )
            out.append( '</tr>' )
        except Exception as exc:
            log.exception( 'make_html_peek_header failed on HDA %s' % dataset.id )
            raise Exception( "Can't create peek header %s" % str( exc ) )
        return "".join( out )

    def make_html_peek_rows( self, dataset, skipchars=None, **kwargs ):
        if skipchars is None:
            skipchars = []
        out = []
        try:
            if not dataset.peek:
                dataset.set_peek()
            columns = dataset.metadata.columns
            if columns is None:
                columns = dataset.metadata.spec.columns.no_value
            for line in dataset.peek.splitlines():
                if line.startswith( tuple( skipchars ) ):
                    out.append( '<tr><td colspan="100%%">%s</td></tr>' % escape( line ) )
                elif line:
                    elems = line.split( dataset.metadata.delimiter )
                    # pad shortened elems, since lines could have been truncated by width
                    if len( elems ) < columns:
                        elems.extend( [''] * ( columns - len( elems ) ) )
                    # we may have an invalid comment line or invalid data
                    if len( elems ) != columns:
                        out.append( '<tr><td colspan="100%%">%s</td></tr>' % escape( line ) )
                    else:
                        out.append( '<tr>' )
                        for elem in elems:
                            out.append( '<td>%s</td>' % escape( elem ) )
                        out.append( '</tr>' )
        except Exception as exc:
            log.exception( 'make_html_peek_rows failed on HDA %s' % dataset.id )
            raise Exception( "Can't create peek rows %s" % str( exc ) )
        return "".join( out )

    def display_peek( self, dataset ):
        """Returns formatted html of peek"""
        return self.make_html_table( dataset )

    # ------------- Dataproviders
    @dataproviders.decorators.dataprovider_factory( 'column', dataproviders.column.ColumnarDataProvider.settings )
    def column_dataprovider( self, dataset, **settings ):
        """Uses column settings that are passed in"""
        dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
        delimiter = dataset.metadata.delimiter
        return dataproviders.column.ColumnarDataProvider( dataset_source, deliminator=delimiter, **settings )

    @dataproviders.decorators.dataprovider_factory( 'dataset-column',
                                                    dataproviders.column.ColumnarDataProvider.settings )
    def dataset_column_dataprovider( self, dataset, **settings ):
        """Attempts to get column settings from dataset.metadata"""
        delimiter = dataset.metadata.delimiter
        return dataproviders.dataset.DatasetColumnarDataProvider( dataset, deliminator=delimiter, **settings )

    @dataproviders.decorators.dataprovider_factory( 'dict', dataproviders.column.DictDataProvider.settings )
    def dict_dataprovider( self, dataset, **settings ):
        """Uses column settings that are passed in"""
        dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
        delimiter = dataset.metadata.delimiter
        return dataproviders.column.DictDataProvider( dataset_source, deliminator=delimiter, **settings )

    @dataproviders.decorators.dataprovider_factory( 'dataset-dict', dataproviders.column.DictDataProvider.settings )
    def dataset_dict_dataprovider( self, dataset, **settings ):
        """Attempts to get column settings from dataset.metadata"""
        delimiter = dataset.metadata.delimiter
        return dataproviders.dataset.DatasetDictDataProvider( dataset, deliminator=delimiter, **settings )


@dataproviders.decorators.has_dataproviders
class Tabular( TabularData ):
    """Tab delimited data"""

    def set_meta( self, dataset, overwrite=True, skip=None, max_data_lines=100000, max_guess_type_data_lines=None, **kwd ):
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
        column_type_set_order = [ 'int', 'float', 'list', 'str'  ]  # Order to set column types in
        default_column_type = column_type_set_order[-1]  # Default column type is lowest in list
        column_type_compare_order = list( column_type_set_order )  # Order to compare column types
        column_type_compare_order.reverse()

        def type_overrules_type( column_type1, column_type2 ):
            if column_type1 is None or column_type1 == column_type2:
                return False
            if column_type2 is None:
                return True
            for column_type in column_type_compare_order:
                if column_type1 == column_type:
                    return True
                if column_type2 == column_type:
                    return False
            # neither column type was found in our ordered list, this cannot happen
            raise ValueError( "Tried to compare unknown column types: %s and %s" % ( column_type1, column_type2 ) )

        def is_int( column_text ):
            try:
                int( column_text )
                return True
            except:
                return False

        def is_float( column_text ):
            try:
                float( column_text )
                return True
            except:
                if column_text.strip().lower() == 'na':
                    return True  # na is special cased to be a float
                return False

        def is_list( column_text ):
            return "," in column_text

        def is_str( column_text ):
            # anything, except an empty string, is True
            if column_text == "":
                return False
            return True
        is_column_type = {}  # Dict to store column type string to checking function
        for column_type in column_type_set_order:
            is_column_type[column_type] = locals()[ "is_%s" % ( column_type ) ]

        def guess_column_type( column_text ):
            for column_type in column_type_set_order:
                if is_column_type[column_type]( column_text ):
                    return column_type
            return None
        data_lines = 0
        comment_lines = 0
        column_types = []
        first_line_column_types = [default_column_type]  # default value is one column of type str
        if dataset.has_data():
            # NOTE: if skip > num_check_lines, we won't detect any metadata, and will use default
            dataset_fh = open( dataset.file_name )
            i = 0
            while True:
                line = dataset_fh.readline()
                if not line:
                    break
                line = line.rstrip( '\r\n' )
                if i < skip or not line or line.startswith( '#' ):
                    # We'll call blank lines comments
                    comment_lines += 1
                else:
                    data_lines += 1
                    if max_guess_type_data_lines is None or data_lines <= max_guess_type_data_lines:
                        fields = line.split( '\t' )
                        for field_count, field in enumerate( fields ):
                            if field_count >= len( column_types ):  # found a previously unknown column, we append None
                                column_types.append( None )
                            column_type = guess_column_type( field )
                            if type_overrules_type( column_type, column_types[field_count] ):
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
                        column_types = [ None for col in first_line_column_types ]
                if max_data_lines is not None and data_lines >= max_data_lines:
                    if dataset_fh.tell() != dataset.get_size():
                        data_lines = None  # Clear optional data_lines metadata value
                        comment_lines = None  # Clear optional comment_lines metadata value; additional comment lines could appear below this point
                    break
                i += 1
            dataset_fh.close()

        # we error on the larger number of columns
        # first we pad our column_types by using data from first line
        if len( first_line_column_types ) > len( column_types ):
            for column_type in first_line_column_types[len( column_types ):]:
                column_types.append( column_type )
        # Now we fill any unknown (None) column_types with data from first line
        for i in range( len( column_types ) ):
            if column_types[i] is None:
                if len( first_line_column_types ) <= i or first_line_column_types[i] is None:
                    column_types[i] = default_column_type
                else:
                    column_types[i] = first_line_column_types[i]
        # Set the discovered metadata values for the dataset
        dataset.metadata.data_lines = data_lines
        dataset.metadata.comment_lines = comment_lines
        dataset.metadata.column_types = column_types
        dataset.metadata.columns = len( column_types )
        dataset.metadata.delimiter = '\t'

    def as_gbrowse_display_file( self, dataset, **kwd ):
        return open( dataset.file_name )

    def as_ucsc_display_file( self, dataset, **kwd ):
        return open( dataset.file_name )


class Taxonomy( Tabular ):
    def __init__(self, **kwd):
        """Initialize taxonomy datatype"""
        super(Taxonomy, self).__init__( **kwd )
        self.column_names = ['Name', 'TaxId', 'Root', 'Superkingdom', 'Kingdom', 'Subkingdom',
                             'Superphylum', 'Phylum', 'Subphylum', 'Superclass', 'Class', 'Subclass',
                             'Superorder', 'Order', 'Suborder', 'Superfamily', 'Family', 'Subfamily',
                             'Tribe', 'Subtribe', 'Genus', 'Subgenus', 'Species', 'Subspecies'
                             ]

    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return self.make_html_table( dataset, column_names=self.column_names )


@dataproviders.decorators.has_dataproviders
class Sam( Tabular ):
    edam_format = "format_2573"
    edam_data = "data_0863"
    file_ext = 'sam'
    track_type = "ReadTrack"
    data_sources = { "data": "bam", "index": "bigwig" }

    def __init__(self, **kwd):
        """Initialize taxonomy datatype"""
        super( Sam, self ).__init__( **kwd )
        self.column_names = ['QNAME', 'FLAG', 'RNAME', 'POS', 'MAPQ', 'CIGAR',
                             'MRNM', 'MPOS', 'ISIZE', 'SEQ', 'QUAL', 'OPT'
                             ]

    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return self.make_html_table( dataset, column_names=self.column_names )

    def sniff( self, filename ):
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
        try:
            fh = open( filename )
            count = 0
            while True:
                line = fh.readline()
                line = line.strip()
                if not line:
                    break  # EOF
                if line:
                    if line[0] != '@':
                        line_pieces = line.split('\t')
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
            fh.close()
            if count < 5 and count > 0:
                return True
        except:
            pass
        return False

    def set_meta( self, dataset, overwrite=True, skip=None, max_data_lines=5, **kwd ):
        if dataset.has_data():
            dataset_fh = open( dataset.file_name )
            comment_lines = 0
            if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
                # If the dataset is larger than optional_metadata, just count comment lines.
                for i, l in enumerate(dataset_fh):
                    if l.startswith('@'):
                        comment_lines += 1
                    else:
                        # No more comments, and the file is too big to look at the whole thing.  Give up.
                        dataset.metadata.data_lines = None
                        break
            else:
                # Otherwise, read the whole thing and set num data lines.
                for i, l in enumerate(dataset_fh):
                    if l.startswith('@'):
                        comment_lines += 1
                dataset.metadata.data_lines = i + 1 - comment_lines
            dataset_fh.close()
            dataset.metadata.comment_lines = comment_lines
            dataset.metadata.columns = 12
            dataset.metadata.column_types = ['str', 'int', 'str', 'int', 'int', 'str', 'str', 'int', 'int', 'str', 'str', 'str']

    def merge( split_files, output_file):
        """
        Multiple SAM files may each have headers. Since the headers should all be the same, remove
        the headers from files 1-n, keeping them in the first file only
        """
        cmd = 'mv %s %s' % ( split_files[0], output_file )
        result = os.system(cmd)
        if result != 0:
            raise Exception('Result %s from %s' % (result, cmd))
        if len(split_files) > 1:
            cmd = 'egrep -v -h "^@" %s >> %s' % ( ' '.join(split_files[1:]), output_file )
        result = os.system(cmd)
        if result != 0:
            raise Exception('Result %s from %s' % (result, cmd))
    merge = staticmethod(merge)

    # Dataproviders
    # sam does not use '#' to indicate comments/headers - we need to strip out those headers from the std. providers
    # TODO:?? seems like there should be an easier way to do this - metadata.comment_char?
    @dataproviders.decorators.dataprovider_factory( 'line', dataproviders.line.FilteredLineDataProvider.settings )
    def line_dataprovider( self, dataset, **settings ):
        settings[ 'comment_char' ] = '@'
        return super( Sam, self ).line_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'regex-line', dataproviders.line.RegexLineDataProvider.settings )
    def regex_line_dataprovider( self, dataset, **settings ):
        settings[ 'comment_char' ] = '@'
        return super( Sam, self ).regex_line_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'column', dataproviders.column.ColumnarDataProvider.settings )
    def column_dataprovider( self, dataset, **settings ):
        settings[ 'comment_char' ] = '@'
        return super( Sam, self ).column_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'dataset-column',
                                                    dataproviders.column.ColumnarDataProvider.settings )
    def dataset_column_dataprovider( self, dataset, **settings ):
        settings[ 'comment_char' ] = '@'
        return super( Sam, self ).dataset_column_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'dict', dataproviders.column.DictDataProvider.settings )
    def dict_dataprovider( self, dataset, **settings ):
        settings[ 'comment_char' ] = '@'
        return super( Sam, self ).dict_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'dataset-dict', dataproviders.column.DictDataProvider.settings )
    def dataset_dict_dataprovider( self, dataset, **settings ):
        settings[ 'comment_char' ] = '@'
        return super( Sam, self ).dataset_dict_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'header', dataproviders.line.RegexLineDataProvider.settings )
    def header_dataprovider( self, dataset, **settings ):
        dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
        headers_source = dataproviders.line.RegexLineDataProvider( dataset_source, regex_list=[ '^@' ] )
        return dataproviders.line.RegexLineDataProvider( headers_source, **settings )

    @dataproviders.decorators.dataprovider_factory( 'id-seq-qual', dict_dataprovider.settings )
    def id_seq_qual_dataprovider( self, dataset, **settings ):
        # provided as an example of a specified column dict (w/o metadata)
        settings[ 'indeces' ] = [ 0, 9, 10 ]
        settings[ 'column_names' ] = [ 'id', 'seq', 'qual' ]
        return self.dict_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'genomic-region',
                                                    dataproviders.dataset.GenomicRegionDataProvider.settings )
    def genomic_region_dataprovider( self, dataset, **settings ):
        settings[ 'comment_char' ] = '@'
        return dataproviders.dataset.GenomicRegionDataProvider( dataset, 2, 3, 3, **settings )

    @dataproviders.decorators.dataprovider_factory( 'genomic-region-dict',
                                                    dataproviders.dataset.GenomicRegionDataProvider.settings )
    def genomic_region_dict_dataprovider( self, dataset, **settings ):
        settings[ 'comment_char' ] = '@'
        return dataproviders.dataset.GenomicRegionDataProvider( dataset, 2, 3, 3, True, **settings )

    # @dataproviders.decorators.dataprovider_factory( 'samtools' )
    # def samtools_dataprovider( self, dataset, **settings ):
    #     dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
    #     return dataproviders.dataset.SamtoolsDataProvider( dataset_source, **settings )


@dataproviders.decorators.has_dataproviders
class Pileup( Tabular ):
    """Tab delimited data in pileup (6- or 10-column) format"""
    edam_format = "format_3015"
    file_ext = "pileup"
    line_class = "genomic coordinate"
    data_sources = { "data": "tabix" }

    """Add metadata elements"""
    MetadataElement( name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="startCol", default=2, desc="Start column", param=metadata.ColumnParameter )
    MetadataElement( name="endCol", default=2, desc="End column", param=metadata.ColumnParameter )
    MetadataElement( name="baseCol", default=3, desc="Reference base column", param=metadata.ColumnParameter )

    def init_meta( self, dataset, copy_from=None ):
        super( Pileup, self ).init_meta( dataset, copy_from=copy_from )

    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return self.make_html_table( dataset, column_parameter_alias={'chromCol': 'Chrom', 'startCol': 'Start', 'baseCol': 'Base'} )

    def repair_methods( self, dataset ):
        """Return options for removing errors along with a description"""
        return [ ("lines", "Remove erroneous lines") ]

    def sniff( self, filename ):
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
        """
        headers = get_headers( filename, '\t' )
        try:
            for hdr in headers:
                if hdr and not hdr[0].startswith( '#' ):
                    if len( hdr ) < 5:
                        return False
                    try:
                        # chrom start in column 1 (with 0-based columns)
                        # and reference base is in column 2
                        chrom = int( hdr[1] )
                        assert chrom >= 0
                        assert hdr[2] in [ 'A', 'C', 'G', 'T', 'N', 'a', 'c', 'g', 't', 'n' ]
                    except:
                        return False
            return True
        except:
            return False

    # Dataproviders
    @dataproviders.decorators.dataprovider_factory( 'genomic-region',
                                                    dataproviders.dataset.GenomicRegionDataProvider.settings )
    def genomic_region_dataprovider( self, dataset, **settings ):
        return dataproviders.dataset.GenomicRegionDataProvider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'genomic-region-dict',
                                                    dataproviders.dataset.GenomicRegionDataProvider.settings )
    def genomic_region_dict_dataprovider( self, dataset, **settings ):
        settings[ 'named_columns' ] = True
        return self.genomic_region_dataprovider( dataset, **settings )


@dataproviders.decorators.has_dataproviders
class Vcf( Tabular ):
    """ Variant Call Format for describing SNPs and other simple genome variations. """
    edam_format = "format_3016"
    track_type = "VariantTrack"
    data_sources = { "data": "tabix", "index": "bigwig" }

    file_ext = 'vcf'
    column_names = [ 'Chrom', 'Pos', 'ID', 'Ref', 'Alt', 'Qual', 'Filter', 'Info', 'Format', 'data' ]

    MetadataElement( name="columns", default=10, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_types", default=['str', 'int', 'str', 'str', 'str', 'int', 'str', 'list', 'str', 'str'], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False )
    MetadataElement( name="viz_filter_cols", desc="Score column for visualization", default=[5], param=metadata.ColumnParameter, optional=True, multiple=True, visible=False )
    MetadataElement( name="sample_names", default=[], desc="Sample names", readonly=True, visible=False, optional=True, no_value=[] )

    def sniff( self, filename ):
        headers = get_headers( filename, '\n', count=1 )
        return headers[0][0].startswith("##fileformat=VCF")

    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return self.make_html_table( dataset, column_names=self.column_names )

    def set_meta( self, dataset, **kwd ):
        super( Vcf, self ).set_meta( dataset, **kwd )
        source = open( dataset.file_name )

        # Skip comments.
        line = None
        for line in source:
            if not line.startswith( '##' ):
                break

        if line and line.startswith( '#' ):
            # Found header line, get sample names.
            dataset.metadata.sample_names = line.split()[ 9: ]

    @staticmethod
    def merge(split_files, output_file):
        stderr_f = tempfile.NamedTemporaryFile(prefix="bam_merge_stderr")
        stderr_name = stderr_f.name
        command = ["bcftools", "concat"] + split_files + ["-o", output_file]
        log.info("Merging vcf files with command [%s]" % " ".join(command))
        exit_code = subprocess.call( args=command, stderr=open( stderr_name, 'wb' ) )
        with open(stderr_name, "rb") as f:
            stderr = f.read().strip()
        # Did merge succeed?
        if exit_code != 0:
            raise Exception("Error merging VCF files: %s" % stderr)

    # Dataproviders
    @dataproviders.decorators.dataprovider_factory( 'genomic-region',
                                                    dataproviders.dataset.GenomicRegionDataProvider.settings )
    def genomic_region_dataprovider( self, dataset, **settings ):
        return dataproviders.dataset.GenomicRegionDataProvider( dataset, 0, 1, 1, **settings )

    @dataproviders.decorators.dataprovider_factory( 'genomic-region-dict',
                                                    dataproviders.dataset.GenomicRegionDataProvider.settings )
    def genomic_region_dict_dataprovider( self, dataset, **settings ):
        settings[ 'named_columns' ] = True
        return self.genomic_region_dataprovider( dataset, **settings )


class Eland( Tabular ):
    """Support for the export.txt.gz file used by Illumina's ELANDv2e aligner"""
    file_ext = '_export.txt.gz'
    MetadataElement( name="columns", default=0, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_types", default=[], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False, no_value=[] )
    MetadataElement( name="comment_lines", default=0, desc="Number of comments", readonly=True, visible=False )
    MetadataElement( name="tiles", default=[], param=metadata.ListParameter, desc="Set of tiles", readonly=True, visible=False, no_value=[] )
    MetadataElement( name="reads", default=[], param=metadata.ListParameter, desc="Set of reads", readonly=True, visible=False, no_value=[] )
    MetadataElement( name="lanes", default=[], param=metadata.ListParameter, desc="Set of lanes", readonly=True, visible=False, no_value=[] )
    MetadataElement( name="barcodes", default=[], param=metadata.ListParameter, desc="Set of barcodes", readonly=True, visible=False, no_value=[] )

    def __init__(self, **kwd):
        """Initialize taxonomy datatype"""
        super( Eland, self ).__init__( **kwd )
        self.column_names = ['MACHINE', 'RUN_NO', 'LANE', 'TILE', 'X', 'Y',
                             'INDEX', 'READ_NO', 'SEQ', 'QUAL', 'CHROM', 'CONTIG',
                             'POSITION', 'STRAND', 'DESC', 'SRAS', 'PRAS', 'PART_CHROM'
                             'PART_CONTIG', 'PART_OFFSET', 'PART_STRAND', 'FILT'
                             ]

    def make_html_table( self, dataset, skipchars=None ):
        """Create HTML table, used for displaying peek"""
        if skipchars is None:
            skipchars = []
        out = ['<table cellspacing="0" cellpadding="3">']
        try:
            # Generate column header
            out.append( '<tr>' )
            for i, name in enumerate( self.column_names ):
                out.append( '<th>%s.%s</th>' % ( str( i + 1 ), name ) )
            # This data type requires at least 11 columns in the data
            if dataset.metadata.columns - len( self.column_names ) > 0:
                for i in range( len( self.column_names ), dataset.metadata.columns ):
                    out.append( '<th>%s</th>' % str( i + 1 ) )
                out.append( '</tr>' )
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception as exc:
            out = "Can't create peek %s" % exc
        return out

    def sniff( self, filename ):
        """
        Determines whether the file is in ELAND export format

        A file in ELAND export format consists of lines of tab-separated data.
        There is no header.

        Rules for sniffing as True::

            - There must be 22 columns on each line
            - LANE, TILEm X, Y, INDEX, READ_NO, SEQ, QUAL, POSITION, *STRAND, FILT must be correct
            - We will only check that up to the first 5 alignments are correctly formatted.
        """
        try:
            fh = compression_utils.get_fileobj(filename, gzip_only=True)
            count = 0
            while True:
                line = fh.readline()
                line = line.strip()
                if not line:
                    break  # EOF
                if line:
                    line_pieces = line.split('\t')
                    if len(line_pieces) != 22:
                        return False
                    try:
                        if long(line_pieces[1]) < 0:
                            raise Exception('Out of range')
                        if long(line_pieces[2]) < 0:
                            raise Exception('Out of range')
                        if long(line_pieces[3]) < 0:
                            raise Exception('Out of range')
                        int(line_pieces[4])
                        int(line_pieces[5])
                        # can get a lot more specific
                    except ValueError:
                        fh.close()
                        return False
                    count += 1
                    if count == 5:
                        break
            if count > 0:
                fh.close()
                return True
        except:
            pass
        fh.close()
        return False

    def set_meta( self, dataset, overwrite=True, skip=None, max_data_lines=5, **kwd ):
        if dataset.has_data():
            dataset_fh = compression_utils.get_fileobj(dataset.file_name, gzip_only=True)
            try:
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
                        line_pieces = line.split('\t')
                        if len(line_pieces) != 22:
                            raise Exception('%s:%d:Corrupt line!' % (dataset.file_name, i))
                        lanes[line_pieces[2]] = 1
                        tiles[line_pieces[3]] = 1
                        barcodes[line_pieces[6]] = 1
                        reads[line_pieces[7]] = 1
                    pass
                dataset.metadata.data_lines = i + 1
            finally:
                dataset_fh.close()
            dataset.metadata.comment_lines = 0
            dataset.metadata.columns = 21
            dataset.metadata.column_types = ['str', 'int', 'int', 'int', 'int', 'int', 'str', 'int', 'str', 'str', 'str', 'str', 'str', 'str', 'str', 'str', 'str', 'str', 'str', 'str', 'str']
            dataset.metadata.lanes = list(lanes.keys())
            dataset.metadata.tiles = ["%04d" % int(t) for t in tiles.keys()]
            dataset.metadata.barcodes = [_ for _ in barcodes.keys() if _ != '0'] + ['NoIndex' for _ in barcodes.keys() if _ == '0']
            dataset.metadata.reads = list(reads.keys())


class ElandMulti( Tabular ):
    file_ext = 'elandmulti'

    def sniff( self, filename ):
        return False


class FeatureLocationIndex( Tabular ):
    """
    An index that stores feature locations in tabular format.
    """
    file_ext = 'fli'
    MetadataElement( name="columns", default=2, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_types", default=['str', 'str'], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False, no_value=[] )


@dataproviders.decorators.has_dataproviders
class BaseCSV( TabularData ):
    """
    Delimiter-separated table data.
    This includes CSV, TSV and other dialects understood by the
    Python 'csv' module https://docs.python.org/2/library/csv.html
    Must be extended to define the dialect to use, strict_width and file_ext.
    See the Python module csv for documentation of dialect settings
    """
    delimiter = ','
    peek_size = 1024  # File chunk used for sniffing CSV dialect
    big_peek_size = 10240  # Large File chunk used for sniffing CSV dialect

    def is_int( self, column_text ):
        try:
            int( column_text )
            return True
        except:
            return False

    def is_float( self, column_text ):
        try:
            float( column_text )
            return True
        except:
            if column_text.strip().lower() == 'na':
                return True  # na is special cased to be a float
            return False

    def guess_type( self, text ):
        if self.is_int(text):
            return 'int'
        if self.is_float(text):
            return 'float'
        else:
            return 'str'

    def sniff( self, filename ):
        """ Return True if if recognizes dialect and header. """
        try:
            # check the dialect works
            reader = csv.reader(open(filename, 'r'), self.dialect)
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
                for data_row in reader:
                    pass

            # Optional: Check Python's csv comes up with a similar dialect
            auto_dialect = csv.Sniffer().sniff(open(filename, 'r').read(self.big_peek_size))
            if (auto_dialect.delimiter != self.dialect.delimiter):
                return False
            if (auto_dialect.quotechar != self.dialect.quotechar):
                return False
            """
            Not checking for other dialect options
            They may be mis detected from just the sample.
            Or not effect the read such as doublequote

            Optional: Check for headers as in the past.
            Note No way around Python's csv calling Sniffer.sniff again.
            Note Without checking the dialect returned by sniff
                  this test may be checking the wrong dialect.
            """
            if not csv.Sniffer().has_header(open(filename, 'r').read(self.big_peek_size)):
                return False
            return True
        except:
            # Not readable by Python's csv using this dialect
            return False

    def set_meta( self, dataset, **kwd ):
        with open(dataset.file_name, 'r') as csvfile:
            # Parse file with the correct dialect
            reader = csv.reader(csvfile, self.dialect)
            data_row = None
            header_row = None
            try:
                header_row = next(reader)
                data_row = next(reader)
                for row in reader:
                    pass
            except csv.Error as e:
                raise Exception('CSV reader error - line %d: %s' % (reader.line_num, e))

            # Guess column types
            column_types = []
            for cell in data_row:
                column_types.append(self.guess_type(cell))

            # Set metadata
            dataset.metadata.data_lines = reader.line_num - 1
            dataset.metadata.comment_lines = 1
            dataset.metadata.column_types = column_types
            dataset.metadata.columns = max( len( header_row ), len( data_row ) )
            dataset.metadata.column_names = header_row
            dataset.metadata.delimiter = reader.dialect.delimiter


@dataproviders.decorators.has_dataproviders
class CSV( BaseCSV ):
    """
    Comma-separated table data.
    Only sniffs comma-separated files with at least 2 rows and 2 columns.
    """
    file_ext = 'csv'
    dialect = csv.excel  # This is the default
    strict_width = False  # Previous csv type did not check column width


@dataproviders.decorators.has_dataproviders
class TSV( BaseCSV ):
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
    file_ext = 'tsv'
    dialect = csv.excel_tab
    strict_width = True  # Leave files with different width to tabular


class ConnectivityTable( Tabular ):
    edam_format = "format_3309"
    file_ext = "ct"

    header_regexp = re.compile( "^[0-9]+" + "(?:\t|[ ]+)" + ".*?" + "(?:ENERGY|energy|dG)" + "[ \t].*?=")
    structure_regexp = re.compile( "^[0-9]+" + "(?:\t|[ ]+)" + "[ACGTURYKMSWBDHVN]+" + "(?:\t|[ ]+)" + "[^\t]+" + "(?:\t|[ ]+)" + "[^\t]+" + "(?:\t|[ ]+)" + "[^\t]+" + "(?:\t|[ ]+)" + "[^\t]+")

    def __init__(self, **kwd):
        super( ConnectivityTable, self ).__init__( **kwd )
        self.columns = 6
        self.column_names = ['base_index', 'base', 'neighbor_left', 'neighbor_right', 'partner', 'natural_numbering']
        self.column_types = ['int', 'str', 'int', 'int', 'int', 'int']

    def set_meta( self, dataset, **kwd ):
        data_lines = 0

        for line in open( dataset.file_name ):
            data_lines += 1

        dataset.metadata.data_lines = data_lines

    def sniff(self, filename):
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

        try:
            with open( filename ) as handle:
                for line in handle:
                    line = line.strip()

                    if len(line) > 0:
                        if i == 0:
                            if not self.header_regexp.match(line):
                                return False
                            else:
                                length = int(re.split('\W+', line, 1)[0])
                        else:
                            if not self.structure_regexp.match(line.upper()):
                                return False
                            else:
                                if j != int(re.split('\W+', line, 1)[0]):
                                    return False
                                elif j == length:                       # Last line of first sequence has been recheached
                                    return True
                                else:
                                    j += 1
                        i += 1
            return False
        except:
            return False

    def get_chunk(self, trans, dataset, chunk):
        ck_index = int(chunk)
        f = open(dataset.file_name)
        f.seek(ck_index * trans.app.config.display_chunk_size)
        # If we aren't at the start of the file, seek to next newline.  Do this better eventually.
        if f.tell() != 0:
            cursor = f.read(1)
            while cursor and cursor != '\n':
                cursor = f.read(1)
        ck_data = f.read(trans.app.config.display_chunk_size)
        cursor = f.read(1)
        while cursor and ck_data[-1] != '\n':
            ck_data += cursor
            cursor = f.read(1)

        # The ConnectivityTable format has several derivatives of which one is delimited by (multiple) spaces.
        # By converting these spaces back to tabs, chucks can still be interpreted by tab delimited file parsers
        ck_data_header, ck_data_body = ck_data.split('\n', 1)
        ck_data_header = re.sub('^([0-9]+)[ ]+', r'\1\t', ck_data_header)
        ck_data_body = re.sub('\n[ \t]+', '\n', ck_data_body)
        ck_data_body = re.sub('[ ]+', '\t', ck_data_body)

        return dumps( { 'ck_data': util.unicodify(ck_data_header + "\n" + ck_data_body ), 'ck_index': ck_index + 1 } )
