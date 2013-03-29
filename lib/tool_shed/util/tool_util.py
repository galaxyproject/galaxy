import filecmp
import logging
import os
import shutil
import tempfile
import galaxy.tools
from galaxy import eggs
from galaxy import util
from galaxy.datatypes import checkers
from galaxy.model.orm import and_
from galaxy.tools import parameters
from galaxy.tools.parameters import dynamic_options
from galaxy.tools.search import ToolBoxSearch
from galaxy.web.form_builder import SelectField
import tool_shed.util.shed_util_common as suc

import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import commands
from mercurial import hg
from mercurial import ui

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree
from elementtree import ElementInclude
from elementtree.ElementTree import Element
from elementtree.ElementTree import SubElement

log = logging.getLogger( __name__ )

def add_to_shed_tool_config( app, shed_tool_conf_dict, elem_list ):
    # A tool shed repository is being installed so change the shed_tool_conf file.  Parse the config file to generate the entire list
    # of config_elems instead of using the in-memory list since it will be a subset of the entire list if one or more repositories have
    # been deactivated.
    shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    config_elems = []
    tree = util.parse_xml( shed_tool_conf )
    root = tree.getroot()
    for elem in root:
        config_elems.append( elem )
    # Add the elements to the in-memory list of config_elems.
    for elem_entry in elem_list:
        config_elems.append( elem_entry )
    # Persist the altered shed_tool_config file.
    suc.config_elems_to_xml_file( app, config_elems, shed_tool_conf, tool_path )

def add_to_tool_panel( app, repository_name, repository_clone_url, changeset_revision, repository_tools_tups, owner, shed_tool_conf, tool_panel_dict,
                       new_install=True ):
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
            app.toolbox.load_workflow_tag_set( config_elem, app.toolbox.tool_panel, app.toolbox.integrated_tool_panel, load_panel_dict=True )
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

def build_shed_tool_conf_select_field( trans ):
    """Build a SelectField whose options are the keys in trans.app.toolbox.shed_tool_confs."""
    options = []
    for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
        shed_tool_conf_filename = shed_tool_conf_dict[ 'config_filename' ]
        if shed_tool_conf_filename != trans.app.config.migrated_tools_config:
            if shed_tool_conf_filename.startswith( './' ):
                option_label = shed_tool_conf_filename.replace( './', '', 1 )
            else:
                option_label = shed_tool_conf_filename
            options.append( ( option_label, shed_tool_conf_filename ) )
    select_field = SelectField( name='shed_tool_conf' )
    for option_tup in options:
        select_field.add_option( option_tup[ 0 ], option_tup[ 1 ] )
    return select_field

def build_tool_panel_section_select_field( trans ):
    """Build a SelectField whose options are the sections of the current in-memory toolbox."""
    options = []
    for k, v in trans.app.toolbox.tool_panel.items():
        if isinstance( v, galaxy.tools.ToolSection ):
            options.append( ( v.name, v.id ) )
    select_field = SelectField( name='tool_panel_section', display='radio' )
    for option_tup in options:
        select_field.add_option( option_tup[ 0 ], option_tup[ 1 ] )
    return select_field

def can_use_tool_config_disk_file( trans, repository, repo, file_path, changeset_revision ):
    """
    Determine if repository's tool config file on disk can be used.  This method is restricted to tool config files since, with the
    exception of tool config files, multiple files with the same name will likely be in various directories in the repository and we're
    comparing file names only (not relative paths).
    """
    if not file_path or not os.path.exists( file_path ):
        # The file no longer exists on disk, so it must have been deleted at some previous point in the change log.
        return False
    if changeset_revision == repository.tip( trans.app ):
        return True
    file_name = suc.strip_path( file_path )
    latest_version_of_file = get_latest_tool_config_revision_from_repository_manifest( repo, file_name, changeset_revision )
    can_use_disk_file = filecmp.cmp( file_path, latest_version_of_file )
    try:
        os.unlink( latest_version_of_file )
    except:
        pass
    return can_use_disk_file

