"""
Manage tool data tables, which store (at the application level) data that is
used by tools, for example in the generation of dynamic options. Tables are
loaded and stored by names which tools use to refer to them. This allows
users to configure data tables for a local Galaxy instance without needing
to modify the tool configurations.
"""

import logging
import os
import os.path
import shutil
import tempfile

from galaxy import util

log = logging.getLogger( __name__ )


class ToolDataTableManager( object ):
    """Manages a collection of tool data tables"""

    def __init__( self, tool_data_path, config_filename=None ):
        self.tool_data_path = tool_data_path
        # This stores all defined data table entries from both the tool_data_table_conf.xml file and the shed_tool_data_table_conf.xml file
        # at server startup. If tool shed repositories are installed that contain a valid file named tool_data_table_conf.xml.sample, entries
        # from that file are inserted into this dict at the time of installation.
        self.data_tables = {}
        # Store config elements for on-the-fly persistence to the defined shed_tool_data_table_config file name.
        self.shed_data_table_elems = []
        self.data_table_elem_names = []
        if config_filename:
            self.load_from_config_file( config_filename, self.tool_data_path, from_shed_config=False )

    def __getitem__( self, key ):
        return self.data_tables.__getitem__( key )

    def __contains__( self, key ):
        return self.data_tables.__contains__( key )

    def get( self, name, default=None ):
        try:
            return self[ name ]
        except KeyError:
            return default

    def load_from_config_file( self, config_filename, tool_data_path, from_shed_config=False ):
        """
        This method is called under 3 conditions:

        1. When the ToolDataTableManager is initialized (see __init__ above).
        2. Just after the ToolDataTableManager is initialized and the additional entries defined by shed_tool_data_table_conf.xml
           are being loaded into the ToolDataTableManager.data_tables.
        3. When a tool shed repository that includes a tool_data_table_conf.xml.sample file is being installed into a local
           Galaxy instance.  In this case, we have 2 entry types to handle, files whose root tag is <tables>, for example:
        """
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        table_elems = []
        for table_elem in root.findall( 'table' ):
            type = table_elem.get( 'type', 'tabular' )
            assert type in tool_data_table_types, "Unknown data table type '%s'" % type
            table_elems.append( table_elem )
            table_elem_name = table_elem.get( 'name', None )
            if table_elem_name and table_elem_name not in self.data_table_elem_names:
                self.data_table_elem_names.append( table_elem_name )
                if from_shed_config:
                    self.shed_data_table_elems.append( table_elem )
            table = tool_data_table_types[ type ]( table_elem, tool_data_path, from_shed_config)
            if table.name not in self.data_tables:
                self.data_tables[ table.name ] = table
                log.debug( "Loaded tool data table '%s'", table.name )
            else:
                for table_row in table.data:
                    # FIXME: This does not account for an entry with the same unique build ID, but a different path.
                    if table_row not in self.data_tables[ table.name ].data:
                        self.data_tables[ table.name ].data.append( table_row )
        return table_elems

    def add_new_entries_from_config_file( self, config_filename, tool_data_path, shed_tool_data_table_config, persist=False ):
        """
        This method is called when a tool shed repository that includes a tool_data_table_conf.xml.sample file is being
        installed into a local galaxy instance.  We have 2 cases to handle, files whose root tag is <tables>, for example::

            <tables>
                <!-- Location of Tmap files -->
                <table name="tmap_indexes" comment_char="#">
                    <columns>value, dbkey, name, path</columns>
                    <file path="tool-data/tmap_index.loc" />
                </table>
            </tables>

        and files whose root tag is <table>, for example::

            <!-- Location of Tmap files -->
            <table name="tmap_indexes" comment_char="#">
                <columns>value, dbkey, name, path</columns>
                <file path="tool-data/tmap_index.loc" />
            </table>

        """
        error_message = ''
        table_elems = []
        try:
            tree = util.parse_xml( config_filename )
            root = tree.getroot()
        except Exception, e:
            error_message = 'Error attempting to parse file %s: %s' % ( str( os.path.split( config_filename )[ 1 ] ), str( e ) )
            log.debug( error_message )
            return table_elems, error_message
        # Make a copy of the current list of data_table_elem_names so we can persist later if changes to the config file are necessary.
        original_data_table_elem_names = [ name for name in self.data_table_elem_names ]
        if root.tag == 'tables':
            table_elems = self.load_from_config_file( config_filename=config_filename,
                                                      tool_data_path=tool_data_path,
                                                      from_shed_config=True )
        else:
            type = root.get( 'type', 'tabular' )
            assert type in tool_data_table_types, "Unknown data table type '%s'" % type
            table_elems.append( root )
            table_elem_name = root.get( 'name', None )
            if table_elem_name and table_elem_name not in self.data_table_elem_names:
                self.data_table_elem_names.append( table_elem_name )
                self.shed_data_table_elems.append( root )
            table = tool_data_table_types[ type ]( root, tool_data_path )
            if table.name not in self.data_tables:
                self.data_tables[ table.name ] = table
                log.debug( "Added new tool data table '%s'", table.name )
        if persist and self.data_table_elem_names != original_data_table_elem_names:
            # Persist Galaxy's version of the changed tool_data_table_conf.xml file.
            self.to_xml_file( shed_tool_data_table_config )
        return table_elems, error_message

    def to_xml_file( self, shed_tool_data_table_config ):
        """Write the current in-memory version of the shed_tool_data_table_conf.xml file to disk."""
        full_path = os.path.abspath( shed_tool_data_table_config )
        fd, filename = tempfile.mkstemp()
        os.write( fd, '<?xml version="1.0"?>\n' )
        os.write( fd, '<tables>\n' )
        for elem in self.shed_data_table_elems:
            os.write( fd, '%s' % util.xml_to_string( elem ) )
        os.write( fd, '</tables>\n' )
        os.close( fd )
        shutil.move( filename, full_path )
        os.chmod( full_path, 0644 )


