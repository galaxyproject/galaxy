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

def add_to_shed_tool_config( app, shed_tool_conf_dict, elem_list ):
    # A tool shed repository is being installed so change the shed_tool_conf file.  Parse the
    # config file to generate the entire list of config_elems instead of using the in-memory list
    # since it will be a subset of the entire list if one or more repositories have been deactivated.
    shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    config_elems = []
    tree, error_message = xml_util.parse_xml( shed_tool_conf )
    if tree:
        root = tree.getroot()
        for elem in root:
            config_elems.append( elem )
        # Add the elements to the in-memory list of config_elems.
        for elem_entry in elem_list:
            config_elems.append( elem_entry )
        # Persist the altered shed_tool_config file.
        suc.config_elems_to_xml_file( app, config_elems, shed_tool_conf, tool_path )

def add_to_tool_panel( app, repository_name, repository_clone_url, changeset_revision, repository_tools_tups, owner,
                       shed_tool_conf, tool_panel_dict, new_install=True ):
    """A tool shed repository is being installed or updated so handle tool panel alterations accordingly."""
    # We need to change the in-memory version and the file system version of the shed_tool_conf file.
    index, shed_tool_conf_dict = suc.get_shed_tool_conf_dict( app, shed_tool_conf )
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    # Generate the list of ElementTree Element objects for each section or tool.
    elem_list = generate_tool_panel_elem_list( repository_name,
                                               repository_clone_url,
                                               changeset_revision,
                                               tool_panel_dict,
                                               repository_tools_tups,
                                               owner=owner )
    if new_install:
        # Add the new elements to the shed_tool_conf file on disk.
        add_to_shed_tool_config( app, shed_tool_conf_dict, elem_list )
        # Use the new elements to add entries to the
    config_elems = shed_tool_conf_dict[ 'config_elems' ]
    for config_elem in elem_list:
        # Add the new elements to the in-memory list of config_elems.
        config_elems.append( config_elem )
        # Load the tools into the in-memory tool panel.
        if config_elem.tag == 'section':
            app.toolbox.load_section_tag_set( config_elem, tool_path, load_panel_dict=True )
        elif config_elem.tag == 'workflow':
            app.toolbox.load_workflow_tag_set( config_elem,
                                               app.toolbox.tool_panel,
                                               app.toolbox.integrated_tool_panel,
                                               load_panel_dict=True )
        elif config_elem.tag == 'tool':
            guid = config_elem.get( 'guid' )
            app.toolbox.load_tool_tag_set( config_elem,
                                           app.toolbox.tool_panel,
                                           app.toolbox.integrated_tool_panel,
                                           tool_path,
                                           load_panel_dict=True,
                                           guid=guid )
    # Replace the old list of in-memory config_elems with the new list for this shed_tool_conf_dict.
    shed_tool_conf_dict[ 'config_elems' ] = config_elems
    app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
    if app.config.update_integrated_tool_panel:
        # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
        app.toolbox.write_integrated_tool_panel_config_file()
    app.toolbox_search = ToolBoxSearch( app.toolbox )

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

def generate_tool_panel_dict_for_new_install( tool_dicts, tool_section=None ):
    """
    When installing a repository that contains tools, all tools must currently be defined
    within the same tool section in the tool panel or outside of any sections.
    """
    tool_panel_dict = {}
    if tool_section:
        section_id = tool_section.id
        section_name = tool_section.name
        section_version = tool_section.version or ''
    else:
        section_id = ''
        section_name = ''
        section_version = ''
    for tool_dict in tool_dicts:
        if tool_dict.get( 'add_to_tool_panel', True ):
            guid = tool_dict[ 'guid' ]
            tool_config = tool_dict[ 'tool_config' ]
            tool_section_dict = dict( tool_config=tool_config, id=section_id, name=section_name, version=section_version )
            if guid in tool_panel_dict:
                tool_panel_dict[ guid ].append( tool_section_dict )
            else:
                tool_panel_dict[ guid ] = [ tool_section_dict ]
    return tool_panel_dict

def generate_tool_panel_dict_for_tool_config( guid, tool_config, tool_sections=None ):
    """
    Create a dictionary of the following type for a single tool config file name.
    The intent is to call this method for every tool config in a repository and
    append each of these as entries to a tool panel dictionary for the repository.
    This allows for each tool to be loaded into a different section in the tool panel.
    {<Tool guid> :
       [{ tool_config : <tool_config_file>,
          id: <ToolSection id>,
          version : <ToolSection version>,
          name : <TooSection name>}]}
    """
    tool_panel_dict = {}
    file_name = basic_util.strip_path( tool_config )
    tool_section_dicts = generate_tool_section_dicts( tool_config=file_name, tool_sections=tool_sections )
    tool_panel_dict[ guid ] = tool_section_dicts
    return tool_panel_dict

