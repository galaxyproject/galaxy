"""
Manage tool data tables, which store (at the application level) data that is
used by tools, for example in the generation of dynamic options. Tables are
loaded and stored by names which tools use to refer to them. This allows
users to configure data tables for a local Galaxy instance without needing
to modify the tool configurations.
"""

import hashlib
import logging
import os
import os.path
import re
import string
from glob import glob
from tempfile import NamedTemporaryFile

from six.moves.urllib.request import urlopen

from galaxy import util
from galaxy.util.dictifiable import Dictifiable
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
        for single_config_filename in util.listify( config_filename ):
            if not single_config_filename:
                continue
            self.load_from_config_file( single_config_filename, self.tool_data_path, from_shed_config=False )

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
                table = ToolDataTable.from_elem( table_elem, tool_data_path, from_shed_config, filename=filename )
                table_elems.append( table_elem )
                if table.name not in self.data_tables:
                    self.data_tables[ table.name ] = table
                    log.debug( "Loaded tool data table '%s' from file '%s'", table.name, filename )
                else:
                    log.debug( "Loading another instance of data table '%s' from file '%s', attempting to merge content.", table.name, filename )
                    self.data_tables[ table.name ].merge_tool_data_table( table, allow_duplicates=False )  # only merge content, do not persist to disk, do not allow duplicate rows when merging
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
        except Exception as e:
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
            return  # no changes provided, no need to persist any changes
        if not new_elems:
            new_elems = []
        if not remove_elems:
            remove_elems = []
        full_path = os.path.abspath( shed_tool_data_table_config )
        # FIXME: we should lock changing this file by other threads / head nodes
        try:
            tree = util.parse_xml( full_path )
            root = tree.getroot()
            out_elems = [ elem for elem in root ]
        except Exception as e:
            out_elems = []
            log.debug( 'Could not parse existing tool data table config, assume no existing elements: %s', e )
        for elem in remove_elems:
            # handle multiple occurrences of remove elem in existing elems
            while elem in out_elems:
                remove_elems.remove( elem )
        # add new elems
        out_elems.extend( new_elems )
        with open( full_path, 'wb' ) as out:
            out.write( '<?xml version="1.0"?>\n<tables>\n' )
            for elem in out_elems:
                out.write( util.xml_to_string( elem, pretty=True ) )
            out.write( '</tables>\n' )
        os.chmod( full_path, 0o644 )

    def reload_tables( self, table_names=None ):
        """
        Reload tool data tables.
        """
        tables = self.get_tables()
        if not table_names:
            table_names = list(tables.keys())
        elif not isinstance( table_names, list ):
            table_names = [ table_names ]
        for table_name in table_names:
            tables[ table_name ].reload_from_files()
            log.debug( "Reloaded tool data table '%s' from files.", table_name )
        return table_names


class ToolDataTable( object ):

    @classmethod
    def from_elem( cls, table_elem, tool_data_path, from_shed_config, filename ):
        table_type = table_elem.get( 'type', 'tabular' )
        assert table_type in tool_data_table_types, "Unknown data table type '%s'" % type
        return tool_data_table_types[ table_type ]( table_elem, tool_data_path, from_shed_config=from_shed_config, filename=filename )

    def __init__( self, config_element, tool_data_path, from_shed_config=False, filename=None ):
        self.name = config_element.get( 'name' )
        self.comment_char = config_element.get( 'comment_char' )
        self.empty_field_value = config_element.get( 'empty_field_value', '' )
        self.empty_field_values = {}
        self.allow_duplicate_entries = util.asbool( config_element.get( 'allow_duplicate_entries', True ) )
        self.here = filename and os.path.dirname(filename)
        self.filenames = odict()
        self.tool_data_path = tool_data_path
        self.missing_index_file = None
        # increment this variable any time a new entry is added, or when the table is totally reloaded
        # This value has no external meaning, and does not represent an abstract version of the underlying data
        self._loaded_content_version = 1
        self._load_info = ( [ config_element, tool_data_path ], { 'from_shed_config': from_shed_config } )
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

    def _remove_entry(self, values):
        raise NotImplementedError( "Abstract method" )

    def remove_entry(self, values):
        self._remove_entry( values )
        return self._update_version()

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