class ToolDataTable( object ):

    def __init__( self, config_element, tool_data_path, from_shed_config = False):
        self.name = config_element.get( 'name' )
        self.comment_char = config_element.get( 'comment_char' )
        self.empty_field_value = config_element.get( 'empty_field_value', '' )
        self.empty_field_values = {}
        for file_elem in config_element.findall( 'file' ):
            # There should only be one file_elem.
            if 'path' in file_elem.attrib:
                tool_data_file_path = file_elem.get( 'path' )
                self.tool_data_file = os.path.split( tool_data_file_path )[1]
            else:
                self.tool_data_file = None
        self.tool_data_path = tool_data_path
        self.missing_index_file = None
        # increment this variable any time a new entry is added, or when the table is totally reloaded
        # This value has no external meaning, and does not represent an abstract version of the underlying data
        self._loaded_content_version = 1

    def get_empty_field_by_name( self, name ):
        return self.empty_field_values.get( name, self.empty_field_value )
    
    def _add_entry( self, entry, persist=False, persist_on_error=False, **kwd ):
        raise NotImplementedError( "Abstract method" )
    
    def add_entry( self, entry, persist=False, persist_on_error=False, **kwd ):
        self._add_entry( entry, persist=persist, persist_on_error=persist_on_error, **kwd )
        self._loaded_content_version += 1
        return self._loaded_content_version
    
    def is_current_version( self, other_version ):
        return self._loaded_content_version == other_version