def generate_tool_panel_elem_list( repository_name, repository_clone_url, changeset_revision, tool_panel_dict,
                                   repository_tools_tups, owner='' ):
    """Generate a list of ElementTree Element objects for each section or tool."""
    elem_list = []
    tool_elem = None
    cleaned_repository_clone_url = common_util.remove_protocol_and_user_from_clone_url( repository_clone_url )
    if not owner:
        owner = suc.get_repository_owner( cleaned_repository_clone_url )
    tool_shed = cleaned_repository_clone_url.split( '/repos/' )[ 0 ].rstrip( '/' )
    for guid, tool_section_dicts in tool_panel_dict.items():
        for tool_section_dict in tool_section_dicts:
            tool_section = None
            inside_section = False
            section_in_elem_list = False
            if tool_section_dict[ 'id' ]:
                inside_section = True
                # Create a new section element only if we haven't already created it.
                for index, elem in enumerate( elem_list ):
                    if elem.tag == 'section':
                        section_id = elem.get( 'id', None )
                        if section_id == tool_section_dict[ 'id' ]:
                            section_in_elem_list = True
                            tool_section = elem
                            break
                if tool_section is None:
                    tool_section = generate_tool_section_element_from_dict( tool_section_dict )
            # Find the tuple containing the current guid from the list of repository_tools_tups.
            for repository_tool_tup in repository_tools_tups:
                tool_file_path, tup_guid, tool = repository_tool_tup
                if tup_guid == guid:
                    break
            if inside_section:
                tool_elem = suc.generate_tool_elem( tool_shed,
                                                    repository_name,
                                                    changeset_revision,
                                                    owner,
                                                    tool_file_path,
                                                    tool,
                                                    tool_section )
            else:
                tool_elem = suc.generate_tool_elem( tool_shed,
                                                    repository_name,
                                                    changeset_revision,
                                                    owner,
                                                    tool_file_path,
                                                    tool,
                                                    None )
            if inside_section:
                if section_in_elem_list:
                    elem_list[ index ] = tool_section
                else:
                    elem_list.append( tool_section )
            else:
                elem_list.append( tool_elem )
    return elem_list

def generate_tool_section_dicts( tool_config=None, tool_sections=None ):
    tool_section_dicts = []
    if tool_config is None:
        tool_config = ''
    if tool_sections:
        for tool_section in tool_sections:
            # The value of tool_section will be None if the tool is displayed outside
            # of any sections in the tool panel.
            if tool_section:
                section_id = tool_section.id or ''
                section_version = tool_section.version or ''
                section_name = tool_section.name or ''
            else:
                section_id = ''
                section_version = ''
                section_name = ''
            tool_section_dicts.append( dict( tool_config=tool_config,
                                             id=section_id,
                                             version=section_version,
                                             name=section_name ) )
    else:
        tool_section_dicts.append( dict( tool_config=tool_config, id='', version='', name='' ) )
    return tool_section_dicts

def generate_tool_section_element_from_dict( tool_section_dict ):
    # The value of tool_section_dict looks like the following.
    # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
    if tool_section_dict[ 'id' ]:
        # Create a new tool section.
        tool_section = XmlET.Element( 'section' )
        tool_section.attrib[ 'id' ] = tool_section_dict[ 'id' ]
        tool_section.attrib[ 'name' ] = tool_section_dict[ 'name' ]
        tool_section.attrib[ 'version' ] = tool_section_dict[ 'version' ]
    else:
        tool_section = None
    return tool_section

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

