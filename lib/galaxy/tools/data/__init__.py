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
from galaxy.util.odict import odict

log = logging.getLogger( __name__ )

DEFAULT_TABLE_TYPE = 'tabular'

class ToolDataTableManager( object ):
    """Manages a collection of tool data tables"""

    def __init__( self, tool_data_path, config_filename=None ):
        self.tool_data_path = tool_data_path
        # This stores all defined data table entries from both the tool_data_table_conf.xml file and the shed_tool_data_table_conf.xml file
        # at server startup. If tool shed repositories are installed that contain a valid file named tool_data_table_conf.xml.sample, entries
        # from that file are inserted into this dict at the time of installation.
        self.data_tables = {}
        if config_filename:
            self.load_from_config_file( config_filename, self.tool_data_path, from_shed_config=False )

    def __getitem__( self, key ):
        return self.data_tables.__getitem__( key )

    def __setitem__( self, key, value ):
        return self.data_tables.__setitem__( key, value )

    def __contains__( self, key ):
        return self.data_tables.__contains__( key )

    def get( self, name, default=None ):
        try:
            return self[ name ]
        except KeyError:
            return default

    def set( self, name, value ):
        self[ name ] = value

    def get_tables( self ):
        return self.data_tables

    def load_from_config_file( self, config_filename, tool_data_path, from_shed_config=False ):
        """
        This method is called under 3 conditions:

        1. When the ToolDataTableManager is initialized (see __init__ above).
        2. Just after the ToolDataTableManager is initialized and the additional entries defined by shed_tool_data_table_conf.xml
           are being loaded into the ToolDataTableManager.data_tables.
        3. When a tool shed repository that includes a tool_data_table_conf.xml.sample file is being installed into a local
           Galaxy instance.  In this case, we have 2 entry types to handle, files whose root tag is <tables>, for example:
        """
        table_elems = []
        if not isinstance( config_filename, list ):
            config_filename = [ config_filename ]
        for filename in config_filename:
            tree = util.parse_xml( filename )
            root = tree.getroot()
            for table_elem in root.findall( 'table' ):
                table = ToolDataTable.from_elem( table_elem, tool_data_path, from_shed_config )
                table_elems.append( table_elem )
                if table.name not in self.data_tables:
                    self.data_tables[ table.name ] = table
                    log.debug( "Loaded tool data table '%s'", table.name )
                else:
                    log.debug( "Loading another instance of data table '%s', attempting to merge content.", table.name )
                    self.data_tables[ table.name ].merge_tool_data_table( table, allow_duplicates=False ) #only merge content, do not persist to disk, do not allow duplicate rows when merging
                    # FIXME: This does not account for an entry with the same unique build ID, but a different path.
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
        try:
            table_elems = self.load_from_config_file( config_filename=config_filename,
                                                      tool_data_path=tool_data_path,
                                                      from_shed_config=True )
        except Exception, e:
            error_message = 'Error attempting to parse file %s: %s' % ( str( os.path.split( config_filename )[ 1 ] ), str( e ) )
            log.debug( error_message )
            table_elems = []
        if persist:
            # Persist Galaxy's version of the changed tool_data_table_conf.xml file.
            self.to_xml_file( shed_tool_data_table_config, table_elems )
        return table_elems, error_message

    def to_xml_file( self, shed_tool_data_table_config, new_elems=None, remove_elems=None ):
        """
        Write the current in-memory version of the shed_tool_data_table_conf.xml file to disk.
        remove_elems are removed before new_elems are added.
        """
        if not ( new_elems or remove_elems ):
            log.debug( 'ToolDataTableManager.to_xml_file called without any elements to add or remove.' )
            return #no changes provided, no need to persist any changes
        if not new_elems:
            new_elems = []
        if not remove_elems:
            remove_elems = []
        full_path = os.path.abspath( shed_tool_data_table_config )
        #FIXME: we should lock changing this file by other threads / head nodes
        try:
            tree = util.parse_xml( full_path )
            root = tree.getroot()
            out_elems = [ elem for elem in root ]
        except Exception, e:
            out_elems = []
            log.debug( 'Could not parse existing tool data table config, assume no existing elements: %s', e )
        for elem in remove_elems:
            #handle multiple occurrences of remove elem in existing elems
            while elem in out_elems:
                remove_elems.remove( elem )
        #add new elems
        out_elems.extend( new_elems )
        with open( full_path, 'wb' ) as out:
            out.write( '<?xml version="1.0"?>\n<tables>\n' )
            for elem in out_elems:
                out.write( util.xml_to_string( elem ) )
            out.write( '</tables>\n' )
        os.chmod( full_path, 0644 )

    def reload_tables( self, table_names=None ):
        tables = self.get_tables()
        if not table_names:
            table_names = tables.keys()
        elif not isinstance( table_names, list ):
            table_names = [ table_names ]
        for table_name in table_names:
            tables[ table_name ].reload_from_files()
            log.debug( "Reloaded tool data table '%s' from files.", table_name )
        return table_names


