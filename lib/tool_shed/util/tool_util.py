import logging
import os
import shutil
import galaxy.tools
from galaxy import util
from galaxy.datatypes import checkers
from galaxy.model.orm import and_
from galaxy.tools import parameters
from galaxy.tools.search import ToolBoxSearch
from galaxy.util.expressions import ExpressionContext
from galaxy.web.form_builder import SelectField
from galaxy.tools.actions.upload import UploadToolAction
from tool_shed.util import basic_util
from tool_shed.util import common_util
from tool_shed.util import hg_util
from tool_shed.util import xml_util
import tool_shed.util.shed_util_common as suc
from xml.etree import ElementTree as XmlET

log = logging.getLogger( __name__ )

def build_shed_tool_conf_select_field( app ):
    """Build a SelectField whose options are the keys in app.toolbox.shed_tool_confs."""
    options = []
    for shed_tool_conf_dict in app.toolbox.shed_tool_confs:
        shed_tool_conf_filename = shed_tool_conf_dict[ 'config_filename' ]
        if shed_tool_conf_filename != app.config.migrated_tools_config:
            if shed_tool_conf_filename.startswith( './' ):
                option_label = shed_tool_conf_filename.replace( './', '', 1 )
            else:
                option_label = shed_tool_conf_filename
            options.append( ( option_label, shed_tool_conf_filename ) )
    select_field = SelectField( name='shed_tool_conf' )
    for option_tup in options:
        select_field.add_option( option_tup[ 0 ], option_tup[ 1 ] )
    return select_field

def build_tool_panel_section_select_field( app ):
    """Build a SelectField whose options are the sections of the current in-memory toolbox."""
    options = []
    for k, v in app.toolbox.tool_panel.items():
        if isinstance( v, galaxy.tools.ToolSection ):
            options.append( ( v.name, v.id ) )
    select_field = SelectField( name='tool_panel_section_id', display='radio' )
    for option_tup in options:
        select_field.add_option( option_tup[ 0 ], option_tup[ 1 ] )
    return select_field

def copy_sample_file( app, filename, dest_path=None ):
    """
    Copy xxx.sample to dest_path/xxx.sample and dest_path/xxx.  The default value for dest_path
    is ~/tool-data.
    """
    if dest_path is None:
        dest_path = os.path.abspath( app.config.tool_data_path )
    sample_file_name = basic_util.strip_path( filename )
    copied_file = sample_file_name.replace( '.sample', '' )
    full_source_path = os.path.abspath( filename )
    full_destination_path = os.path.join( dest_path, sample_file_name )
    # Don't copy a file to itself - not sure how this happens, but sometimes it does...
    if full_source_path != full_destination_path:
        # It's ok to overwrite the .sample version of the file.
        shutil.copy( full_source_path, full_destination_path )
    # Only create the .loc file if it does not yet exist.  We don't overwrite it in case it
    # contains stuff proprietary to the local instance.
    if not os.path.exists( os.path.join( dest_path, copied_file ) ):
        shutil.copy( full_source_path, os.path.join( dest_path, copied_file ) )

def copy_sample_files( app, sample_files, tool_path=None, sample_files_copied=None, dest_path=None ):
    """
    Copy all appropriate files to dest_path in the local Galaxy environment that have not
    already been copied.  Those that have been copied are contained in sample_files_copied.
    The default value for dest_path is ~/tool-data.  We need to be careful to copy only
    appropriate files here because tool shed repositories can contain files ending in .sample
    that should not be copied to the ~/tool-data directory.
    """
    filenames_not_to_copy = [ 'tool_data_table_conf.xml.sample' ]
    sample_files_copied = util.listify( sample_files_copied )
    for filename in sample_files:
        filename_sans_path = os.path.split( filename )[ 1 ]
        if filename_sans_path not in filenames_not_to_copy and filename not in sample_files_copied:
            if tool_path:
                filename=os.path.join( tool_path, filename )
            # Attempt to ensure we're copying an appropriate file.
            if is_data_index_sample_file( filename ):
                copy_sample_file( app, filename, dest_path=dest_path )