def get_list_of_copied_sample_files( repo, ctx, dir ):
    """
    Find all sample files (files in the repository with the special .sample extension)
    in the reversed repository manifest up to ctx.  Copy each discovered file to dir and
    return the list of filenames.  If a .sample file was added in a changeset and then
    deleted in a later changeset, it will be returned in the deleted_sample_files list.
    The caller will set the value of app.config.tool_data_path to dir in order to load
    the tools and generate metadata for them.
    """
    deleted_sample_files = []
    sample_files = []
    for changeset in hg_util.reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        for ctx_file in changeset_ctx.files():
            ctx_file_name = basic_util.strip_path( ctx_file )
            # If we decide in the future that files deleted later in the changelog should
            # not be used, we can use the following if statement. if ctx_file_name.endswith( '.sample' )
            # and ctx_file_name not in sample_files and ctx_file_name not in deleted_sample_files:
            if ctx_file_name.endswith( '.sample' ) and ctx_file_name not in sample_files:
                fctx = hg_util.get_file_context_from_ctx( changeset_ctx, ctx_file )
                if fctx in [ 'DELETED' ]:
                    # Since the possibly future used if statement above is commented out, the
                    # same file that was initially added will be discovered in an earlier changeset
                    # in the change log and fall through to the else block below.  In other words,
                    # if a file named blast2go.loc.sample was added in change set 0 and then deleted
                    # in changeset 3, the deleted file in changeset 3 will be handled here, but the
                    # later discovered file in changeset 0 will be handled in the else block below.
                    # In this way, the file contents will always be found for future tools even though
                    # the file was deleted.
                    if ctx_file_name not in deleted_sample_files:
                        deleted_sample_files.append( ctx_file_name )
                else:
                    sample_files.append( ctx_file_name )
                    tmp_ctx_file_name = os.path.join( dir, ctx_file_name.replace( '.sample', '' ) )
                    fh = open( tmp_ctx_file_name, 'wb' )
                    fh.write( fctx.data() )
                    fh.close()
    return sample_files, deleted_sample_files

def get_or_create_tool_section( toolbox, tool_panel_section_id, new_tool_panel_section_label=None ):
    tool_panel_section_key = str( tool_panel_section_id )
    if tool_panel_section_key in toolbox.tool_panel:
        # Appending a tool to an existing section in toolbox.tool_panel
        tool_section = toolbox.tool_panel[ tool_panel_section_key ]
        log.debug( "Appending to tool panel section: %s" % str( tool_section.name ) )
    else:
        # Appending a new section to toolbox.tool_panel
        if new_tool_panel_section_label is None:
            # This might add an ugly section label to the tool panel, but, oh well...
            new_tool_panel_section_label = tool_panel_section_id
        elem = XmlET.Element( 'section' )
        elem.attrib[ 'name' ] = new_tool_panel_section_label
        elem.attrib[ 'id' ] = tool_panel_section_id
        elem.attrib[ 'version' ] = ''
        tool_section = galaxy.tools.ToolSection( elem )
        toolbox.tool_panel[ tool_panel_section_key ] = tool_section
        log.debug( "Loading new tool panel section: %s" % str( tool_section.name ) )
    return tool_panel_section_key, tool_section

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

def handle_tool_panel_selection( toolbox, metadata, no_changes_checked, tool_panel_section_id, new_tool_panel_section_label ):
    """
    Handle the selected tool panel location for loading tools included in tool shed repositories when installing
    or reinstalling them.
    """
    # Get the location in the tool panel in which each tool was originally loaded.
    tool_section = None
    tool_panel_section_key = None
    if 'tools' in metadata:
        # This forces everything to be loaded into the same section (or no section) in the tool panel.
        if no_changes_checked:
            # Make sure the no_changes check box overrides the new_tool_panel_section_label if the user checked the check
            # box and entered something into the field.
            new_tool_panel_section_label = None
            if 'tool_panel_section' in metadata:
                tool_panel_dict = metadata[ 'tool_panel_section' ]
                if not tool_panel_dict:
                    tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            else:
                tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            if tool_panel_dict:
                # The tool_panel_dict is empty when tools exist but are not installed into a tool panel section.
                tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
                tool_section_dict = tool_section_dicts[ 0 ]
                original_section_id = tool_section_dict[ 'id' ]
                original_section_name = tool_section_dict[ 'name' ]
                if original_section_id:
                    tool_panel_section_key, tool_section = \
                        get_or_create_tool_section( toolbox,
                                                    tool_panel_section_id=original_section_id,
                                                    new_tool_panel_section_label=new_tool_panel_section_label )
        else:
            # The user elected to change the tool panel section to contain the tools.
            tool_panel_section_key, tool_section = handle_tool_panel_section( toolbox,
                                                                              tool_panel_section_id=tool_panel_section_id,
                                                                              new_tool_panel_section_label=new_tool_panel_section_label )
    return tool_section, tool_panel_section_key

