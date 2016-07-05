"""
Migration script to add 'name' attribute to the JSON dict which describes
a form definition field and the form values in the database. In the 'form_values'
table, the 'content' column is now a JSON dict instead of a list.
"""
from __future__ import print_function

import datetime
import logging
import sys
from json import loads, dumps

from sqlalchemy import MetaData, Table

from galaxy.model.custom_types import _sniffnfix_pg9_hex

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    try:
        Table( "form_definition", metadata, autoload=True )
    except Exception as e:
        log.debug( "Loading 'form_definition' table failed: %s" % str( e ) )
    try:
        Table( "form_values", metadata, autoload=True )
    except Exception as e:
        log.debug( "Loading 'form_values' table failed: %s" % str( e ) )

    def get_value(lst, index):
        try:
            return str(lst[index]).replace("'", "''")
        except IndexError:
            return ''
    # Go through the entire table and add a 'name' attribute for each field
    # in the list of fields for each form definition
    cmd = "SELECT f.id, f.fields FROM form_definition AS f"
    result = migrate_engine.execute( cmd )
    for row in result:
        form_definition_id = row[0]
        fields = str( row[1] )
        if not fields.strip():
            continue
        fields_list = loads( _sniffnfix_pg9_hex( fields ) )
        if len( fields_list ):
            for index, field in enumerate( fields_list ):
                field[ 'name' ] = 'field_%i' % index
                field[ 'helptext' ] = field[ 'helptext' ].replace("'", "''").replace('"', "")
                field[ 'label' ] = field[ 'label' ].replace("'", "''")
            fields_json = dumps( fields_list )
            if migrate_engine.name == 'mysql':
                cmd = "UPDATE form_definition AS f SET f.fields='%s' WHERE f.id=%i" % ( fields_json, form_definition_id )
            else:
                cmd = "UPDATE form_definition SET fields='%s' WHERE id=%i" % ( fields_json, form_definition_id )
            migrate_engine.execute( cmd )
    # replace the values list in the content field of the form_values table with a name:value dict
    cmd = "SELECT form_values.id, form_values.content, form_definition.fields" \
          " FROM form_values, form_definition" \
          " WHERE form_values.form_definition_id=form_definition.id" \
          " ORDER BY form_values.id ASC"
    result = migrate_engine.execute( cmd )
    for row in result:
        form_values_id = int( row[0] )
        if not str( row[1] ).strip():
            continue
        row1 = str(row[1]).replace('\n', '').replace('\r', '')
        values_list = loads( str( row1 ).strip() )
        if not str( row[2] ).strip():
            continue
        fields_list = loads( str( row[2] ).strip() )
        if fields_list and isinstance(values_list, list):
            values_dict = {}
            for field_index, field in enumerate( fields_list ):
                field_name = field[ 'name' ]
                values_dict[ field_name ] = get_value(values_list, field_index )
            cmd = "UPDATE form_values SET content='%s' WHERE id=%i" % ( dumps( values_dict ), form_values_id )
            migrate_engine.execute( cmd )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        Table( "form_definition", metadata, autoload=True )
    except Exception as e:
        log.debug( "Loading 'form_definition' table failed: %s" % str( e ) )
    try:
        Table( "form_values", metadata, autoload=True )
    except Exception as e:
        log.debug( "Loading 'form_values' table failed: %s" % str( e ) )
    # remove the name attribute in the content column JSON dict in the form_values table
    # and restore it to a list of values
    cmd = "SELECT form_values.id, form_values.content, form_definition.fields" \
          " FROM form_values, form_definition" \
          " WHERE form_values.form_definition_id=form_definition.id" \
          " ORDER BY form_values.id ASC"
    result = migrate_engine.execute( cmd )
    for row in result:
        form_values_id = int( row[0] )
        if not str( row[1] ).strip():
            continue
        values_dict = loads( str( row[1] ) )
        if not str( row[2] ).strip():
            continue
        fields_list = loads( str( row[2] ) )
        if fields_list:
            values_list = []
            for field_index, field in enumerate( fields_list ):
                field_name = field[ 'name' ]
                field_value = values_dict[ field_name ]
                values_list.append( field_value )
            cmd = "UPDATE form_values SET content='%s' WHERE id=%i" % ( dumps( values_list ), form_values_id )
            migrate_engine.execute( cmd )
    # remove name attribute from the field column of the form_definition table
    cmd = "SELECT f.id, f.fields FROM form_definition AS f"
    result = migrate_engine.execute( cmd )
    for row in result:
        form_definition_id = row[0]
        fields = str( row[1] )
        if not fields.strip():
            continue
        fields_list = loads( _sniffnfix_pg9_hex( fields ) )
        if len( fields_list ):
            for index, field in enumerate( fields_list ):
                if 'name' in field:
                    del field[ 'name' ]
            if migrate_engine.name == 'mysql':
                cmd = "UPDATE form_definition AS f SET f.fields='%s' WHERE f.id=%i" % ( dumps( fields_list ), form_definition_id )
            else:
                cmd = "UPDATE form_definition SET fields='%s' WHERE id=%i" % ( dumps( fields_list ), form_definition_id )
        migrate_engine.execute( cmd )