class TabularToolDataTable( ToolDataTable ):
    """
    Data stored in a tabular / separated value format on disk, allows multiple
    files to be merged but all must have the same column definitions::

        <table type="tabular" name="test">
            <column name='...' index = '...' />
            <file path="..." />
            <file path="..." />
        </table>

    """

    type_key = 'tabular'

    def __init__( self, config_element, tool_data_path, from_shed_config = False):
        super( TabularToolDataTable, self ).__init__( config_element, tool_data_path, from_shed_config)
        self.configure_and_load( config_element, tool_data_path, from_shed_config)

    def configure_and_load( self, config_element, tool_data_path, from_shed_config = False):
        """
        Configure and load table from an XML element.
        """
        self.separator = config_element.get( 'separator', '\t' )
        self.comment_char = config_element.get( 'comment_char', '#' )
        # Configure columns
        self.parse_column_spec( config_element )
        # Read every file
        all_rows = []
        for file_element in config_element.findall( 'file' ):
            found = False
            if tool_data_path and from_shed_config:
                # Must identify with from_shed_config as well, because the
                # regular galaxy app has and uses tool_data_path.
                # We're loading a tool in the tool shed, so we cannot use the Galaxy tool-data
                # directory which is hard-coded into the tool_data_table_conf.xml entries.
                filepath = file_element.get( 'path' )
                filename = os.path.split( filepath )[ 1 ]
                filename = os.path.join( tool_data_path, filename )
            else:
               filename = file_element.get( 'path' )
            if os.path.exists( filename ):
                found = True
                all_rows.extend( self.parse_file_fields( open( filename ) ) )
                self.filename = filename
            else:
                # Since the path attribute can include a hard-coded path to a specific directory
                # (e.g., <file path="tool-data/cg_crr_files.loc" />) which may not be the same value
                # as self.tool_data_path, we'll parse the path to get the filename and see if it is
                # in self.tool_data_path.
                file_path, file_name = os.path.split( filename )
                if file_path and file_path != self.tool_data_path:
                    corrected_filename = os.path.join( self.tool_data_path, file_name )
                    if os.path.exists( corrected_filename ):
                        found = True
                        all_rows.extend( self.parse_file_fields( open( corrected_filename ) ) )
                        self.filename = corrected_filename
            if not found:
                self.missing_index_file = filename
                log.warn( "Cannot find index file '%s' for tool data table '%s'" % ( filename, self.name ) )
        self.data = all_rows

    def handle_found_index_file( self, filename ):
        self.missing_index_file = None
        self.data.extend( self.parse_file_fields( open( filename ) ) )

    def get_fields( self ):
        return self.data
    
    def get_version_fields( self ):
        return ( self._loaded_content_version, self.data )

    def parse_column_spec( self, config_element ):
        """
        Parse column definitions, which can either be a set of 'column' elements
        with a name and index (as in dynamic options config), or a shorthand
        comma separated list of names in order as the text of a 'column_names'
        element.

        A column named 'value' is required.
        """
        self.columns = {}
        if config_element.find( 'columns' ) is not None:
            column_names = util.xml_text( config_element.find( 'columns' ) )
            column_names = [ n.strip() for n in column_names.split( ',' ) ]
            for index, name in enumerate( column_names ):
                self.columns[ name ] = index
                self.largest_index = index
        else:
            for column_elem in config_element.findall( 'column' ):
                name = column_elem.get( 'name', None )
                assert name is not None, "Required 'name' attribute missing from column def"
                index = column_elem.get( 'index', None )
                assert index is not None, "Required 'index' attribute missing from column def"
                index = int( index )
                self.columns[name] = index
                if index > self.largest_index:
                    self.largest_index = index
                empty_field_value = column_elem.get( 'empty_field_value', None )
                if empty_field_value is not None:
                    self.empty_field_values[ name ] = empty_field_value
        assert 'value' in self.columns, "Required 'value' column missing from column def"
        if 'name' not in self.columns:
            self.columns['name'] = self.columns['value']

    def parse_file_fields( self, reader ):
        """
        Parse separated lines from file and return a list of tuples.

        TODO: Allow named access to fields using the column names.
        """
        separator_char = (lambda c: '<TAB>' if c == '\t' else c)(self.separator)

        rval = []
        for i, line in enumerate( reader ):
            if line.lstrip().startswith( self.comment_char ):
                continue
            line = line.rstrip( "\n\r" )
            if line:
                fields = line.split( self.separator )
                if self.largest_index < len( fields ):
                    rval.append( fields )
                else:
                    log.warn( "Line %i in tool data table '%s' is invalid (HINT: "
                              "'%s' characters must be used to separate fields):\n%s"
                              % ( ( i + 1 ), self.name, separator_char, line ) )
        return rval

    def get_column_name_list( self ):
        rval = []
        for i in range( self.largest_index + 1 ):
            found_column = False
            for name, index in self.columns.iteritems():
                if index == i:
                    if not found_column:
                        rval.append( name )
                    elif name == 'value':
                        #the column named 'value' always has priority over other named columns
                        rval[ -1 ] = name
                    found_column = True
            if not found_column:
                rval.append( None )
        return rval

    def get_entry( self, query_attr, query_val, return_attr, default=None ):
        """
        Returns table entry associated with a col/val pair.
        """
        query_col = self.columns.get( query_attr, None )
        if query_col is None:
            return default
        return_col = self.columns.get( return_attr, None )
        if return_col is None:
            return default
        rval = default
        # Look for table entry.
        for fields in self.data:
            if fields[ query_col ] == query_val:
                rval = fields[ return_col ]
                break
        return rval
    
    def _add_entry( self, entry, persist=False, persist_on_error=False, **kwd ):
        #accepts dict or list of columns
        if isinstance( entry, dict ):
            fields = []
            for column_name in self.get_column_name_list():
                if column_name not in entry:
                    log.debug( "Using default column value for column '%s' when adding data table entry (%s) to table '%s'.", column_name, entry, self.name )
                    field_value = self.get_empty_field_by_name( column_name )
                else:
                    field_value = entry[ column_name ]
                fields.append( field_value )
        else:
            fields = entry
        if self.largest_index < len( fields ):
            fields = self._replace_field_separators( fields )
            self.data.append( fields )
            field_len_error = False
        else:
            log.error( "Attempted to add fields (%s) to data table '%s', but there were not enough fields specified ( %i < %i ).", fields, self.name, len( fields ), self.largest_index + 1 )
            field_len_error = True
        if persist and ( not field_len_error or persist_on_error ):
            #FIXME: Need to lock these files for editing
            try:
                data_table_fh = open( self.filename, 'r+b' )
            except IOError, e:
                log.warning( 'Error opening data table file (%s) with r+b, assuming file does not exist and will open as wb: %s', self.filename, e )
                data_table_fh = open( self.filename, 'wb' )
            if os.stat( self.filename )[6] != 0:
                # ensure last existing line ends with new line
                data_table_fh.seek( -1, 2 ) #last char in file
                last_char = data_table_fh.read( 1 )
                if last_char not in [ '\n', '\r' ]:
                    data_table_fh.write( '\n' )
            data_table_fh.write( "%s\n" % ( self.separator.join( fields ) ) )
        return not field_len_error
    
    def _replace_field_separators( self, fields, separator=None, replace=None, comment_char=None ):
        #make sure none of the fields contain separator
        #make sure separator replace is different from comment_char,
        #due to possible leading replace
        if separator is None:
            separator = self.separator
        if replace is None:
            if separator == " ":
                if comment_char == "\t":
                    replace = "_"
                else:
                    replace = "\t"
            else:
                if comment_char == " ":
                    replace = "_"
                else:
                    replace = " "
        return map( lambda x: x.replace( separator, replace ), fields )
    
# Registry of tool data types by type_key
tool_data_table_types = dict( [ ( cls.type_key, cls ) for cls in [ TabularToolDataTable ] ] )
