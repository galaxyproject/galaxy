"""
SnpFile datatype
"""

import re
import data
from galaxy import util
from galaxy.datatypes.sniff import *
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement

class SnpFile( Tabular ):
    """ Webb's SNP file format """
    file_ext = 'wsf'
    species_regex = re.compile('species=(\S+)')
    MetadataElement( name="species", desc="species", default='', no_value='', visible=False, readonly=True )
    MetadataElement( name="scaffold", desc="scaffold column", param=metadata.ColumnParameter, default=0 )
    MetadataElement( name="pos", desc="pos column", param=metadata.ColumnParameter, default=0 )
    MetadataElement( name="ref", desc="ref column", param=metadata.ColumnParameter, default=0 )
    MetadataElement( name="rPos", desc="rPos column", param=metadata.ColumnParameter, default=0 )
    MetadataElement( name="labels", desc="Number of labels", default=0, no_value=0, visible=False, readonly=True )
    MetadataElement( name="label_for_column", desc="Mapping from column to label", default=[], no_value=[], visible=False, readonly=True )
    MetadataElement( name="columns_with_label", desc="Mapping from label to columns", param=metadata.DictParameter, default={}, no_value={}, visible=False, readonly=True )
    MetadataElement( name="column_headers", desc="Column headers", default=[], no_value=[], visible=False, readonly=True )


    def set_meta( self, dataset, overwrite = True, **kwd ):
        Tabular.set_meta( self, dataset, overwrite=overwrite, max_data_lines=None, **kwd )
        # these two if statements work around a potential bug in metadata.py
        if dataset.metadata.labels is None or dataset.metadata.labels == dataset.metadata.spec['labels'].no_value:
            self._set_column_labels_metadata( dataset )
        if dataset.metadata.column_headers is None or dataset.metadata.column_headers == dataset.metadata.spec['column_headers'].no_value:
            self._set_column_headers_metadata( dataset )
        self._set_columnParameter_metadata( dataset )


    def _set_column_labels_metadata( self, dataset ):
        def build_map_from_label_to_comma_separated_column_list( labels ):
            map = {}
            for index, label in enumerate( labels ):
                map.setdefault( label, [] ).append( index )

            for label in map:
                map[label] = ','.join( [ str( index + 1 ) for index in map[label] ] )
            return map

        def strip_list_elements( list ):
            return [ element.strip() for element in list ]

        def initial_comment_lines_of_dataset( dataset ):
            comment_lines = []
            if dataset.has_data():
                try:
                    fh = open( dataset.file_name, 'r' )
                    for line in fh:
                        if not line.startswith('#'):
                            break
                        line = line[1:]
                        line = line.rstrip( '\r\n' )
                        if line:
                            comment_lines.append( line )
                    fh.close()
                except:
                    pass
            return comment_lines

        def set_metadata_from_comment_lines( dataset ):
            labels = []
            comment_lines = initial_comment_lines_of_dataset( dataset )

            for line in comment_lines:
                match = SnpFile.species_regex.match( line )
                if match:
                    dataset.metadata.species = match.group(1)
                    continue
                elems = line.split( '\t' )
                if len(elems) > 1:
                    labels = strip_list_elements( elems )

            dataset.metadata.labels = len( labels )
            dataset.metadata.label_for_column = labels[:]
            if labels:
                dataset.metadata.label_for_column.insert(0, '')
                dataset.metadata.columns_with_label = build_map_from_label_to_comma_separated_column_list( labels )

        set_metadata_from_comment_lines( dataset )


    def _set_column_headers_metadata( self, dataset ):
        if dataset.metadata.labels < dataset.metadata.columns:
            column_headers = dataset.metadata.label_for_column[1:] + [ '' ] * ( dataset.metadata.columns - dataset.metadata.labels )
        else:
            column_headers = dataset.metadata.label_for_column[1:dataset.metadata.columns+1]

        dataset.metadata.column_headers = column_headers


    def _set_columnParameter_metadata( self, dataset ):
        def unique_column_number_or_zero( string ):
            try:
                val = int( string )
            except:
                val = 0
            return val

        for name in self._metadata_columnParameter_names( dataset ):
            if name in dataset.metadata.columns_with_label:
                if dataset.metadata.columns_with_label[name]:
                    column = unique_column_number_or_zero( dataset.metadata.columns_with_label[name] )
                    if column:
                        setattr( dataset.metadata, name, column )


    def _metadata_columnParameter_names( self, dataset ):
        for name, spec in dataset.metadata.spec.items():
            if isinstance( spec.param, metadata.ColumnParameter ):
                yield name


    def set_peek( self, dataset, line_count=None, is_multi_byte=False ):
        super(Tabular, self).set_peek( dataset, line_count=line_count, is_multi_byte=is_multi_byte, skipchars=[ '#' ])


    def make_html_table( self, dataset, skipchars=[ '#' ] ):
        """Create HTML table, used for displaying peek"""
        def table_header_values( dataset ):
            headers = dataset.metadata.column_headers[:]
            for name in self._metadata_columnParameter_names( dataset ):
                col = getattr( dataset.metadata, name )
                assert col <= dataset.metadata.columns, Exception( 'ColumnParameter %s %d > %d columns for dataset %s.' % ( name, col, dataset.metadata.columns, dataset.id ) )
                if col > 0:
                    headers[ col - 1 ] = name
            return headers

        def table_headers( dataset ):
            out = [ '<tr>' ]
            headers = table_header_values( dataset )
            for index, header in enumerate( headers ):
                column = index + 1
                if header:
                    out.append( "<th>%d.%s</th>" % ( column, header ) )
                else:
                    out.append( "<th>%d.</th>" % column )
            out.append( '</tr>' )
            return out

        try:
            out = ['<table cellspacing="0" cellpadding="3">']
            out.extend( table_headers( dataset ) )
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % exc
        return out