class TabularToolDataTable( ToolDataTable, Dictifiable ):
    """
    Data stored in a tabular / separated value format on disk, allows multiple
    files to be merged but all must have the same column definitions::

        <table type="tabular" name="test">
            <column name='...' index = '...' />
            <file path="..." />
            <file path="..." />
        </table>

    """
    dict_collection_visible_keys = [ 'name' ]

    type_key = 'tabular'

    def __init__( self, config_element, tool_data_path, from_shed_config=False, filename=None ):
        super( TabularToolDataTable, self ).__init__( config_element, tool_data_path, from_shed_config, filename)
        self.config_element = config_element
        self.data = []
        self.configure_and_load( config_element, tool_data_path, from_shed_config)

    def configure_and_load( self, config_element, tool_data_path, from_shed_config=False, url_timeout=10 ):
        """
        Configure and load table from an XML element.
        """
        self.separator = config_element.get( 'separator', '\t' )
        self.comment_char = config_element.get( 'comment_char', '#' )
        # Configure columns
        self.parse_column_spec( config_element )

        # store repo info if available:
        repo_elem = config_element.find( 'tool_shed_repository' )
        if repo_elem is not None:
            repo_info = dict( tool_shed=repo_elem.find( 'tool_shed' ).text, name=repo_elem.find( 'repository_name' ).text,
                              owner=repo_elem.find( 'repository_owner' ).text, installed_changeset_revision=repo_elem.find( 'installed_changeset_revision' ).text )
        else:
            repo_info = None
        # Read every file
        for file_element in config_element.findall( 'file' ):
            tmp_file = None
            filename = file_element.get( 'path', None )
            if filename is None:
                # Handle URLs as files
                filename = file_element.get( 'url', None )
                if filename:
                    tmp_file = NamedTemporaryFile( prefix='TTDT_URL_%s-' % self.name )
                    try:
                        tmp_file.write( urlopen( filename, timeout=url_timeout ).read() )
                    except Exception as e:
                        log.error( 'Error loading Data Table URL "%s": %s', filename, e )
                        continue
                    log.debug( 'Loading Data Table URL "%s" as filename "%s".', filename, tmp_file.name )
                    filename = tmp_file.name
                    tmp_file.flush()
            filename = file_path = expand_here_template( filename, here=self.here )
            found = False
            if file_path is None:
                log.debug( "Encountered a file element (%s) that does not contain a path value when loading tool data table '%s'.", util.xml_to_string( file_element ), self.name )
                continue

            # FIXME: splitting on and merging paths from a configuration file when loading is wonky
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
            elif os.path.exists( "%s.sample" % filename ) and not from_shed_config:
                log.info("Could not find tool data %s, reading sample" % filename)
                filename = "%s.sample" % filename
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
                self.extend_data_with( filename, errors=errors )
                self._update_version()
            else:
                self.missing_index_file = filename
                log.warning( "Cannot find index file '%s' for tool data table '%s'" % ( filename, self.name ) )

            if filename not in self.filenames or not self.filenames[ filename ][ 'found' ]:
                self.filenames[ filename ] = dict( found=found, filename=filename, from_shed_config=from_shed_config, tool_data_path=tool_data_path,
                                                   config_element=config_element, tool_shed_repository=repo_info, errors=errors )
            else:
                log.debug( "Filename '%s' already exists in filenames (%s), not adding", filename, list(self.filenames.keys()) )
            # Remove URL tmp file
            if tmp_file is not None:
                tmp_file.close()

    def merge_tool_data_table( self, other_table, allow_duplicates=True, persist=False, persist_on_error=False, entry_source=None, **kwd ):
        assert self.columns == other_table.columns, "Merging tabular data tables with non matching columns is not allowed: %s:%s != %s:%s" % ( self.name, self.columns, other_table.name, other_table.columns )
        # merge filename info
        for filename, info in other_table.filenames.items():
            if filename not in self.filenames:
                self.filenames[ filename ] = info
        # save info about table
        self._merged_load_info.append( ( other_table.__class__, other_table._load_info ) )
        # If we are merging in a data table that does not allow duplicates, enforce that upon the data table
        if self.allow_duplicate_entries and not other_table.allow_duplicate_entries:
            log.debug( 'While attempting to merge tool data table "%s", the other instance of the table specified that duplicate entries are not allowed, now deduplicating all previous entries.', self.name )
            self.allow_duplicate_entries = False
            self._deduplicate_data()
        # add data entries and return current data table version
        return self.add_entries( other_table.data, allow_duplicates=allow_duplicates, persist=persist, persist_on_error=persist_on_error, entry_source=entry_source, **kwd )

    def handle_found_index_file( self, filename ):
        self.missing_index_file = None
        self.extend_data_with( filename )

    def get_fields( self ):
        return self.data

    def get_field(self, value):
        rval = None
        for i in self.get_named_fields_list():
            if i['value'] == value:
                rval = TabularToolDataField(i)
        return rval

    def get_named_fields_list( self ):
        rval = []
        named_columns = self.get_column_name_list()
        for fields in self.get_fields():
            field_dict = {}
            for i, field in enumerate( fields ):
                if i == len( named_columns ):
                    break
                field_name = named_columns[i]
                if field_name is None:
                    field_name = i  # check that this is supposed to be 0 based.
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
            self.largest_index = 0
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

    def extend_data_with( self, filename, errors=None ):
        here = os.path.dirname(os.path.abspath(filename))
        self.data.extend( self.parse_file_fields( open( filename ), errors=errors, here=here ) )
        if not self.allow_duplicate_entries:
            self._deduplicate_data()

    def parse_file_fields( self, reader, errors=None, here="__HERE__" ):
        """
        Parse separated lines from file and return a list of tuples.

        TODO: Allow named access to fields using the column names.
        """
        separator_char = "<TAB>" if self.separator == "\t" else self.separator

        rval = []
        for i, line in enumerate( reader ):
            if line.lstrip().startswith( self.comment_char ):
                continue
            line = line.rstrip( "\n\r" )
            if line:
                line = expand_here_template( line, here=here )
                fields = line.split( self.separator )
                if self.largest_index < len( fields ):
                    rval.append( fields )
                else:
                    line_error = "Line %i in tool data table '%s' is invalid (HINT: '%s' characters must be used to separate fields):\n%s" % ( ( i + 1 ), self.name, separator_char, line )
                    if errors is not None:
                        errors.append( line_error )
                    log.warning( line_error )
        if hasattr(reader, "name"):
            log.debug("Loaded %i lines from '%s' for '%s'", len(rval), reader.name, self.name)
        return rval

    def get_column_name_list( self ):
        rval = []
        for i in range( self.largest_index + 1 ):
            found_column = False
            for name, index in self.columns.items():
                if index == i:
                    if not found_column:
                        rval.append( name )
                    elif name == 'value':
                        # the column named 'value' always has priority over other named columns
                        rval[ -1 ] = name
                    found_column = True
            if not found_column:
                rval.append( None )
        return rval

    def get_entry( self, query_attr, query_val, return_attr, default=None ):
        """
        Returns table entry associated with a col/val pair.
        """
        rval = self.get_entries( query_attr, query_val, return_attr, default=default, limit=1 )
        if rval:
            return rval[0]
        return default

    def get_entries( self, query_attr, query_val, return_attr, default=None, limit=None ):
        """
        Returns table entry associated with a col/val pair.
        """
        query_col = self.columns.get( query_attr, None )
        if query_col is None:
            return default
        if return_attr is not None:
            return_col = self.columns.get( return_attr, None )
            if return_col is None:
                return default
        rval = []
        # Look for table entry.
        for fields in self.get_fields():
            if fields[ query_col ] == query_val:
                if return_attr is None:
                    field_dict = {}
                    for i, col_name in enumerate( self.get_column_name_list() ):
                        field_dict[ col_name or i ] = fields[i]
                    rval.append( field_dict )
                else:
                    rval.append( fields[ return_col ] )
                if limit is not None and len( rval ) == limit:
                    break
        return rval or default

    def get_filename_for_source( self, source, default=None ):
        if source:
            # if dict, assume is compatible info dict, otherwise call method
            if isinstance( source, dict ):
                source_repo_info = source
            else:
                source_repo_info = source.get_tool_shed_repository_info_dict()
        else:
            source_repo_info = None
        filename = default
        for name, value in self.filenames.items():
            repo_info = value.get( 'tool_shed_repository', None )
            if ( not source_repo_info and not repo_info ) or ( source_repo_info and repo_info and source_repo_info == repo_info ):
                filename = name
                break
        return filename

    def _add_entry( self, entry, allow_duplicates=True, persist=False, persist_on_error=False, entry_source=None, **kwd ):
        # accepts dict or list of columns
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
            if fields not in self.get_fields() or ( allow_duplicates and self.allow_duplicate_entries ):
                self.data.append( fields )
            else:
                log.debug( "Attempted to add fields (%s) to data table '%s', but this entry already exists and allow_duplicates is False.", fields, self.name )
                is_error = True
        else:
            log.error( "Attempted to add fields (%s) to data table '%s', but there were not enough fields specified ( %i < %i ).", fields, self.name, len( fields ), self.largest_index + 1 )
            is_error = True
        filename = None

        if persist and ( not is_error or persist_on_error ):
            filename = self.get_filename_for_source( entry_source )
            if filename is None:
                # should we default to using any filename here instead?
                log.error( "Unable to determine filename for persisting data table '%s' values: '%s'.", self.name, fields )
                is_error = True
            else:
                # FIXME: Need to lock these files for editing
                log.debug( "Persisting changes to file: %s", filename )
                try:
                    data_table_fh = open( filename, 'r+b' )
                except IOError as e:
                    log.warning( 'Error opening data table file (%s) with r+b, assuming file does not exist and will open as wb: %s', filename, e )
                    data_table_fh = open( filename, 'wb' )
                if os.stat( filename )[6] != 0:
                    # ensure last existing line ends with new line
                    data_table_fh.seek( -1, 2 )  # last char in file
                    last_char = data_table_fh.read( 1 )
                    if last_char not in [ '\n', '\r' ]:
                        data_table_fh.write( '\n' )
                data_table_fh.write( "%s\n" % ( self.separator.join( fields ) ) )
        return not is_error

    def _remove_entry( self, values):

        # update every file
        for filename in self.filenames:

            if os.path.exists( filename ):
                values = self._replace_field_separators( values )
                self.filter_file_fields( filename, values )
            else:
                log.warning( "Cannot find index file '%s' for tool data table '%s'" % ( filename, self.name ) )

        self.reload_from_files()

    def filter_file_fields( self, loc_file, values ):
        """
        Reads separated lines from file and print back only the lines that pass a filter.
        """
        with open(loc_file) as reader:
            rval = ""
            for line in reader:
                if line.lstrip().startswith( self.comment_char ):
                    rval += line
                else:
                    line_s = line.rstrip( "\n\r" )
                    if line_s:
                        fields = line_s.split( self.separator )
                        if fields != values:
                            rval += line

        with open(loc_file, 'wb') as writer:
            writer.write(rval)

        return rval

    def _replace_field_separators( self, fields, separator=None, replace=None, comment_char=None ):
        # make sure none of the fields contain separator
        # make sure separator replace is different from comment_char,
        # due to possible leading replace
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
        return [x.replace( separator, replace ) for x in fields]

    def _deduplicate_data( self ):
        # Remove duplicate entries, without recreating self.data object
        dup_lines = []
        hash_list = []
        for i, fields in enumerate( self.data ):
            fields_hash = hash( self.separator.join( fields ) )
            if fields_hash in hash_list:
                dup_lines.append( i )
                log.debug( 'Found duplicate entry in tool data table "%s", but duplicates are not allowed, removing additional entry for: "%s"', self.name, fields )
            else:
                hash_list.append( fields_hash )
        for i in reversed( dup_lines ):
            self.data.pop( i )

    @property
    def xml_string( self ):
        return util.xml_to_string( self.config_element )

    def to_dict(self, view='collection'):
        rval = super(TabularToolDataTable, self).to_dict()
        if view == 'element':
            rval['columns'] = sorted(self.columns.keys(), key=lambda x: self.columns[x])
            rval['fields'] = self.get_fields()
        return rval