class ToolDataTable( object ):

    @classmethod
    def from_elem( cls, table_elem, tool_data_path, from_shed_config ):
        table_type = table_elem.get( 'type', 'tabular' )
        assert table_type in tool_data_table_types, "Unknown data table type '%s'" % type
        return tool_data_table_types[ table_type ]( table_elem, tool_data_path, from_shed_config=from_shed_config )

    def __init__( self, config_element, tool_data_path, from_shed_config = False):
        self.name = config_element.get( 'name' )
        self.comment_char = config_element.get( 'comment_char' )
        self.empty_field_value = config_element.get( 'empty_field_value', '' )
        self.empty_field_values = {}
        self.filenames = odict()
        self.tool_data_path = tool_data_path
        self.missing_index_file = None
        # increment this variable any time a new entry is added, or when the table is totally reloaded
        # This value has no external meaning, and does not represent an abstract version of the underlying data
        self._loaded_content_version = 1
        self._load_info = ( [ config_element, tool_data_path ], { 'from_shed_config':from_shed_config } )
        self._merged_load_info = []

    def _update_version( self, version=None ):
        if version is not None:
            self._loaded_content_version = version
        else:
            self._loaded_content_version += 1
        return self._loaded_content_version

    def get_empty_field_by_name( self, name ):
        return self.empty_field_values.get( name, self.empty_field_value )

    def _add_entry( self, entry, allow_duplicates=True, persist=False, persist_on_error=False, entry_source=None, **kwd ):
        raise NotImplementedError( "Abstract method" )

    def add_entry( self, entry, allow_duplicates=True, persist=False, persist_on_error=False, entry_source=None, **kwd ):
        self._add_entry( entry, allow_duplicates=allow_duplicates, persist=persist, persist_on_error=persist_on_error, entry_source=entry_source, **kwd )
        return self._update_version()

    def add_entries( self, entries, allow_duplicates=True, persist=False, persist_on_error=False, entry_source=None, **kwd ):
        if entries:
            for entry in entries:
                self.add_entry( entry, allow_duplicates=allow_duplicates, persist=persist, persist_on_error=persist_on_error, entry_source=entry_source, **kwd )
        return self._loaded_content_version

    def is_current_version( self, other_version ):
        return self._loaded_content_version == other_version

    def merge_tool_data_table( self, other_table, allow_duplicates=True, persist=False, persist_on_error=False, entry_source=None, **kwd ):
        raise NotImplementedError( "Abstract method" )

    def reload_from_files( self ):
        new_version = self._update_version()
        merged_info = self._merged_load_info
        self.__init__( *self._load_info[0], **self._load_info[1] )
        self._update_version( version=new_version )
        for ( tool_data_table_class, load_info ) in merged_info:
            self.merge_tool_data_table( tool_data_table_class( *load_info[0], **load_info[1] ), allow_duplicates=False )
        return self._update_version()


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
        self.config_element = config_element
        self.data = []
        self.configure_and_load( config_element, tool_data_path, from_shed_config)

    def configure_and_load( self, config_element, tool_data_path, from_shed_config = False):
        """
        Configure and load table from an XML element.
        """
        self.separator = config_element.get( 'separator', '\t' )
        self.comment_char = config_element.get( 'comment_char', '#' )
        # Configure columns
        self.parse_column_spec( config_element )

        #store repo info if available:
        repo_elem = config_element.find( 'tool_shed_repository' )
        if repo_elem is not None:
            repo_info = dict( tool_shed=repo_elem.find( 'tool_shed' ).text, name=repo_elem.find( 'repository_name' ).text,
                              owner=repo_elem.find( 'repository_owner' ).text, installed_changeset_revision=repo_elem.find( 'installed_changeset_revision' ).text )
        else:
            repo_info = None
        # Read every file
        for file_element in config_element.findall( 'file' ):
            filename = file_path = file_element.get( 'path', None )
            found = False
            if file_path is None:
                log.debug( "Encountered a file element (%s) that does not contain a path value when loading tool data table '%s'.", util.xml_to_string( file_element ), self.name )
                continue

            #FIXME: splitting on and merging paths from a configuration file when loading is wonky
            # Data should exist on disk in the state needed, i.e. the xml configuration should
            # point directly to the desired file to load. Munging of the tool_data_tables_conf.xml.sample
            # can be done during installing / testing / metadata resetting with the creation of a proper
            # tool_data_tables_conf.xml file, containing correct <file path=> attributes. Allowing a
            # path.join with a different root should be allowed, but splitting should not be necessary.
            if tool_data_path and from_shed_config:
                # Must identify with from_shed_config as well, because the
                # regular galaxy app has and uses tool_data_path.
                # We're loading a tool in the tool shed, so we cannot use the Galaxy tool-data
                # directory which is hard-coded into the tool_data_table_conf.xml entries.
                filename = os.path.split( file_path )[ 1 ]
                filename = os.path.join( tool_data_path, filename )
            if os.path.exists( filename ):
                found = True
            else:
                # Since the path attribute can include a hard-coded path to a specific directory
                # (e.g., <file path="tool-data/cg_crr_files.loc" />) which may not be the same value
                # as self.tool_data_path, we'll parse the path to get the filename and see if it is
                # in self.tool_data_path.
                file_path, file_name = os.path.split( filename )
                if file_path and file_path != self.tool_data_path:
                    corrected_filename = os.path.join( self.tool_data_path, file_name )
                    if os.path.exists( corrected_filename ):
                        filename = corrected_filename
                        found = True

            errors = []
            if found:
                self.data.extend( self.parse_file_fields( open( filename ), errors=errors ) )
                self._update_version()
            else:
                self.missing_index_file = filename
                log.warn( "Cannot find index file '%s' for tool data table '%s'" % ( filename, self.name ) )

            if filename not in self.filenames or not self.filenames[ filename ][ 'found' ]:
                self.filenames[ filename ] = dict( found=found, filename=filename, from_shed_config=from_shed_config, tool_data_path=tool_data_path,
                                                   config_element=config_element, tool_shed_repository=repo_info, errors=errors )
            else:
                log.debug( "Filename '%s' already exists in filenames (%s), not adding", filename, self.filenames.keys() )


    def merge_tool_data_table( self, other_table, allow_duplicates=True, persist=False, persist_on_error=False, entry_source=None, **kwd ):
        assert self.columns == other_table.columns, "Merging tabular data tables with non matching columns is not allowed: %s:%s != %s:%s" % ( self.name, self.columns, other_table.name, other_table.columns )
        #merge filename info
        for filename, info in other_table.filenames.iteritems():
            if filename not in self.filenames:
                self.filenames[ filename ] = info
        #save info about table
        self._merged_load_info.append( ( other_table.__class__, other_table._load_info ) )
        #add data entries and return current data table version
        return self.add_entries( other_table.data, allow_duplicates=allow_duplicates, persist=persist, persist_on_error=persist_on_error, entry_source=entry_source, **kwd )

    def handle_found_index_file( self, filename ):
        self.missing_index_file = None
        self.data.extend( self.parse_file_fields( open( filename ) ) )

    def get_fields( self ):
        return self.data

    def get_named_fields_list( self ):
        rval = []
        named_colums = self.get_column_name_list()
        for fields in self.get_fields():
            field_dict = {}
            for i, field in enumerate( fields ):
                field_name = named_colums[i]
                if field_name is None:
                    field_name = i #check that this is supposed to be 0 based.
                field_dict[ field_name ] = field
            rval.append( field_dict )
        return rval

    def get_version_fields( self ):
        return ( self._loaded_content_version, self.get_fields() )

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

    def parse_file_fields( self, reader, errors=None ):
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
                    line_error = "Line %i in tool data table '%s' is invalid (HINT: '%s' characters must be used to separate fields):\n%s" % ( ( i + 1 ), self.name, separator_char, line )
                    if errors is not None:
                        errors.append( line_error )
                    log.warn( line_error )
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
        for fields in self.get_fields():
            if fields[ query_col ] == query_val:
                rval = fields[ return_col ]
                break
        return rval

    def _add_entry( self, entry, allow_duplicates=True, persist=False, persist_on_error=False, entry_source=None, **kwd ):
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
        is_error = False
        if self.largest_index < len( fields ):
            fields = self._replace_field_separators( fields )
            if fields not in self.get_fields() or allow_duplicates:
                self.data.append( fields )
            else:
                log.debug( "Attempted to add fields (%s) to data table '%s', but this entry already exists and allow_duplicates is False.", fields, self.name )
                is_error = True
        else:
            log.error( "Attempted to add fields (%s) to data table '%s', but there were not enough fields specified ( %i < %i ).", fields, self.name, len( fields ), self.largest_index + 1 )
            is_error = True
        filename = None

        if persist and ( not is_error or persist_on_error ):
            if entry_source:
                #if dict, assume is compatible info dict, otherwise call method
                if isinstance( entry_source, dict ):
                    source_repo_info = entry_source
                else:
                    source_repo_info = entry_source.get_tool_shed_repository_info_dict()
            else:
                source_repo_info = None
            for name, value in self.filenames.iteritems():
                repo_info = value.get( 'tool_shed_repository', None )
                if ( not source_repo_info and not repo_info ) or ( source_repo_info and repo_info and source_repo_info == repo_info ):
                    filename = name
                    break
            if filename is None:
                #should we default to using any filename here instead?
                log.error( "Unable to determine filename for persisting data table '%s' values: '%s'.", self.name, fields )
                is_error = True
            else:
                #FIXME: Need to lock these files for editing
                log.debug( "Persisting changes to file: %s", filename )
                try:
                    data_table_fh = open( filename, 'r+b' )
                except IOError, e:
                    log.warning( 'Error opening data table file (%s) with r+b, assuming file does not exist and will open as wb: %s', self.filename, e )
                    data_table_fh = open( filename, 'wb' )
                if os.stat( filename )[6] != 0:
                    # ensure last existing line ends with new line
                    data_table_fh.seek( -1, 2 ) #last char in file
                    last_char = data_table_fh.read( 1 )
                    if last_char not in [ '\n', '\r' ]:
                        data_table_fh.write( '\n' )
                data_table_fh.write( "%s\n" % ( self.separator.join( fields ) ) )
        return not is_error

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
    
    @property
    def xml_string( self ):
        return util.xml_to_string( self.config_element )

# Registry of tool data types by type_key
tool_data_table_types = dict( [ ( cls.type_key, cls ) for cls in [ TabularToolDataTable ] ] )