def generate_message_for_invalid_tools( app, invalid_file_tups, repository, metadata_dict, as_html=True,
                                        displaying_invalid_tool=False ):
    if as_html:
        new_line = '<br/>'
        bold_start = '<b>'
        bold_end = '</b>'
    else:
        new_line = '\n'
        bold_start = ''
        bold_end = ''
    message = ''
    if app.name == 'galaxy':
        tip_rev = str( repository.changeset_revision )
    else:
        tip_rev = str( repository.tip( app ) )
    if not displaying_invalid_tool:
        if metadata_dict:
            message += "Metadata may have been defined for some items in revision '%s'.  " % tip_rev
            message += "Correct the following problems if necessary and reset metadata.%s" % new_line
        else:
            message += "Metadata cannot be defined for revision '%s' so this revision cannot be automatically " % tip_rev
            message += "installed into a local Galaxy instance.  Correct the following problems and reset metadata.%s" % new_line
    for itc_tup in invalid_file_tups:
        tool_file, exception_msg = itc_tup
        if exception_msg.find( 'No such file or directory' ) >= 0:
            exception_items = exception_msg.split()
            missing_file_items = exception_items[ 7 ].split( '/' )
            missing_file = missing_file_items[ -1 ].rstrip( '\'' )
            if missing_file.endswith( '.loc' ):
                sample_ext = '%s.sample' % missing_file
            else:
                sample_ext = missing_file
            correction_msg = "This file refers to a missing file %s%s%s.  " % \
                ( bold_start, str( missing_file ), bold_end )
            correction_msg += "Upload a file named %s%s%s to the repository to correct this error." % \
                ( bold_start, sample_ext, bold_end )
        else:
            if as_html:
                correction_msg = exception_msg
            else:
                correction_msg = exception_msg.replace( '<br/>', new_line ).replace( '<b>', bold_start ).replace( '</b>', bold_end )
        message += "%s%s%s - %s%s" % ( bold_start, tool_file, bold_end, correction_msg, new_line )
    return message

def get_headers( fname, sep, count=60, is_multi_byte=False ):
    """Returns a list with the first 'count' lines split by 'sep'."""
    headers = []
    for idx, line in enumerate( file( fname ) ):
        line = line.rstrip( '\n\r' )
        if is_multi_byte:
            line = unicode( line, 'utf-8' )
            sep = sep.encode( 'utf-8' )
        headers.append( line.split( sep ) )
        if idx == count:
            break
    return headers

def get_tool_path_install_dir( partial_install_dir, shed_tool_conf_dict, tool_dict, config_elems ):
    for elem in config_elems:
        if elem.tag == 'tool':
            if elem.get( 'guid' ) == tool_dict[ 'guid' ]:
                tool_path = shed_tool_conf_dict[ 'tool_path' ]
                relative_install_dir = os.path.join( tool_path, partial_install_dir )
                return tool_path, relative_install_dir
        elif elem.tag == 'section':
            for section_elem in elem:
                if section_elem.tag == 'tool':
                    if section_elem.get( 'guid' ) == tool_dict[ 'guid' ]:
                        tool_path = shed_tool_conf_dict[ 'tool_path' ]
                        relative_install_dir = os.path.join( tool_path, partial_install_dir )
                        return tool_path, relative_install_dir
    return None, None

def get_tool_index_sample_files( sample_files ):
    """Try to return the list of all appropriate tool data sample files included in the repository."""
    tool_index_sample_files = []
    for s in sample_files:
        # The problem with this is that Galaxy does not follow a standard naming convention for file names.
        if s.endswith( '.loc.sample' ) or s.endswith( '.xml.sample' ) or s.endswith( '.txt.sample' ):
            tool_index_sample_files.append( str( s ) )
    return tool_index_sample_files

def get_tool_version( app, tool_id ):
    context = app.install_model.context
    return context.query( app.install_model.ToolVersion ) \
                     .filter( app.install_model.ToolVersion.table.c.tool_id == tool_id ) \
                     .first()

def get_tool_version_association( app, parent_tool_version, tool_version ):
    """Return a ToolVersionAssociation if one exists that associates the two received tool_versions"""
    context = app.install_model.context
    return context.query( app.install_model.ToolVersionAssociation ) \
                  .filter( and_( app.install_model.ToolVersionAssociation.table.c.parent_id == parent_tool_version.id,
                                 app.install_model.ToolVersionAssociation.table.c.tool_id == tool_version.id ) ) \
                  .first()