class TabularToolDataField(Dictifiable, object):

    dict_collection_visible_keys = []

    def __init__(self, data):
        self.data = data

    def __getitem__(self, key):
        return self.data[key]

    def get_base_path(self):
        return os.path.normpath(os.path.abspath( self.data['path'] ))

    def get_base_dir(self):
        path = self.get_base_path()
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        return path

    def clean_base_dir(self, path):
        return re.sub( "^" + self.get_base_dir() + r"/*", "", path )

    def get_files(self):
        return glob( self.get_base_path() + "*" )

    def get_filesize_map(self, rm_base_dir=False):
        out = {}
        for path in self.get_files():
            if rm_base_dir:
                out[self.clean_base_dir(path)] = os.path.getsize(path)
            else:
                out[path] = os.path.getsize(path)
        return out

    def get_fingerprint(self):
        sha1 = hashlib.sha1()
        fmap = self.get_filesize_map(True)
        for k in sorted(fmap.keys()):
            sha1.update(k)
            sha1.update(str(fmap[k]))
        return sha1.hexdigest()

    def to_dict(self):
        rval = super(TabularToolDataField, self).to_dict()
        rval['name'] = self.data['value']
        rval['fields'] = self.data
        rval['base_dir'] = self.get_base_dir(),
        rval['files'] = self.get_filesize_map(True)
        rval['fingerprint'] = self.get_fingerprint()
        return rval


def expand_here_template(content, here=None):
    if here and content:
        content = string.Template(content).safe_substitute( { "__HERE__": here })
    return content


# Registry of tool data types by type_key
tool_data_table_types = dict( [ ( cls.type_key, cls ) for cls in [ TabularToolDataTable ] ] )