def handle_tool_panel_section( toolbox, tool_panel_section_id=None, new_tool_panel_section_label=None ):
    """Return a ToolSection object retrieved from the current in-memory tool_panel."""
    # If tool_panel_section_id is received, the section exists in the tool panel.  In this
    # case, the value of the received tool_panel_section_id must be the id retrieved from a
    # tool panel config (e.g., tool_conf.xml, which may have getext).  If new_tool_panel_section_label
    # is received, a new section will be added to the tool panel.  
    if new_tool_panel_section_label:
        section_id = str( new_tool_panel_section_label.lower().replace( ' ', '_' ) )
        tool_panel_section_key, tool_section = \
            get_or_create_tool_section( toolbox,
                                        tool_panel_section_id=section_id,
                                        new_tool_panel_section_label=new_tool_panel_section_label )
    elif tool_panel_section_id:
        tool_panel_section_key = str( tool_panel_section_id )
        tool_section = toolbox.tool_panel[ tool_panel_section_key ]
    else:
        return None, None
    return tool_panel_section_key, tool_section

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

def remove_from_shed_tool_config( app, shed_tool_conf_dict, guids_to_remove ):
    # A tool shed repository is being uninstalled so change the shed_tool_conf file.
    # Parse the config file to generate the entire list of config_elems instead of
    # using the in-memory list since it will be a subset of the entire list if one
    # or more repositories have been deactivated.
    shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    config_elems = []
    tree, error_message = xml_util.parse_xml( shed_tool_conf )
    if tree:
        root = tree.getroot()
        for elem in root:
            config_elems.append( elem )
        config_elems_to_remove = []
        for config_elem in config_elems:
            if config_elem.tag == 'section':
                tool_elems_to_remove = []
                for tool_elem in config_elem:
                    if tool_elem.get( 'guid' ) in guids_to_remove:
                        tool_elems_to_remove.append( tool_elem )
                for tool_elem in tool_elems_to_remove:
                    # Remove all of the appropriate tool sub-elements from the section element.
                    config_elem.remove( tool_elem )
                if len( config_elem ) < 1:
                    # Keep a list of all empty section elements so they can be removed.
                    config_elems_to_remove.append( config_elem )
            elif config_elem.tag == 'tool':
                if config_elem.get( 'guid' ) in guids_to_remove:
                    config_elems_to_remove.append( config_elem )
        for config_elem in config_elems_to_remove:
            config_elems.remove( config_elem )
        # Persist the altered in-memory version of the tool config.
        suc.config_elems_to_xml_file( app, config_elems, shed_tool_conf, tool_path )