def get_version_lineage_for_tool( app, repository_id, repository_metadata, guid ):
    """
    Return the tool version lineage chain in descendant order for the received
    guid contained in the received repsitory_metadata.tool_versions.
    """
    repository = suc.get_repository_by_id( app, repository_id )
    repo = hg_util.get_repo_for_repository( app, repository=repository, repo_path=None, create=False )
    # Initialize the tool lineage
    version_lineage = [ guid ]
    # Get all ancestor guids of the received guid.
    current_child_guid = guid
    for changeset in hg_util.reversed_upper_bounded_changelog( repo, repository_metadata.changeset_revision ):
        ctx = repo.changectx( changeset )
        rm = suc.get_repository_metadata_by_changeset_revision( app, repository_id, str( ctx ) )
        if rm:
            parent_guid = rm.tool_versions.get( current_child_guid, None )
            if parent_guid:
                version_lineage.append( parent_guid )
                current_child_guid = parent_guid
    # Get all descendant guids of the received guid.
    current_parent_guid = guid
    for changeset in hg_util.reversed_lower_upper_bounded_changelog( repo,
                                                                     repository_metadata.changeset_revision,
                                                                     repository.tip( app ) ):
        ctx = repo.changectx( changeset )
        rm = suc.get_repository_metadata_by_changeset_revision( app, repository_id, str( ctx ) )
        if rm:
            tool_versions = rm.tool_versions
            for child_guid, parent_guid in tool_versions.items():
                if parent_guid == current_parent_guid:
                    version_lineage.insert( 0, child_guid )
                    current_parent_guid = child_guid
                    break
    return version_lineage

def handle_missing_data_table_entry( app, relative_install_dir, tool_path, repository_tools_tups ):
    """
    Inspect each tool to see if any have input parameters that are dynamically
    generated select lists that require entries in the tool_data_table_conf.xml
    file.  This method is called only from Galaxy (not the tool shed) when a
    repository is being installed or reinstalled.
    """
    missing_data_table_entry = False
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        if repository_tool.params_with_missing_data_table_entry:
            missing_data_table_entry = True
            break
    if missing_data_table_entry:
        # The repository must contain a tool_data_table_conf.xml.sample file that includes
        # all required entries for all tools in the repository.
        sample_tool_data_table_conf = hg_util.get_config_from_disk( 'tool_data_table_conf.xml.sample', relative_install_dir )
        if sample_tool_data_table_conf:
            # Add entries to the ToolDataTableManager's in-memory data_tables dictionary.
            error, message = handle_sample_tool_data_table_conf_file( app, sample_tool_data_table_conf, persist=True )
            if error:
                # TODO: Do more here than logging an exception.
                log.debug( message )
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ), guid=guid )
        repository_tools_tups[ index ] = ( tup_path, guid, repository_tool )
        # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
        reset_tool_data_tables( app )
    return repository_tools_tups

def handle_missing_index_file( app, tool_path, sample_files, repository_tools_tups, sample_files_copied ):
    """
    Inspect each tool to see if it has any input parameters that are dynamically
    generated select lists that depend on a .loc file.  This method is not called
    from the tool shed, but from Galaxy when a repository is being installed.
    """
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        params_with_missing_index_file = repository_tool.params_with_missing_index_file
        for param in params_with_missing_index_file:
            options = param.options
            missing_file_name = basic_util.strip_path( options.missing_index_file )
            if missing_file_name not in sample_files_copied:
                # The repository must contain the required xxx.loc.sample file.
                for sample_file in sample_files:
                    sample_file_name = basic_util.strip_path( sample_file )
                    if sample_file_name == '%s.sample' % missing_file_name:
                        copy_sample_file( app, sample_file )
                        if options.tool_data_table and options.tool_data_table.missing_index_file:
                            options.tool_data_table.handle_found_index_file( options.missing_index_file )
                        sample_files_copied.append( options.missing_index_file )
                        break
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ), guid=guid )
        repository_tools_tups[ index ] = ( tup_path, guid, repository_tool )
    return repository_tools_tups, sample_files_copied

