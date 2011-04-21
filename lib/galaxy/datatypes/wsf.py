"""
SnpFile datatype
"""

import data
from galaxy import util
from galaxy.datatypes.sniff import *
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement

snp_type_dict = {}
snp_required_columns = ('scaffold', 'pos')
snp_required_column_count = len( snp_required_columns )
snp_required_index = {}
snp_column_set = set( snp_required_columns )

""" check for duplicate required columns """
for i, column in enumerate( snp_required_columns ):
    assert column not in snp_required_index, \
        "duplicate required column: '%s'" % column
    snp_required_index[column] = i

def add_type( type_list=None, name_list=None, species=None, comment=None ):
    type_list_len = len( type_list )
    name_list_len = len( name_list )
    assert type_list_len == name_list_len, \
        "type length mismatch: '%s' has %d names and %d types" % ( comment, name_list_len, type_list_len )
    for column in snp_required_columns:
        assert column in name_list, \
            "type missing required column: '%s' missing %s column" % ( comment, column )
    type_key = tuple( type_list )
    type_data = tuple( [tuple( name_list ), species, comment] )
    if type_list_len in snp_type_dict:
        assert type_key not in snp_type_dict[type_list_len], \
            "type collision: column count and types for '%s' and '%s' match" % ( comment, snp_type_dict[type_list_len][type_key][2] )
        snp_type_dict[type_list_len][type_key] = type_data
    else:
        snp_type_dict[type_list_len] = { type_key:type_data }
    snp_column_set.update( name_list )

""" add our types """
add_type(
    species='tasmanian_devil',
    comment='tasmanian devil coding snps',
    type_list=['str', 'int', 'str', 'str', 'str', 'str', 'str', 'int', 'str', 'int', 'int', 'int', 'int', 'int', 'int', 'int', 'int', 'int', 'str', 'int', 'float', 'int'],
    name_list=['scaffold', 'pos', 'A', 'B', 'aa1', 'aa2', 'ref', 'rPos', 'rAA', '#CA', '#CB', 'CQ', '#SA', '#SB', 'SQ', '#TA', '#TB', 'GQ', 'pair', 'sep', 'prim', '#RFLP']
)
add_type(
    species='tasmanian_devil',
    comment='tasmanian devil noncoding snps',
    type_list=['str', 'int', 'str', 'str', 'int', 'int', 'int', 'int', 'int', 'int', 'int', 'int', 'int', 'str', 'int', 'float', 'int'],
    name_list=['scaffold', 'pos', 'A', 'B', '#CA', '#CB', 'CQ', '#SA', '#SB', 'SQ', '#TA', '#TB', 'GQ', 'pair', 'sep', 'prim', '#RFLP']
)
add_type(
    species='bighorn',
    comment='bighorn sheep coding snps',
    type_list=['str', 'int', 'str', 'str', 'str', 'str', 'str', 'int', 'str', 'str', 'int', 'int', 'int', 'int', 'int', 'int', 'str', 'int', 'float', 'float', 'float', 'int'],
    name_list=['scaffold', 'pos', 'A', 'B', 'aa1', 'aa2', 'ref', 'rPos', 'rNuc', 'rAA', '#desA', '#desB', 'desQ', '#mtA', '#mtB', 'mtQ', 'pair', 'sep', 'Fst', 'cons', 'prim', '#RFLP']
)
add_type(
    species='bighorn',
    comment='bighorn sheep noncoding snps',
    type_list=['str', 'int', 'str', 'str', 'str', 'int', 'str', 'int', 'int', 'int', 'int', 'int', 'int', 'str', 'int', 'float', 'float', 'float', 'int'],
    name_list=['scaffold', 'pos', 'A', 'B', 'ref', 'rPos', 'rNuc', '#desA', '#desB', 'desQ', '#mtA', '#mtB', 'mtQ', 'pair', 'sep', 'Fst', 'cons', 'prim', '#RFLP']
)


class SnpFile( Tabular ):
    """ Webb's SNP file format """
    file_ext = 'wsf'

    """ add metadata elements """
    MetadataElement( name="species", desc="species", readonly=True, no_value=None )
    for name in sorted( snp_column_set ):
        default = 0
        desc = "%s column" % name
        optional = False
        if name in snp_required_columns:
            default = snp_required_index[name] + 1
            optional = True
        MetadataElement( name=name, default=default, desc=desc, param=metadata.ColumnParameter, optional=optional )

    def set_meta( self, dataset, overwrite = True, **kwd ):
        Tabular.set_meta( self, dataset, overwrite = overwrite, **kwd )
        if dataset.has_data():
            if dataset.metadata.columns in snp_type_dict:
                type_key = tuple( dataset.metadata.column_types )
                if type_key in snp_type_dict[dataset.metadata.columns]:
                    name_list, dataset.metadata.species, comment = snp_type_dict[dataset.metadata.columns][type_key]
                    for i, name in enumerate( name_list[snp_required_column_count:] ):
                        setattr( dataset.metadata, name, snp_required_column_count + i + 1 )

    def make_html_table(self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        try:
            out.append( '<tr>' )
            col_names = range( 0, dataset.metadata.columns + 1 )
            for name, spec in dataset.metadata.spec.items():
                if isinstance( spec.param, metadata.ColumnParameter ):
                    col = getattr( dataset.metadata, name )
                    if col > 0 and col_names[col] == col:
                        col_names[col] = name
            for i, name in enumerate( col_names[1:] ):
                if col_names[ i + 1 ] == i + 1:
                    out.append( '<th>%d.</th>' % ( i + 1 ) )
                else:
                    out.append( '<th>%d.%s</th>' % ( i + 1, name ) )
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % exc
        return out