def remove_from_tool_panel( app, repository, shed_tool_conf, uninstall ):
    """
    A tool shed repository is being deactivated or uninstalled, so handle tool panel
    alterations accordingly.
    """
    # Determine where the tools are currently defined in the tool panel and store this
    # information so the tools can be displayed in the same way when the repository is
    # activated or reinstalled.
    tool_panel_dict = suc.generate_tool_panel_dict_from_shed_tool_conf_entries( app, repository )
    repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
    app.install_model.context.add( repository )
    app.install_model.context.flush()
    # Create a list of guids for all tools that will be removed from the in-memory tool panel
    # and config file on disk.
    guids_to_remove = [ k for k in tool_panel_dict.keys() ]
    # Remove the tools from the toolbox's tools_by_id dictionary.
    for guid_to_remove in guids_to_remove:
        if guid_to_remove in app.toolbox.tools_by_id:
            del app.toolbox.tools_by_id[ guid_to_remove ]
    index, shed_tool_conf_dict = suc.get_shed_tool_conf_dict( app, shed_tool_conf )
    if uninstall:
        # Remove from the shed_tool_conf file on disk.
        remove_from_shed_tool_config( app, shed_tool_conf_dict, guids_to_remove )
    config_elems = shed_tool_conf_dict[ 'config_elems' ]
    config_elems_to_remove = []
    for config_elem in config_elems:
        if config_elem.tag == 'section':
            # Get the section key for the in-memory tool panel.
            section_key = str( config_elem.get( "id" ) )
            # Generate the list of tool elements to remove.
            tool_elems_to_remove = []
            for tool_elem in config_elem:
                if tool_elem.get( 'guid' ) in guids_to_remove:
                    tool_elems_to_remove.append( tool_elem )
            for tool_elem in tool_elems_to_remove:
                if tool_elem in config_elem:
                    # Remove the tool sub-element from the section element.
                    config_elem.remove( tool_elem )
                # Remove the tool from the section in the in-memory tool panel.
                if section_key in app.toolbox.tool_panel:
                    tool_section = app.toolbox.tool_panel[ section_key ]
                    guid = tool_elem.get( 'guid' )
                    tool_key = 'tool_%s' % str( guid )
                    # Get the list of versions of this tool that are currently available in the toolbox.
                    available_tool_versions = app.toolbox.get_loaded_tools_by_lineage( guid )
                    if tool_key in tool_section.elems:
                        if available_tool_versions:
                            available_tool_versions.reverse()
                            replacement_tool_key = None
                            replacement_tool_version = None
                            # Since we are going to remove the tool from the section, replace it with the
                            # newest loaded version of the tool.
                            for available_tool_version in available_tool_versions:
                                available_tool_section_id, available_tool_section_name = available_tool_version.get_panel_section()
                                if available_tool_version.id in tool_section.elems.keys() or section_key == available_tool_section_id:
                                    replacement_tool_key = 'tool_%s' % str( available_tool_version.id )
                                    replacement_tool_version = available_tool_version
                                    break
                            if replacement_tool_key and replacement_tool_version:
                                # Get the index of the tool_key in the tool_section.
                                for tool_section_elems_index, key in enumerate( tool_section.elems.keys() ):
                                    if key == tool_key:
                                        break
                                # Remove the tool from the tool section.
                                del tool_section.elems[ tool_key ]
                                # Add the replacement tool at the same location in the tool section.
                                tool_section.elems.insert( tool_section_elems_index,
                                                           replacement_tool_key,
                                                           replacement_tool_version )
                            else:
                                del tool_section.elems[ tool_key ]
                        else:
                            del tool_section.elems[ tool_key ]
                if uninstall:
                    # Remove the tool from the section in the in-memory integrated tool panel.
                    if section_key in app.toolbox.integrated_tool_panel:
                        tool_section = app.toolbox.integrated_tool_panel[ section_key ]
                        tool_key = 'tool_%s' % str( tool_elem.get( 'guid' ) )
                        if tool_key in tool_section.elems:
                            del tool_section.elems[ tool_key ]
            if len( config_elem ) < 1:
                # Keep a list of all empty section elements so they can be removed.
                config_elems_to_remove.append( config_elem )
        elif config_elem.tag == 'tool':
            guid = config_elem.get( 'guid' )
            if guid in guids_to_remove:
                tool_key = 'tool_%s' % str( config_elem.get( 'guid' ) )
                # Get the list of versions of this tool that are currently available in the toolbox.
                available_tool_versions = app.toolbox.get_loaded_tools_by_lineage( guid )
                if tool_key in app.toolbox.tool_panel:
                    if available_tool_versions:
                        available_tool_versions.reverse()
                        replacement_tool_key = None
                        replacement_tool_version = None
                        # Since we are going to remove the tool from the section, replace it with
                        # the newest loaded version of the tool.
                        for available_tool_version in available_tool_versions:
                            available_tool_section_id, available_tool_section_name = available_tool_version.get_panel_section()
                            if available_tool_version.id in app.toolbox.tool_panel.keys() or not available_tool_section_id:
                                replacement_tool_key = 'tool_%s' % str( available_tool_version.id )
                                replacement_tool_version = available_tool_version
                                break
                        if replacement_tool_key and replacement_tool_version:
                            # Get the index of the tool_key in the tool_section.
                            for tool_panel_index, key in enumerate( app.toolbox.tool_panel.keys() ):
                                if key == tool_key:
                                    break
                            # Remove the tool from the tool panel.
                            del app.toolbox.tool_panel[ tool_key ]
                            # Add the replacement tool at the same location in the tool panel.
                            app.toolbox.tool_panel.insert( tool_panel_index, replacement_tool_key, replacement_tool_version )
                        else:
                            del app.toolbox.tool_panel[ tool_key ]
                    else:
                        del app.toolbox.tool_panel[ tool_key ]
                if uninstall:
                    if tool_key in app.toolbox.integrated_tool_panel:
                        del app.toolbox.integrated_tool_panel[ tool_key ]
                config_elems_to_remove.append( config_elem )
    for config_elem in config_elems_to_remove:
        # Remove the element from the in-memory list of elements.
        config_elems.remove( config_elem )
    # Update the config_elems of the in-memory shed_tool_conf_dict.
    shed_tool_conf_dict[ 'config_elems' ] = config_elems
    app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
    app.toolbox_search = ToolBoxSearch( app.toolbox )
    if uninstall and app.config.update_integrated_tool_panel:
        # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
        app.toolbox.write_integrated_tool_panel_config_file()

def reset_tool_data_tables( app ):
    # Reset the tool_data_tables to an empty dictionary.
    app.tool_data_tables.data_tables = {}