def handle_sample_tool_data_table_conf_file( app, filename, persist=False ):
    """
    Parse the incoming filename and add new entries to the in-memory
    app.tool_data_tables dictionary.  If persist is True (should only occur
    if call is from the Galaxy side, not the tool shed), the new entries will
    be appended to Galaxy's shed_tool_data_table_conf.xml file on disk.
    """
    error = False
    message = ''
    try:
        new_table_elems, message = \
            app.tool_data_tables.add_new_entries_from_config_file( config_filename=filename,
                                                                   tool_data_path=app.config.tool_data_path,
                                                                   shed_tool_data_table_config=app.config.shed_tool_data_table_config,
                                                                   persist=persist )
        if message:
            error = True
    except Exception, e:
        message = str( e )
        error = True
    return error, message

def handle_tool_versions( app, tool_version_dicts, tool_shed_repository ):
    """
    Using the list of tool_version_dicts retrieved from the tool shed (one per changeset
    revison up to the currently installed changeset revision), create the parent / child
    pairs of tool versions.  Each dictionary contains { tool id : parent tool id } pairs.
    """
    context = app.install_model.context
    for tool_version_dict in tool_version_dicts:
        for tool_guid, parent_id in tool_version_dict.items():
            tool_version_using_tool_guid = get_tool_version( app, tool_guid )
            tool_version_using_parent_id = get_tool_version( app, parent_id )
            if not tool_version_using_tool_guid:
                tool_version_using_tool_guid = app.install_model.ToolVersion( tool_id=tool_guid, tool_shed_repository=tool_shed_repository )
                context.add( tool_version_using_tool_guid )
                context.flush()
            if not tool_version_using_parent_id:
                tool_version_using_parent_id = app.install_model.ToolVersion( tool_id=parent_id, tool_shed_repository=tool_shed_repository )
                context.add( tool_version_using_parent_id )
                context.flush()
            tool_version_association = get_tool_version_association( app,
                                                                     tool_version_using_parent_id,
                                                                     tool_version_using_tool_guid )
            if not tool_version_association:
                # Associate the two versions as parent / child.
                tool_version_association = app.install_model.ToolVersionAssociation( tool_id=tool_version_using_tool_guid.id,
                                                                             parent_id=tool_version_using_parent_id.id )
                context.add( tool_version_association )
                context.flush()

def install_tool_data_tables( app, tool_shed_repository, tool_index_sample_files ):
    """Only ever called from Galaxy end when installing"""
    TOOL_DATA_TABLE_FILE_NAME = 'tool_data_table_conf.xml'
    TOOL_DATA_TABLE_FILE_SAMPLE_NAME = '%s.sample' % ( TOOL_DATA_TABLE_FILE_NAME )
    SAMPLE_SUFFIX = '.sample'
    SAMPLE_SUFFIX_OFFSET = -len( SAMPLE_SUFFIX )
    tool_path, relative_target_dir = tool_shed_repository.get_tool_relative_path( app )
    target_dir = os.path.join( app.config.shed_tool_data_path, relative_target_dir ) #this is where index files will reside on a per repo/installed version
    if not os.path.exists( target_dir ):
        os.makedirs( target_dir )
    for sample_file in tool_index_sample_files:
        path, filename = os.path.split ( sample_file )
        target_filename = filename
        if target_filename.endswith( SAMPLE_SUFFIX ):
            target_filename = target_filename[ : SAMPLE_SUFFIX_OFFSET ]
        source_file = os.path.join( tool_path, sample_file )
        #we're not currently uninstalling index files, do not overwrite existing files
        target_path_filename = os.path.join( target_dir, target_filename )
        if not os.path.exists( target_path_filename ) or target_filename == TOOL_DATA_TABLE_FILE_NAME:
            shutil.copy2( source_file, target_path_filename )
        else:
            log.debug( "Did not copy sample file '%s' to install directory '%s' because file already exists.", filename, target_dir )
        #for provenance and to simplify introspection, lets keep the original data table sample file around
        if filename == TOOL_DATA_TABLE_FILE_SAMPLE_NAME:
            shutil.copy2( source_file, os.path.join( target_dir, filename ) )
    tool_data_table_conf_filename = os.path.join( target_dir, TOOL_DATA_TABLE_FILE_NAME )
    elems = []
    if os.path.exists( tool_data_table_conf_filename ):
        tree, error_message = xml_util.parse_xml( tool_data_table_conf_filename )
        if tree:
            for elem in tree.getroot():
                #append individual table elems or other elemes, but not tables elems
                if elem.tag == 'tables':
                    for table_elem in elems:
                        elems.append( elem )
                else:
                    elems.append( elem )
    else:
        log.debug( "The '%s' data table file was not found, but was expected to be copied from '%s' during repository installation.",
                   tool_data_table_conf_filename, TOOL_DATA_TABLE_FILE_SAMPLE_NAME )
    for elem in elems:
        if elem.tag == 'table':
            for file_elem in elem.findall( 'file' ):
                path = file_elem.get( 'path', None )
                if path:
                    file_elem.set( 'path', os.path.normpath( os.path.join( target_dir, os.path.split( path )[1] ) ) )
            #store repository info in the table tagset for traceability
            repo_elem = suc.generate_repository_info_elem_from_repository( tool_shed_repository, parent_elem=elem )
    if elems:
        # Remove old data_table
        os.unlink( tool_data_table_conf_filename )
        # Persist new data_table content.
        app.tool_data_tables.to_xml_file( tool_data_table_conf_filename, elems )
    return tool_data_table_conf_filename, elems