def check_tool_input_params( app, repo_dir, tool_config_name, tool, sample_files ):
    """
    Check all of the tool's input parameters, looking for any that are dynamically generated using external data files to make 
    sure the files exist.
    """
    invalid_files_and_errors_tups = []
    correction_msg = ''
    for input_param in tool.input_params:
        if isinstance( input_param, parameters.basic.SelectToolParameter ) and input_param.is_dynamic:
            # If the tool refers to .loc files or requires an entry in the tool_data_table_conf.xml, make sure all requirements exist.
            options = input_param.dynamic_options or input_param.options
            if options and isinstance( options, dynamic_options.DynamicOptions ):
                if options.tool_data_table or options.missing_tool_data_table_name:
                    # Make sure the repository contains a tool_data_table_conf.xml.sample file.
                    sample_tool_data_table_conf = suc.get_config_from_disk( 'tool_data_table_conf.xml.sample', repo_dir )
                    if sample_tool_data_table_conf:
                        error, correction_msg = handle_sample_tool_data_table_conf_file( app, sample_tool_data_table_conf )
                        if error:
                            invalid_files_and_errors_tups.append( ( 'tool_data_table_conf.xml.sample', correction_msg ) )
                        else:
                            options.missing_tool_data_table_name = None
                    else:
                        correction_msg = "This file requires an entry in the tool_data_table_conf.xml file.  Upload a file named tool_data_table_conf.xml.sample "
                        correction_msg += "to the repository that includes the required entry to correct this error.<br/>"
                        invalid_files_and_errors_tups.append( ( tool_config_name, correction_msg ) )
                if options.index_file or options.missing_index_file:
                    # Make sure the repository contains the required xxx.loc.sample file.
                    index_file = options.index_file or options.missing_index_file
                    index_file_name = suc.strip_path( index_file )
                    sample_found = False
                    for sample_file in sample_files:
                        sample_file_name = suc.strip_path( sample_file )
                        if sample_file_name == '%s.sample' % index_file_name:
                            options.index_file = index_file_name
                            options.missing_index_file = None
                            if options.tool_data_table:
                                options.tool_data_table.missing_index_file = None
                            sample_found = True
                            break
                    if not sample_found:
                        correction_msg = "This file refers to a file named <b>%s</b>.  " % str( index_file_name )
                        correction_msg += "Upload a file named <b>%s.sample</b> to the repository to correct this error." % str( index_file_name )
                        invalid_files_and_errors_tups.append( ( tool_config_name, correction_msg ) )
    return invalid_files_and_errors_tups

def concat_messages( msg1, msg2 ):
    if msg1:
        if msg2:
            message = '%s  %s' % ( msg1, msg2 )
        else:
            message = msg1
    elif msg2:
        message = msg2
    else:
        message = ''
    return message