def is_column_based( fname, sep='\t', skip=0, is_multi_byte=False ):
    """See if the file is column based with respect to a separator."""
    headers = get_headers( fname, sep, is_multi_byte=is_multi_byte )
    count = 0
    if not headers:
        return False
    for hdr in headers[ skip: ]:
        if hdr and hdr[ 0 ] and not hdr[ 0 ].startswith( '#' ):
            if len( hdr ) > 1:
                count = len( hdr )
            break
    if count < 2:
        return False
    for hdr in headers[ skip: ]:
        if hdr and hdr[ 0 ] and not hdr[ 0 ].startswith( '#' ):
            if len( hdr ) != count:
                return False
    return True

def is_data_index_sample_file( file_path ):
    """
    Attempt to determine if a .sample file is appropriate for copying to ~/tool-data when
    a tool shed repository is being installed into a Galaxy instance.
    """
    # Currently most data index files are tabular, so check that first.  We'll assume that
    # if the file is tabular, it's ok to copy.
    if is_column_based( file_path ):
        return True
    # If the file is any of the following, don't copy it.
    if checkers.check_html( file_path ):
        return False
    if checkers.check_image( file_path ):
        return False
    if checkers.check_binary( name=file_path ):
        return False
    if checkers.is_bz2( file_path ):
        return False
    if checkers.is_gzip( file_path ):
        return False
    if checkers.check_zip( file_path ):
        return False
    # Default to copying the file if none of the above are true.
    return True

def new_state( trans, tool, invalid=False ):
    """Create a new `DefaultToolState` for the received tool.  Only inputs on the first page will be initialized."""
    state = galaxy.tools.DefaultToolState()
    state.inputs = {}
    if invalid:
        # We're attempting to display a tool in the tool shed that has been determined to have errors, so is invalid.
        return state
    inputs = tool.inputs_by_page[ 0 ]
    context = ExpressionContext( state.inputs, parent=None )
    for input in inputs.itervalues():
        try:
            state.inputs[ input.name ] = input.get_initial_value( trans, context )
        except:
            state.inputs[ input.name ] = []
    return state

def panel_entry_per_tool( tool_section_dict ):
    # Return True if tool_section_dict looks like this.
    # {<Tool guid> : 
    #    [{ tool_config : <tool_config_file>,
    #       id: <ToolSection id>,
    #       version : <ToolSection version>,
    #       name : <TooSection name>}]}
    # But not like this.
    # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
    if not tool_section_dict:
        return False
    if len( tool_section_dict ) != 3:
        return True
    for k, v in tool_section_dict:
        if k not in [ 'id', 'version', 'name' ]:
            return True
    return False

def reload_upload_tools( app ):
    if hasattr( app, 'toolbox' ):
        for tool_id in app.toolbox.tools_by_id:
            tool = app.toolbox.tools_by_id[ tool_id ]
            if isinstance( tool.tool_action, UploadToolAction ):
                app.toolbox.reload_tool_by_id( tool_id )

def reset_tool_data_tables( app ):
    # Reset the tool_data_tables to an empty dictionary.
    app.tool_data_tables.data_tables = {}