def copy_disk_sample_files_to_dir( trans, repo_files_dir, dest_path ):
    """Copy all files currently on disk that end with the .sample extension to the directory to which dest_path refers."""
    sample_files = []
    for root, dirs, files in os.walk( repo_files_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name.endswith( '.sample' ):
                    relative_path = os.path.join( root, name )
                    copy_sample_file( trans.app, relative_path, dest_path=dest_path )
                    sample_files.append( name )
    return sample_files

def copy_sample_file( app, filename, dest_path=None ):
    """Copy xxx.sample to dest_path/xxx.sample and dest_path/xxx.  The default value for dest_path is ~/tool-data."""
    if dest_path is None:
        dest_path = os.path.abspath( app.config.tool_data_path )
    sample_file_name = suc.strip_path( filename )
    copied_file = sample_file_name.replace( '.sample', '' )
    full_source_path = os.path.abspath( filename )
    full_destination_path = os.path.join( dest_path, sample_file_name )
    # Don't copy a file to itself - not sure how this happens, but sometimes it does...
    if full_source_path != full_destination_path:
        # It's ok to overwrite the .sample version of the file.
        shutil.copy( full_source_path, full_destination_path )
    # Only create the .loc file if it does not yet exist.  We don't overwrite it in case it contains stuff proprietary to the local instance.
    if not os.path.exists( os.path.join( dest_path, copied_file ) ):
        shutil.copy( full_source_path, os.path.join( dest_path, copied_file ) )

def copy_sample_files( app, sample_files, tool_path=None, sample_files_copied=None, dest_path=None ):
    """
    Copy all appropriate files to dest_path in the local Galaxy environment that have not already been copied.  Those that have been copied
    are contained in sample_files_copied.  The default value for dest_path is ~/tool-data.  We need to be careful to copy only appropriate
    files here because tool shed repositories can contain files ending in .sample that should not be copied to the ~/tool-data directory.
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

def generate_message_for_invalid_tools( trans, invalid_file_tups, repository, metadata_dict, as_html=True, displaying_invalid_tool=False ):
    if as_html:
        new_line = '<br/>'
        bold_start = '<b>'
        bold_end = '</b>'
    else:
        new_line = '\n'
        bold_start = ''
        bold_end = ''
    message = ''
    if not displaying_invalid_tool:
        if metadata_dict:
            message += "Metadata may have been defined for some items in revision '%s'.  " % str( repository.tip( trans.app ) )
            message += "Correct the following problems if necessary and reset metadata.%s" % new_line
        else:
            message += "Metadata cannot be defined for revision '%s' so this revision cannot be automatically " % str( repository.tip( trans.app ) )
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
            correction_msg = "This file refers to a missing file %s%s%s.  " % ( bold_start, str( missing_file ), bold_end )
            correction_msg += "Upload a file named %s%s%s to the repository to correct this error." % ( bold_start, sample_ext, bold_end )
        else:
            if as_html:
                correction_msg = exception_msg
            else:
                correction_msg = exception_msg.replace( '<br/>', new_line ).replace( '<b>', bold_start ).replace( '</b>', bold_end )
        message += "%s%s%s - %s%s" % ( bold_start, tool_file, bold_end, correction_msg, new_line )
    return message

def generate_tool_panel_dict_for_new_install( tool_dicts, tool_section=None ):
    """
    When installing a repository that contains tools, all tools must currently be defined within the same tool section in the tool
    panel or outside of any sections.
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
    Create a dictionary of the following type for a single tool config file name.  The intent is to call this method for every tool config
    in a repository and append each of these as entries to a tool panel dictionary for the repository.  This allows for each tool to be
    loaded into a different section in the tool panel.
    {<Tool guid> : [{ tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}]}
    """
    tool_panel_dict = {}
    file_name = suc.strip_path( tool_config )
    tool_section_dicts = generate_tool_section_dicts( tool_config=file_name, tool_sections=tool_sections )
    tool_panel_dict[ guid ] = tool_section_dicts
    return tool_panel_dict

def generate_tool_panel_elem_list( repository_name, repository_clone_url, changeset_revision, tool_panel_dict, repository_tools_tups, owner='' ):
    """Generate a list of ElementTree Element objects for each section or tool."""
    elem_list = []
    tool_elem = None
    cleaned_repository_clone_url = suc.clean_repository_clone_url( repository_clone_url )
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
                tool_elem = suc.generate_tool_elem( tool_shed, repository_name, changeset_revision, owner, tool_file_path, tool, tool_section )
            else:
                tool_elem = suc.generate_tool_elem( tool_shed, repository_name, changeset_revision, owner, tool_file_path, tool, None )
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
            # The value of tool_section will be None if the tool is displayed outside of any sections in the tool panel.
            if tool_section:
                section_id = tool_section.id or ''
                section_version = tool_section.version or ''
                section_name = tool_section.name or ''
            else:
                section_id = ''
                section_version = ''
                section_name = ''
            tool_section_dicts.append( dict( tool_config=tool_config, id=section_id, version=section_version, name=section_name ) )
    else:
        tool_section_dicts.append( dict( tool_config=tool_config, id='', version='', name='' ) )
    return tool_section_dicts

def generate_tool_section_element_from_dict( tool_section_dict ):
    # The value of tool_section_dict looks like the following.
    # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
    if tool_section_dict[ 'id' ]:
        # Create a new tool section.
        tool_section = Element( 'section' )
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

def get_latest_tool_config_revision_from_repository_manifest( repo, filename, changeset_revision ):
    """
    Get the latest revision of a tool config file named filename from the repository manifest up to the value of changeset_revision.
    This method is restricted to tool_config files rather than any file since it is likely that, with the exception of tool config files,
    multiple files will have the same name in various directories within the repository.
    """
    stripped_filename = suc.strip_path( filename )
    for changeset in suc.reversed_upper_bounded_changelog( repo, changeset_revision ):
        manifest_ctx = repo.changectx( changeset )
        for ctx_file in manifest_ctx.files():
            ctx_file_name = suc.strip_path( ctx_file )
            if ctx_file_name == stripped_filename:
                try:
                    fctx = manifest_ctx[ ctx_file ]
                except LookupError:
                    # The ctx_file may have been moved in the change set.  For example, 'ncbi_blastp_wrapper.xml' was moved to
                    # 'tools/ncbi_blast_plus/ncbi_blastp_wrapper.xml', so keep looking for the file until we find the new location.
                    continue
                fh = tempfile.NamedTemporaryFile( 'wb' )
                tmp_filename = fh.name
                fh.close()
                fh = open( tmp_filename, 'wb' )
                fh.write( fctx.data() )
                fh.close()
                return tmp_filename
    return None

def get_list_of_copied_sample_files( repo, ctx, dir ):
    """
    Find all sample files (files in the repository with the special .sample extension) in the reversed repository manifest up to ctx.  Copy
    each discovered file to dir and return the list of filenames.  If a .sample file was added in a changeset and then deleted in a later
    changeset, it will be returned in the deleted_sample_files list.  The caller will set the value of app.config.tool_data_path to dir in
    order to load the tools and generate metadata for them.
    """
    deleted_sample_files = []
    sample_files = []
    for changeset in suc.reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        for ctx_file in changeset_ctx.files():
            ctx_file_name = suc.strip_path( ctx_file )
            # If we decide in the future that files deleted later in the changelog should not be used, we can use the following if statement.
            # if ctx_file_name.endswith( '.sample' ) and ctx_file_name not in sample_files and ctx_file_name not in deleted_sample_files:
            if ctx_file_name.endswith( '.sample' ) and ctx_file_name not in sample_files:
                fctx = suc.get_file_context_from_ctx( changeset_ctx, ctx_file )
                if fctx in [ 'DELETED' ]:
                    # Since the possibly future used if statement above is commented out, the same file that was initially added will be
                    # discovered in an earlier changeset in the change log and fall through to the else block below.  In other words, if
                    # a file named blast2go.loc.sample was added in change set 0 and then deleted in changeset 3, the deleted file in changeset
                    # 3 will be handled here, but the later discovered file in changeset 0 will be handled in the else block below.  In this
                    # way, the file contents will always be found for future tools even though the file was deleted.
                    if ctx_file_name not in deleted_sample_files:
                        deleted_sample_files.append( ctx_file_name )
                else:
                    sample_files.append( ctx_file_name )
                    tmp_ctx_file_name = os.path.join( dir, ctx_file_name.replace( '.sample', '' ) )
                    fh = open( tmp_ctx_file_name, 'wb' )
                    fh.write( fctx.data() )
                    fh.close()
    return sample_files, deleted_sample_files

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
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolVersion ) \
                     .filter( app.model.ToolVersion.table.c.tool_id == tool_id ) \
                     .first()

def get_tool_version_association( app, parent_tool_version, tool_version ):
    """Return a ToolVersionAssociation if one exists that associates the two received tool_versions"""
    sa_session = app.model.context.current
    return sa_session.query( app.model.ToolVersionAssociation ) \
                     .filter( and_( app.model.ToolVersionAssociation.table.c.parent_id == parent_tool_version.id,
                                    app.model.ToolVersionAssociation.table.c.tool_id == tool_version.id ) ) \
                     .first()

def handle_missing_data_table_entry( app, relative_install_dir, tool_path, repository_tools_tups ):
    """
    Inspect each tool to see if any have input parameters that are dynamically generated select lists that require entries in the
    tool_data_table_conf.xml file.  This method is called only from Galaxy (not the tool shed) when a repository is being installed
    or reinstalled.
    """
    missing_data_table_entry = False
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        if repository_tool.params_with_missing_data_table_entry:
            missing_data_table_entry = True
            break
    if missing_data_table_entry:
        # The repository must contain a tool_data_table_conf.xml.sample file that includes all required entries for all tools in the repository.
        sample_tool_data_table_conf = suc.get_config_from_disk( 'tool_data_table_conf.xml.sample', relative_install_dir )
        if sample_tool_data_table_conf:
            # Add entries to the ToolDataTableManager's in-memory data_tables dictionary as well as the list of data_table_elems and the list of
            # data_table_elem_names.
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
    Inspect each tool to see if it has any input parameters that are dynamically generated select lists that depend on a .loc file.
    This method is not called from the tool shed, but from Galaxy when a repository is being installed.
    """
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        params_with_missing_index_file = repository_tool.params_with_missing_index_file
        for param in params_with_missing_index_file:
            options = param.options
            missing_file_name = suc.strip_path( options.missing_index_file )
            if missing_file_name not in sample_files_copied:
                # The repository must contain the required xxx.loc.sample file.
                for sample_file in sample_files:
                    sample_file_name = suc.strip_path( sample_file )
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

def handle_sample_files_and_load_tool_from_disk( trans, repo_files_dir, repository_id, tool_config_filepath, work_dir ):
    # Copy all sample files from disk to a temporary directory since the sample files may be in multiple directories.
    message = ''
    sample_files = copy_disk_sample_files_to_dir( trans, repo_files_dir, work_dir )
    if sample_files:
        if 'tool_data_table_conf.xml.sample' in sample_files:
            # Load entries into the tool_data_tables if the tool requires them.
            tool_data_table_config = os.path.join( work_dir, 'tool_data_table_conf.xml' )
            error, message = handle_sample_tool_data_table_conf_file( trans.app, tool_data_table_config )
    tool, valid, message2 = load_tool_from_config( trans.app, repository_id, tool_config_filepath )
    message = concat_messages( message, message2 )
    return tool, valid, message, sample_files

def handle_sample_files_and_load_tool_from_tmp_config( trans, repo, repository_id, changeset_revision, tool_config_filename, work_dir ):
    tool = None
    message = ''
    ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
    # We're not currently doing anything with the returned list of deleted_sample_files here.  It is intended to help handle sample files that are in 
    # the manifest, but have been deleted from disk.
    sample_files, deleted_sample_files = get_list_of_copied_sample_files( repo, ctx, dir=work_dir )
    if sample_files:
        trans.app.config.tool_data_path = work_dir
        if 'tool_data_table_conf.xml.sample' in sample_files:
            # Load entries into the tool_data_tables if the tool requires them.
            tool_data_table_config = os.path.join( work_dir, 'tool_data_table_conf.xml' )
            if tool_data_table_config:
                error, message = handle_sample_tool_data_table_conf_file( trans.app, tool_data_table_config )
                if error:
                    log.debug( message )
    manifest_ctx, ctx_file = suc.get_ctx_file_path_from_manifest( tool_config_filename, repo, changeset_revision )
    if manifest_ctx and ctx_file:
        tool, message2 = load_tool_from_tmp_config( trans, repo, repository_id, manifest_ctx, ctx_file, work_dir )
        message = concat_messages( message, message2 )
    return tool, message, sample_files

def handle_sample_tool_data_table_conf_file( app, filename, persist=False ):
    """
    Parse the incoming filename and add new entries to the in-memory app.tool_data_tables dictionary.  If persist is True (should only occur
    if call is from the Galaxy side, not the tool shed), the new entries will be appended to Galaxy's shed_tool_data_table_conf.xml file on disk.
    """
    error = False
    message = ''
    try:
        new_table_elems, message = app.tool_data_tables.add_new_entries_from_config_file( config_filename=filename,
                                                                                          tool_data_path=app.config.tool_data_path,
                                                                                          shed_tool_data_table_config=app.config.shed_tool_data_table_config,
                                                                                          persist=persist )
        if message:
            error = True
    except Exception, e:
        message = str( e )
        error = True
    return error, message

def handle_tool_panel_selection( trans, metadata, no_changes_checked, tool_panel_section, new_tool_panel_section ):
    """Handle the selected tool panel location for loading tools included in tool shed repositories when installing or reinstalling them."""
    # Get the location in the tool panel in which each tool was originally loaded.
    tool_section = None
    tool_panel_section_key = None
    if 'tools' in metadata:
        # This forces everything to be loaded into the same section (or no section) in the tool panel.
        if no_changes_checked:
            if 'tool_panel_section' in metadata:
                tool_panel_dict = metadata[ 'tool_panel_section' ]
                if not tool_panel_dict:
                    tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            else:
                tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            if tool_panel_dict:
                #tool_panel_dict is empty when tools exist but are not installed into a tool panel
                tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
                tool_section_dict = tool_section_dicts[ 0 ]
                original_section_id = tool_section_dict[ 'id' ]
                original_section_name = tool_section_dict[ 'name' ]
                if original_section_id:
                    tool_panel_section_key = 'section_%s' % str( original_section_id )
                    if tool_panel_section_key in trans.app.toolbox.tool_panel:
                        tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
                    else:
                        # The section in which the tool was originally loaded used to be in the tool panel, but no longer is.
                        elem = Element( 'section' )
                        elem.attrib[ 'name' ] = original_section_name
                        elem.attrib[ 'id' ] = original_section_id
                        elem.attrib[ 'version' ] = ''
                        tool_section = galaxy.tools.ToolSection( elem )
                        trans.app.toolbox.tool_panel[ tool_panel_section_key ] = tool_section
        else:
            # The user elected to change the tool panel section to contain the tools.
            if new_tool_panel_section:
                section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                tool_panel_section_key = 'section_%s' % str( section_id )
                if tool_panel_section_key in trans.app.toolbox.tool_panel:
                    # Appending a tool to an existing section in trans.app.toolbox.tool_panel
                    log.debug( "Appending to tool panel section: %s" % new_tool_panel_section )
                    tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
                else:
                    # Appending a new section to trans.app.toolbox.tool_panel
                    log.debug( "Loading new tool panel section: %s" % new_tool_panel_section )
                    elem = Element( 'section' )
                    elem.attrib[ 'name' ] = new_tool_panel_section
                    elem.attrib[ 'id' ] = section_id
                    elem.attrib[ 'version' ] = ''
                    tool_section = galaxy.tools.ToolSection( elem )
                    trans.app.toolbox.tool_panel[ tool_panel_section_key ] = tool_section
            elif tool_panel_section:
                tool_panel_section_key = 'section_%s' % tool_panel_section
                tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
            else:
                tool_section = None
    return tool_section, new_tool_panel_section, tool_panel_section_key

def handle_tool_versions( app, tool_version_dicts, tool_shed_repository ):
    """
    Using the list of tool_version_dicts retrieved from the tool shed (one per changeset revison up to the currently installed changeset revision),
    create the parent / child pairs of tool versions.  Each dictionary contains { tool id : parent tool id } pairs.
    """
    sa_session = app.model.context.current
    for tool_version_dict in tool_version_dicts:
        for tool_guid, parent_id in tool_version_dict.items():
            tool_version_using_tool_guid = get_tool_version( app, tool_guid )
            tool_version_using_parent_id = get_tool_version( app, parent_id )
            if not tool_version_using_tool_guid:
                tool_version_using_tool_guid = app.model.ToolVersion( tool_id=tool_guid, tool_shed_repository=tool_shed_repository )
                sa_session.add( tool_version_using_tool_guid )
                sa_session.flush()
            if not tool_version_using_parent_id:
                tool_version_using_parent_id = app.model.ToolVersion( tool_id=parent_id, tool_shed_repository=tool_shed_repository )
                sa_session.add( tool_version_using_parent_id )
                sa_session.flush()
            tool_version_association = get_tool_version_association( app,
                                                                     tool_version_using_parent_id,
                                                                     tool_version_using_tool_guid )
            if not tool_version_association:
                # Associate the two versions as parent / child.
                tool_version_association = app.model.ToolVersionAssociation( tool_id=tool_version_using_tool_guid.id,
                                                                             parent_id=tool_version_using_parent_id.id )
                sa_session.add( tool_version_association )
                sa_session.flush()

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
    Attempt to determine if a .sample file is appropriate for copying to ~/tool-data when a tool shed repository is being installed
    into a Galaxy instance.
    """
    # Currently most data index files are tabular, so check that first.  We'll assume that if the file is tabular, it's ok to copy.
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

def load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_config_filename ):
    """
    Return a loaded tool whose tool config file name (e.g., filtering.xml) is the value of tool_config_filename.  The value of changeset_revision
    is a valid (downloadable) changset revision.  The tool config will be located in the repository manifest between the received valid changeset
    revision and the first changeset revision in the repository, searching backwards.
    """
    original_tool_data_path = trans.app.config.tool_data_path
    repository = suc.get_repository_in_tool_shed( trans, repository_id )
    repo_files_dir = repository.repo_path( trans.app )
    repo = hg.repository( suc.get_configured_ui(), repo_files_dir )
    message = ''
    tool = None
    can_use_disk_file = False
    tool_config_filepath = suc.get_absolute_path_to_file_in_repository( repo_files_dir, tool_config_filename )
    work_dir = tempfile.mkdtemp()
    can_use_disk_file = can_use_tool_config_disk_file( trans, repository, repo, tool_config_filepath, changeset_revision )
    if can_use_disk_file:
        trans.app.config.tool_data_path = work_dir
        tool, valid, message, sample_files = handle_sample_files_and_load_tool_from_disk( trans, repo_files_dir, repository_id, tool_config_filepath, work_dir )
        if tool is not None:
            invalid_files_and_errors_tups = check_tool_input_params( trans.app,
                                                                     repo_files_dir,
                                                                     tool_config_filename,
                                                                     tool,
                                                                     sample_files )
            if invalid_files_and_errors_tups:
                message2 = generate_message_for_invalid_tools( trans,
                                                               invalid_files_and_errors_tups,
                                                               repository,
                                                               metadata_dict=None,
                                                               as_html=True,
                                                               displaying_invalid_tool=True )
                message = concat_messages( message, message2 )
    else:
        tool, message, sample_files = handle_sample_files_and_load_tool_from_tmp_config( trans, repo, repository_id, changeset_revision, tool_config_filename, work_dir )
    suc.remove_dir( work_dir )
    trans.app.config.tool_data_path = original_tool_data_path
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    reset_tool_data_tables( trans.app )
    return repository, tool, message

def load_tool_from_config( app, repository_id, full_path ):
    try:
        tool = app.toolbox.load_tool( full_path, repository_id=repository_id )
        valid = True
        error_message = None
    except KeyError, e:
        tool = None
        valid = False
        error_message = 'This file requires an entry for "%s" in the tool_data_table_conf.xml file.  Upload a file ' % str( e )
        error_message += 'named tool_data_table_conf.xml.sample to the repository that includes the required entry to correct '
        error_message += 'this error.  '
    except Exception, e:
        tool = None
        valid = False
        error_message = str( e )
    return tool, valid, error_message

def load_tool_from_tmp_config( trans, repo, repository_id, ctx, ctx_file, work_dir ):
    tool = None
    message = ''
    tmp_tool_config = suc.get_named_tmpfile_from_ctx( ctx, ctx_file, work_dir )
    if tmp_tool_config:
        element_tree = util.parse_xml( tmp_tool_config )
        element_tree_root = element_tree.getroot()
        # Look for code files required by the tool config.
        tmp_code_files = []
        for code_elem in element_tree_root.findall( 'code' ):
            code_file_name = code_elem.get( 'file' )
            tmp_code_file_name = suc.copy_file_from_manifest( repo, ctx, code_file_name, work_dir )
            if tmp_code_file_name:
                tmp_code_files.append( tmp_code_file_name )
        tool, valid, message = load_tool_from_config( trans.app, repository_id, tmp_tool_config )
        for tmp_code_file in tmp_code_files:
            try:
                os.unlink( tmp_code_file )
            except:
                pass
        try:
            os.unlink( tmp_tool_config )
        except:
            pass
    return tool, message

def panel_entry_per_tool( tool_section_dict ):
    # Return True if tool_section_dict looks like this.
    # {<Tool guid> : [{ tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}]}
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

def remove_from_shed_tool_config( trans, shed_tool_conf_dict, guids_to_remove ):
    # A tool shed repository is being uninstalled so change the shed_tool_conf file.  Parse the config file to generate the entire list
    # of config_elems instead of using the in-memory list since it will be a subset of the entire list if one or more repositories have
    # been deactivated.
    shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
    tool_path = shed_tool_conf_dict[ 'tool_path' ]
    config_elems = []
    tree = util.parse_xml( shed_tool_conf )
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
    suc.config_elems_to_xml_file( trans.app, config_elems, shed_tool_conf, tool_path )

def remove_from_tool_panel( trans, repository, shed_tool_conf, uninstall ):
    """A tool shed repository is being deactivated or uninstalled so handle tool panel alterations accordingly."""
    # Determine where the tools are currently defined in the tool panel and store this information so the tools can be displayed
    # in the same way when the repository is activated or reinstalled.
    tool_panel_dict = suc.generate_tool_panel_dict_from_shed_tool_conf_entries( trans.app, repository )
    repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
    trans.sa_session.add( repository )
    trans.sa_session.flush()
    # Create a list of guids for all tools that will be removed from the in-memory tool panel and config file on disk.
    guids_to_remove = [ k for k in tool_panel_dict.keys() ]
    # Remove the tools from the toolbox's tools_by_id dictionary.
    for guid_to_remove in guids_to_remove:
        if guid_to_remove in trans.app.toolbox.tools_by_id:
            del trans.app.toolbox.tools_by_id[ guid_to_remove ]
    index, shed_tool_conf_dict = suc.get_shed_tool_conf_dict( trans.app, shed_tool_conf )
    if uninstall:
        # Remove from the shed_tool_conf file on disk.
        remove_from_shed_tool_config( trans, shed_tool_conf_dict, guids_to_remove )
    config_elems = shed_tool_conf_dict[ 'config_elems' ]
    config_elems_to_remove = []
    for config_elem in config_elems:
        if config_elem.tag == 'section':
            # Get the section key for the in-memory tool panel.
            section_key = 'section_%s' % str( config_elem.get( "id" ) )
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
                if section_key in trans.app.toolbox.tool_panel:
                    tool_section = trans.app.toolbox.tool_panel[ section_key ]
                    guid = tool_elem.get( 'guid' )
                    tool_key = 'tool_%s' % str( guid )
                    # Get the list of versions of this tool that are currently available in the toolbox.
                    available_tool_versions = trans.app.toolbox.get_loaded_tools_by_lineage( guid )
                    if tool_key in tool_section.elems:
                        if available_tool_versions:
                            available_tool_versions.reverse()
                            replacement_tool_key = None
                            replacement_tool_version = None
                            # Since we are going to remove the tool from the section, replace it with the newest loaded version of the tool.
                            for available_tool_version in available_tool_versions:
                                if available_tool_version.id in tool_section.elems.keys():
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
                                tool_section.elems.insert( tool_section_elems_index, replacement_tool_key, replacement_tool_version )
                            else:
                                del tool_section.elems[ tool_key ]
                        else:
                            del tool_section.elems[ tool_key ]
                if uninstall:
                    # Remove the tool from the section in the in-memory integrated tool panel.
                    if section_key in trans.app.toolbox.integrated_tool_panel:
                        tool_section = trans.app.toolbox.integrated_tool_panel[ section_key ]
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
                available_tool_versions = trans.app.toolbox.get_loaded_tools_by_lineage( guid )
                if tool_key in trans.app.toolbox.tool_panel:
                    if available_tool_versions:
                        available_tool_versions.reverse()
                        replacement_tool_key = None
                        replacement_tool_version = None
                        # Since we are going to remove the tool from the section, replace it with the newest loaded version of the tool.
                        for available_tool_version in available_tool_versions:
                            if available_tool_version.id in trans.app.toolbox.tool_panel.keys():
                                replacement_tool_key = 'tool_%s' % str( available_tool_version.id )
                                replacement_tool_version = available_tool_version
                                break
                        if replacement_tool_key and replacement_tool_version:
                            # Get the index of the tool_key in the tool_section.
                            for tool_panel_index, key in enumerate( trans.app.toolbox.tool_panel.keys() ):
                                if key == tool_key:
                                    break
                            # Remove the tool from the tool panel.
                            del trans.app.toolbox.tool_panel[ tool_key ]
                            # Add the replacement tool at the same location in the tool panel.
                            trans.app.toolbox.tool_panel.insert( tool_panel_index, replacement_tool_key, replacement_tool_version )
                        else:
                            del trans.app.toolbox.tool_panel[ tool_key ]
                    else:
                        del trans.app.toolbox.tool_panel[ tool_key ]
                if uninstall:
                    if tool_key in trans.app.toolbox.integrated_tool_panel:
                        del trans.app.toolbox.integrated_tool_panel[ tool_key ]
                config_elems_to_remove.append( config_elem )
    for config_elem in config_elems_to_remove:
        # Remove the element from the in-memory list of elements.
        config_elems.remove( config_elem )
    # Update the config_elems of the in-memory shed_tool_conf_dict.
    shed_tool_conf_dict[ 'config_elems' ] = config_elems
    trans.app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
    trans.app.toolbox_search = ToolBoxSearch( trans.app.toolbox )
    if uninstall and trans.app.config.update_integrated_tool_panel:
        # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
        trans.app.toolbox.write_integrated_tool_panel_config_file()

def reset_tool_data_tables( app ):
    # Reset the tool_data_tables to an empty dictionary.
    app.tool_data_tables.data_tables = {}
