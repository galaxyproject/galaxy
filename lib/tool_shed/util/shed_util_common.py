import logging
import os
import re
import shutil
import string
import tempfile
from galaxy import util
from galaxy.util import asbool
from galaxy.util import json
from galaxy.util import unicodify
from galaxy.web import url_for
from galaxy.web.form_builder import SelectField
from galaxy.datatypes import checkers
from galaxy.model.orm import and_
from galaxy.model.orm import or_
import sqlalchemy.orm.exc
from tool_shed.util import common_util
from tool_shed.util import encoding_util
from tool_shed.util import hg_util
from tool_shed.util import xml_util
import tool_shed.repository_types.util as rt_util
from xml.etree import ElementTree as XmlET
from urllib2 import HTTPError

from galaxy import eggs
eggs.require( 'mercurial' )

from mercurial import hg

eggs.require( 'markupsafe' )
import markupsafe

log = logging.getLogger( __name__ )

CHUNK_SIZE = 2**20 # 1Mb
INITIAL_CHANGELOG_HASH = '000000000000'
MAX_CONTENT_SIZE = 1048576
MAXDIFFSIZE = 8000
MAX_DISPLAY_SIZE = 32768
DATATYPES_CONFIG_FILENAME = 'datatypes_conf.xml'
REPOSITORY_DATA_MANAGER_CONFIG_FILENAME = 'data_manager_conf.xml'
REPOSITORY_DEPENDENCY_DEFINITION_FILENAME = 'repository_dependencies.xml'
TOOL_DEPENDENCY_DEFINITION_FILENAME = 'tool_dependencies.xml'

new_repo_email_alert_template = """
Sharable link:         ${sharable_link}
Repository name:       ${repository_name}
Revision:              ${revision}
Change description:
${description}

Uploaded by:           ${username}
Date content uploaded: ${display_date}

${content_alert_str}

-----------------------------------------------------------------------------
This change alert was sent from the Galaxy tool shed hosted on the server
"${host}"
-----------------------------------------------------------------------------
You received this alert because you registered to receive email when
new repositories were created in the Galaxy tool shed named "${host}".
-----------------------------------------------------------------------------
"""

email_alert_template = """
Sharable link:         ${sharable_link}
Repository name:       ${repository_name}
Revision:              ${revision}
Change description:
${description}

Changed by:     ${username}
Date of change: ${display_date}

${content_alert_str}

-----------------------------------------------------------------------------
This change alert was sent from the Galaxy tool shed hosted on the server
"${host}"
-----------------------------------------------------------------------------
You received this alert because you registered to receive email whenever
changes were made to the repository named "${repository_name}".
-----------------------------------------------------------------------------
"""

contact_owner_template = """
GALAXY TOOL SHED REPOSITORY MESSAGE
------------------------

The user '${username}' sent you the following message regarding your tool shed
repository named '${repository_name}'.  You can respond by sending a reply to
the user's email address: ${email}.
-----------------------------------------------------------------------------
${message}
-----------------------------------------------------------------------------
This message was sent from the Galaxy Tool Shed instance hosted on the server
'${host}'
"""

def build_repository_ids_select_field( trans, name='repository_ids', multiple=True, display='checkboxes', my_writable=False ):
    """Method called from both Galaxy and the Tool Shed to generate the current list of repositories for resetting metadata."""
    repositories_select_field = SelectField( name=name, multiple=multiple, display=display )
    query = get_query_for_setting_metadata_on_repositories( trans, my_writable=my_writable, order=True )
    for repository in query:
        if trans.webapp.name == 'tool_shed':
            owner = str( repository.user.username )
        else:
            owner = str( repository.owner )
        option_label = '%s (%s)' % ( str( repository.name ), owner )
        option_value = '%s' % trans.security.encode_id( repository.id )
        repositories_select_field.add_option( option_label, option_value )
    return repositories_select_field

def build_tool_dependencies_select_field( trans, tool_shed_repository, name, multiple=True, display='checkboxes', uninstalled_only=False ):
    """Method called from Galaxy to generate the current list of tool dependency ids for an installed tool shed repository."""
    tool_dependencies_select_field = SelectField( name=name, multiple=multiple, display=display )
    for tool_dependency in tool_shed_repository.tool_dependencies:
        if uninstalled_only:
            if tool_dependency.status not in [ trans.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                               trans.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                continue
        else:
            if tool_dependency.status in [ trans.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                           trans.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                continue
        option_label = '%s version %s' % ( str( tool_dependency.name ), str( tool_dependency.version ) )
        option_value = trans.security.encode_id( tool_dependency.id )
        tool_dependencies_select_field.add_option( option_label, option_value )
    return tool_dependencies_select_field

def changeset_is_malicious( trans, id, changeset_revision, **kwd ):
    """Check the malicious flag in repository metadata for a specified change set"""
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
    if repository_metadata:
        return repository_metadata.malicious
    return False

def check_or_update_tool_shed_status_for_installed_repository( trans, repository ):
    updated = False
    tool_shed_status_dict = get_tool_shed_status_for_installed_repository( trans.app, repository )
    if tool_shed_status_dict:
        ok = True
        if tool_shed_status_dict != repository.tool_shed_status:
            repository.tool_shed_status = tool_shed_status_dict
            trans.install_model.context.add( repository )
            trans.install_model.context.flush()
            updated = True
    else:
        ok = False
    return ok, updated

def config_elems_to_xml_file( app, config_elems, config_filename, tool_path ):
    """Persist the current in-memory list of config_elems to a file named by the value of config_filename."""
    fd, filename = tempfile.mkstemp( prefix="tmp-toolshed-cetxf"  )
    os.write( fd, '<?xml version="1.0"?>\n' )
    os.write( fd, '<toolbox tool_path="%s">\n' % str( tool_path ) )
    for elem in config_elems:
        os.write( fd, '%s' % xml_util.xml_to_string( elem, use_indent=True ) )
    os.write( fd, '</toolbox>\n' )
    os.close( fd )
    shutil.move( filename, os.path.abspath( config_filename ) )
    os.chmod( config_filename, 0644 )

def copy_file_from_manifest( repo, ctx, filename, dir ):
    """Copy the latest version of the file named filename from the repository manifest to the directory to which dir refers."""
    for changeset in reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        fctx = get_file_context_from_ctx( changeset_ctx, filename )
        if fctx and fctx not in [ 'DELETED' ]:
            file_path = os.path.join( dir, filename )
            fh = open( file_path, 'wb' )
            fh.write( fctx.data() )
            fh.close()
            return file_path
    return None

def create_or_update_tool_shed_repository( app, name, description, installed_changeset_revision, ctx_rev, repository_clone_url,
                                           metadata_dict, status, current_changeset_revision=None, owner='', dist_to_shed=False ):
    """
    Update a tool shed repository record in the Galaxy database with the new information received.
    If a record defined by the received tool shed, repository name and owner does not exist, create
    a new record with the received information.
    """
    # The received value for dist_to_shed will be True if the ToolMigrationManager is installing a repository
    # that contains tools or datatypes that used to be in the Galaxy distribution, but have been moved
    # to the main Galaxy tool shed.
    if current_changeset_revision is None:
        # The current_changeset_revision is not passed if a repository is being installed for the first
        # time.  If a previously installed repository was later uninstalled, this value should be received
        # as the value of that change set to which the repository had been updated just prior to it being
        # uninstalled.
        current_changeset_revision = installed_changeset_revision
    context = app.install_model.context
    tool_shed = get_tool_shed_from_clone_url( repository_clone_url )
    if not owner:
        owner = get_repository_owner_from_clone_url( repository_clone_url )
    includes_datatypes = 'datatypes' in metadata_dict
    if status in [ app.install_model.ToolShedRepository.installation_status.DEACTIVATED ]:
        deleted = True
        uninstalled = False
    elif status in [ app.install_model.ToolShedRepository.installation_status.UNINSTALLED ]:
        deleted = True
        uninstalled = True
    else:
        deleted = False
        uninstalled = False
    tool_shed_repository = \
        get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( app,
                                                                                  tool_shed,
                                                                                  name,
                                                                                  owner,
                                                                                  installed_changeset_revision )
    if tool_shed_repository:
        log.debug( "Updating an existing row for repository '%s' in the tool_shed_repository table, status set to '%s'." % \
            ( str( name ), str( status ) ) )
        tool_shed_repository.description = description
        tool_shed_repository.changeset_revision = current_changeset_revision
        tool_shed_repository.ctx_rev = ctx_rev
        tool_shed_repository.metadata = metadata_dict
        tool_shed_repository.includes_datatypes = includes_datatypes
        tool_shed_repository.deleted = deleted
        tool_shed_repository.uninstalled = uninstalled
        tool_shed_repository.status = status
    else:
        log.debug( "Adding new row for repository '%s' in the tool_shed_repository table, status set to '%s'." % \
            ( str( name ), str( status ) ) )
        tool_shed_repository = \
            app.install_model.ToolShedRepository( tool_shed=tool_shed,
                                                  name=name,
                                                  description=description,
                                                  owner=owner,
                                                  installed_changeset_revision=installed_changeset_revision,
                                                  changeset_revision=current_changeset_revision,
                                                  ctx_rev=ctx_rev,
                                                  metadata=metadata_dict,
                                                  includes_datatypes=includes_datatypes,
                                                  dist_to_shed=dist_to_shed,
                                                  deleted=deleted,
                                                  uninstalled=uninstalled,
                                                  status=status )
    context.add( tool_shed_repository )
    context.flush()
    return tool_shed_repository

def extract_components_from_tuple( repository_components_tuple ):
    '''Extract the repository components from the provided tuple in a backward-compatible manner.'''
    toolshed = repository_components_tuple[ 0 ]
    name = repository_components_tuple[ 1 ]
    owner = repository_components_tuple[ 2 ]
    changeset_revision = repository_components_tuple[ 3 ]
    components_list = [ toolshed, name, owner, changeset_revision ]
    if len( repository_components_tuple ) == 5:
        toolshed, name, owner, changeset_revision, prior_installation_required = repository_components_tuple
        components_list = [ toolshed, name, owner, changeset_revision, prior_installation_required ]
    elif len( repository_components_tuple ) == 6:
        toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = repository_components_tuple
        components_list = [ toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td ]
    return components_list

def generate_message_for_repository_type_change( trans, repository ):
    message = ''
    if repository.can_change_type_to( trans.app, rt_util.REPOSITORY_SUITE_DEFINITION ):
        repository_suite_definition_type_class = \
            trans.app.repository_types_registry.get_class_by_label( rt_util.REPOSITORY_SUITE_DEFINITION )
        message += "This repository currently contains a single file named <b>%s</b>.  If the intent of this repository is " % \
            REPOSITORY_DEPENDENCY_DEFINITION_FILENAME
        message += "to define relationships to a collection of repositories that contain related Galaxy utilities with "
        message += "no plans to add additional files, consider setting its type to <b>%s</b>.<br/>" % \
            repository_suite_definition_type_class.label
    elif repository.can_change_type_to( trans.app, rt_util.TOOL_DEPENDENCY_DEFINITION ):
        tool_dependency_definition_type_class = \
            trans.app.repository_types_registry.get_class_by_label( rt_util.TOOL_DEPENDENCY_DEFINITION )
        message += "This repository currently contains a single file named <b>%s</b>.  If additional files will " % \
            TOOL_DEPENDENCY_DEFINITION_FILENAME
        message += "not be added to this repository, consider setting its type to <b>%s</b>.<br/>" % \
            tool_dependency_definition_type_class.label
    return message

def generate_repository_info_elem( tool_shed, repository_name, changeset_revision, owner, parent_elem=None, **kwd ):
    """Create and return an ElementTree repository info Element."""
    if parent_elem is None:
        elem = XmlET.Element( 'tool_shed_repository' )
    else:
        elem = XmlET.SubElement( parent_elem, 'tool_shed_repository' )
    tool_shed_elem = XmlET.SubElement( elem, 'tool_shed' )
    tool_shed_elem.text = tool_shed
    repository_name_elem = XmlET.SubElement( elem, 'repository_name' )
    repository_name_elem.text = repository_name
    repository_owner_elem = XmlET.SubElement( elem, 'repository_owner' )
    repository_owner_elem.text = owner
    changeset_revision_elem = XmlET.SubElement( elem, 'installed_changeset_revision' )
    changeset_revision_elem.text = changeset_revision
    #add additional values
    #TODO: enhance additional values to allow e.g. use of dict values that will recurse
    for key, value in kwd.iteritems():
        new_elem = XmlET.SubElement( elem, key )
        new_elem.text = value
    return elem

def generate_repository_info_elem_from_repository( tool_shed_repository, parent_elem=None, **kwd ):
    return generate_repository_info_elem( tool_shed_repository.tool_shed,
                                          tool_shed_repository.name,
                                          tool_shed_repository.installed_changeset_revision,
                                          tool_shed_repository.owner,
                                          parent_elem=parent_elem,
                                          **kwd )

def generate_sharable_link_for_repository_in_tool_shed( trans, repository, changeset_revision=None ):
    """Generate the URL for sharing a repository that is in the tool shed."""
    base_url = url_for( '/', qualified=True ).rstrip( '/' )
    protocol, base = base_url.split( '://' )
    sharable_url = '%s://%s/view/%s/%s' % ( protocol, base, repository.user.username, repository.name )
    if changeset_revision:
        sharable_url += '/%s' % changeset_revision
    return sharable_url

def generate_tool_elem( tool_shed, repository_name, changeset_revision, owner, tool_file_path, tool, tool_section ):
    """Create and return an ElementTree tool Element."""
    if tool_section is not None:
        tool_elem = XmlET.SubElement( tool_section, 'tool' )
    else:
        tool_elem = XmlET.Element( 'tool' )
    tool_elem.attrib[ 'file' ] = tool_file_path
    tool_elem.attrib[ 'guid' ] = tool.guid
    tool_shed_elem = XmlET.SubElement( tool_elem, 'tool_shed' )
    tool_shed_elem.text = tool_shed
    repository_name_elem = XmlET.SubElement( tool_elem, 'repository_name' )
    repository_name_elem.text = repository_name
    repository_owner_elem = XmlET.SubElement( tool_elem, 'repository_owner' )
    repository_owner_elem.text = owner
    changeset_revision_elem = XmlET.SubElement( tool_elem, 'installed_changeset_revision' )
    changeset_revision_elem.text = changeset_revision
    id_elem = XmlET.SubElement( tool_elem, 'id' )
    id_elem.text = tool.id
    version_elem = XmlET.SubElement( tool_elem, 'version' )
    version_elem.text = tool.version
    return tool_elem

def generate_tool_guid( repository_clone_url, tool ):
    """
    Generate a guid for the installed tool.  It is critical that this guid matches the guid for
    the tool in the Galaxy tool shed from which it is being installed.  The form of the guid is
    <tool shed host>/repos/<repository owner>/<repository name>/<tool id>/<tool version>
    """
    tmp_url = common_util.remove_protocol_and_user_from_clone_url( repository_clone_url )
    return '%s/%s/%s' % ( tmp_url, tool.id, tool.version )

def generate_tool_panel_dict_from_shed_tool_conf_entries( app, repository ):
    """
    Keep track of the section in the tool panel in which this repository's tools will be contained by parsing the shed_tool_conf in
    which the repository's tools are defined and storing the tool panel definition of each tool in the repository.  This method is called
    only when the repository is being deactivated or uninstalled and allows for activation or reinstallation using the original layout.
    """
    tool_panel_dict = {}
    shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( app, repository )
    metadata = repository.metadata
    # Create a dictionary of tool guid and tool config file name for each tool in the repository.
    guids_and_configs = {}
    if 'tools' in metadata:
        for tool_dict in metadata[ 'tools' ]:
            guid = tool_dict[ 'guid' ]
            tool_config = tool_dict[ 'tool_config' ]
            file_name = strip_path( tool_config )
            guids_and_configs[ guid ] = file_name
    # Parse the shed_tool_conf file in which all of this repository's tools are defined and generate the tool_panel_dict.
    tree, error_message = xml_util.parse_xml( shed_tool_conf )
    if tree is None:
        return tool_panel_dict
    root = tree.getroot()
    for elem in root:
        if elem.tag == 'tool':
            guid = elem.get( 'guid' )
            if guid in guids_and_configs:
                # The tool is displayed in the tool panel outside of any tool sections.
                tool_section_dict = dict( tool_config=guids_and_configs[ guid ], id='', name='', version='' )
                if guid in tool_panel_dict:
                    tool_panel_dict[ guid ].append( tool_section_dict )
                else:
                    tool_panel_dict[ guid ] = [ tool_section_dict ]
        elif elem.tag == 'section':
            section_id = elem.get( 'id' ) or ''
            section_name = elem.get( 'name' ) or ''
            section_version = elem.get( 'version' ) or ''
            for section_elem in elem:
                if section_elem.tag == 'tool':
                    guid = section_elem.get( 'guid' )
                    if guid in guids_and_configs:
                        # The tool is displayed in the tool panel inside the current tool section.
                        tool_section_dict = dict( tool_config=guids_and_configs[ guid ],
                                                  id=section_id,
                                                  name=section_name,
                                                  version=section_version )
                        if guid in tool_panel_dict:
                            tool_panel_dict[ guid ].append( tool_section_dict )
                        else:
                            tool_panel_dict[ guid ] = [ tool_section_dict ]
    return tool_panel_dict

def generate_tool_shed_repository_install_dir( repository_clone_url, changeset_revision ):
    """
    Generate a repository installation directory that guarantees repositories with the same
    name will always be installed in different directories.  The tool path will be of the form:
    <tool shed url>/repos/<repository owner>/<repository name>/<installed changeset revision>
    """
    tmp_url = common_util.remove_protocol_and_user_from_clone_url( repository_clone_url )
    # Now tmp_url is something like: bx.psu.edu:9009/repos/some_username/column
    items = tmp_url.split( '/repos/' )
    tool_shed_url = items[ 0 ]
    repo_path = items[ 1 ]
    tool_shed_url = common_util.remove_port_from_tool_shed_url( tool_shed_url )
    return common_util.url_join( tool_shed_url, 'repos', repo_path, changeset_revision )

def get_absolute_path_to_file_in_repository( repo_files_dir, file_name ):
    """Return the absolute path to a specified disk file contained in a repository."""
    stripped_file_name = strip_path( file_name )
    file_path = None
    for root, dirs, files in os.walk( repo_files_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == stripped_file_name:
                    return os.path.abspath( os.path.join( root, name ) )
    return file_path

def get_categories( trans ):
    """Get all categories from the database."""
    return trans.sa_session.query( trans.model.Category ) \
                           .filter( trans.model.Category.table.c.deleted==False ) \
                           .order_by( trans.model.Category.table.c.name ) \
                           .all()

def get_category( trans, id ):
    """Get a category from the database."""
    return trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( id ) )

def get_category_by_name( trans, name ):
    """Get a category from the database via name."""
    try:
        return trans.sa_session.query( trans.model.Category ).filter_by( name=name ).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return None

def get_config( config_file, repo, ctx, dir ):
    """Return the latest version of config_filename from the repository manifest."""
    config_file = strip_path( config_file )
    for changeset in reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        for ctx_file in changeset_ctx.files():
            ctx_file_name = strip_path( ctx_file )
            if ctx_file_name == config_file:
                return get_named_tmpfile_from_ctx( changeset_ctx, ctx_file, dir )
    return None

def get_config_from_disk( config_file, relative_install_dir ):
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == config_file:
                    return os.path.abspath( os.path.join( root, name ) )
    return None

def get_ctx_rev( app, tool_shed_url, name, owner, changeset_revision ):
    """
    Send a request to the tool shed to retrieve the ctx_rev for a repository defined by the
    combination of a name, owner and changeset revision.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( app, tool_shed_url )
    params = '?name=%s&owner=%s&changeset_revision=%s' % ( name, owner, changeset_revision )
    url = common_util.url_join( tool_shed_url,
                                'repository/get_ctx_rev%s' % params )
    ctx_rev = common_util.tool_shed_get( app, tool_shed_url, url )
    return ctx_rev

def get_ctx_file_path_from_manifest( filename, repo, changeset_revision ):
    """
    Get the ctx file path for the latest revision of filename from the repository manifest up
    to the value of changeset_revision.
    """
    stripped_filename = strip_path( filename )
    for changeset in reversed_upper_bounded_changelog( repo, changeset_revision ):
        manifest_changeset_revision = str( repo.changectx( changeset ) )
        manifest_ctx = repo.changectx( changeset )
        for ctx_file in manifest_ctx.files():
            ctx_file_name = strip_path( ctx_file )
            if ctx_file_name == stripped_filename:
                return manifest_ctx, ctx_file
    return None, None

def get_current_repository_metadata_for_changeset_revision( trans, repository, changeset_revision ):
    encoded_repository_id = trans.security.encode_id( repository.id )
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, encoded_repository_id, changeset_revision )
    if repository_metadata:
        return repository_metadata
    # The installable changeset_revision may have been changed because it was "moved ahead" in the repository changelog.
    repo = hg.repository( hg_util.get_configured_ui(), repository.repo_path( trans.app ) )
    updated_changeset_revision = get_next_downloadable_changeset_revision( repository, repo, after_changeset_revision=changeset_revision )
    if updated_changeset_revision:
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, encoded_repository_id, updated_changeset_revision )
        if repository_metadata:
            return repository_metadata
    return None

def get_dependent_downloadable_revisions( trans, repository_metadata ):
    """
    Return all repository_metadata records that are downloadable and that depend upon the received
    repository_metadata record.
    """
    # This method is called only from the tool shed.
    rm_changeset_revision = repository_metadata.changeset_revision
    rm_repository = repository_metadata.repository
    rm_repository_name = str( rm_repository.name )
    rm_repository_owner = str( rm_repository.user.username )
    dependent_downloadable_revisions = []
    for repository in trans.sa_session.query( trans.model.Repository ) \
                                      .filter( and_( trans.model.Repository.table.c.id != rm_repository.id,
                                                     trans.model.Repository.table.c.deleted == False,
                                                     trans.model.Repository.table.c.deprecated == False ) ):
        downloadable_revisions = repository.downloadable_revisions
        if downloadable_revisions:
            for downloadable_revision in downloadable_revisions:
                if downloadable_revision.has_repository_dependencies:
                    metadata = downloadable_revision.metadata
                    if metadata:
                        repository_dependencies_dict = metadata.get( 'repository_dependencies', {} )
                        repository_dependencies_tups = repository_dependencies_dict.get( 'repository_dependencies', [] )
                        for repository_dependencies_tup in repository_dependencies_tups:
                            tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                                common_util.parse_repository_dependency_tuple( repository_dependencies_tup )
                            if name == rm_repository_name and owner == rm_repository_owner:
                                # We've discovered a repository revision that depends upon the repository associated
                                # with the received repository_metadata record, but we need to make sure it depends
                                # upon the revision.
                                if changeset_revision == rm_changeset_revision:
                                    dependent_downloadable_revisions.append( downloadable_revision )
                                else:
                                    # Make sure the defined changeset_revision is current.
                                    defined_repository_metadata = \
                                        trans.sa_session.query( trans.model.RepositoryMetadata ) \
                                                        .filter( trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) \
                                                        .first()
                                    if defined_repository_metadata is None:
                                        # The defined changeset_revision is not associated with a repository_metadata
                                        # record, so updates must be necessary.
                                        defined_repository = get_repository_by_name_and_owner( trans.app, name, owner )
                                        defined_repo_dir = defined_repository.repo_path( trans.app )
                                        defined_repo = hg.repository( hg_util.get_configured_ui(), defined_repo_dir )
                                        updated_changeset_revision = \
                                            get_next_downloadable_changeset_revision( defined_repository,
                                                                                      defined_repo,
                                                                                      changeset_revision )
                                        if updated_changeset_revision == rm_changeset_revision:
                                            dependent_downloadable_revisions.append( downloadable_revision )
    return dependent_downloadable_revisions

def get_file_context_from_ctx( ctx, filename ):
    """Return the mercurial file context for a specified file."""
    # We have to be careful in determining if we found the correct file because multiple files with
    # the same name may be in different directories within ctx if the files were moved within the change
    # set.  For example, in the following ctx.files() list, the former may have been moved to the latter: 
    # ['tmap_wrapper_0.0.19/tool_data_table_conf.xml.sample', 'tmap_wrapper_0.3.3/tool_data_table_conf.xml.sample'].
    # Another scenario is that the file has been deleted.
    deleted = False
    filename = strip_path( filename )
    for ctx_file in ctx.files():
        ctx_file_name = strip_path( ctx_file )
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination will be returned here.
                fctx = ctx[ ctx_file ]
                return fctx
            except LookupError, e:
                # Set deleted for now, and continue looking in case the file was moved instead of deleted.
                deleted = True
    if deleted:
        return 'DELETED'
    return None

def get_file_type_str( changeset_revision, file_type ):
    if file_type == 'zip':
        file_type_str = '%s.zip' % changeset_revision
    elif file_type == 'bz2':
        file_type_str = '%s.tar.bz2' % changeset_revision
    elif file_type == 'gz':
        file_type_str = '%s.tar.gz' % changeset_revision
    else:
        file_type_str = ''
    return file_type_str

def get_ids_of_tool_shed_repositories_being_installed( trans, as_string=False ):
    installing_repository_ids = []
    new_status = trans.install_model.ToolShedRepository.installation_status.NEW
    cloning_status = trans.install_model.ToolShedRepository.installation_status.CLONING
    setting_tool_versions_status = trans.install_model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS
    installing_dependencies_status = trans.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES
    loading_datatypes_status = trans.install_model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
    for tool_shed_repository in trans.install_model.context.query( trans.install_model.ToolShedRepository ) \
                                                .filter( or_( trans.install_model.ToolShedRepository.status == new_status,
                                                              trans.install_model.ToolShedRepository.status == cloning_status,
                                                              trans.install_model.ToolShedRepository.status == setting_tool_versions_status,
                                                              trans.install_model.ToolShedRepository.status == installing_dependencies_status,
                                                              trans.install_model.ToolShedRepository.status == loading_datatypes_status ) ):
        installing_repository_ids.append( trans.security.encode_id( tool_shed_repository.id ) )
    if as_string:
        return ','.join( installing_repository_ids )
    return installing_repository_ids

def get_installed_tool_shed_repository( trans, id ):
    """Get a tool shed repository record from the Galaxy database defined by the id."""
    return trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( trans.security.decode_id( id ) )

def get_latest_changeset_revision( trans, repository, repo ):
    repository_tip = repository.tip( trans.app )
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, trans.security.encode_id( repository.id ), repository_tip )
    if repository_metadata and repository_metadata.downloadable:
        return repository_tip
    changeset_revisions = get_ordered_metadata_changeset_revisions( repository, repo, downloadable=False )
    if changeset_revisions:
        return changeset_revisions[ -1 ]
    return INITIAL_CHANGELOG_HASH

def get_latest_downloadable_changeset_revision( trans, repository, repo ):
    repository_tip = repository.tip( trans.app )
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, trans.security.encode_id( repository.id ), repository_tip )
    if repository_metadata and repository_metadata.downloadable:
        return repository_tip
    changeset_revisions = get_ordered_metadata_changeset_revisions( repository, repo, downloadable=True )
    if changeset_revisions:
        return changeset_revisions[ -1 ]
    return INITIAL_CHANGELOG_HASH

def get_named_tmpfile_from_ctx( ctx, filename, dir ):
    """Return a named temporary file created from a specified file with a given name included in a repository changeset revision."""
    filename = strip_path( filename )
    for ctx_file in ctx.files():
        ctx_file_name = strip_path( ctx_file )
        if filename == ctx_file_name:
            try:
                # If the file was moved, its destination file contents will be returned here.
                fctx = ctx[ ctx_file ]
            except LookupError, e:
                # Continue looking in case the file was moved.
                fctx = None
                continue
            if fctx:
                fh = tempfile.NamedTemporaryFile( 'wb', prefix="tmp-toolshed-gntfc", dir=dir )
                tmp_filename = fh.name
                fh.close()
                fh = open( tmp_filename, 'wb' )
                fh.write( fctx.data() )
                fh.close()
                return tmp_filename
    return None

def get_next_downloadable_changeset_revision( repository, repo, after_changeset_revision ):
    """
    Return the installable changeset_revision in the repository changelog after the changeset to which
    after_changeset_revision refers.  If there isn't one, return None.
    """
    changeset_revisions = get_ordered_metadata_changeset_revisions( repository, repo, downloadable=True )
    if len( changeset_revisions ) == 1:
        changeset_revision = changeset_revisions[ 0 ]
        if changeset_revision == after_changeset_revision:
            return None
    found_after_changeset_revision = False
    for changeset in repo.changelog:
        changeset_revision = str( repo.changectx( changeset ) )
        if found_after_changeset_revision:
            if changeset_revision in changeset_revisions:
                return changeset_revision
        elif not found_after_changeset_revision and changeset_revision == after_changeset_revision:
            # We've found the changeset in the changelog for which we need to get the next downloadable changeset.
            found_after_changeset_revision = True
    return None

def get_next_prior_import_or_install_required_dict_entry( prior_required_dict, processed_tsr_ids ):
    """
    This method is used in the Tool Shed when exporting a repository and its dependencies, and in Galaxy
    when a repository and its dependencies are being installed.  The order in which the prior_required_dict
    is processed is critical in order to ensure that the ultimate repository import or installation order is
    correctly defined.  This method determines the next key / value pair from the received prior_required_dict
    that should be processed.
    """
    # Return the first key / value pair that is not yet processed and whose value is an empty list.
    for key, value in prior_required_dict.items():
        if key in processed_tsr_ids:
            continue
        if not value:
            return key
    # Return the first key / value pair that is not yet processed and whose ids in value are all included
    # in processed_tsr_ids.
    for key, value in prior_required_dict.items():
        if key in processed_tsr_ids:
            continue
        all_contained = True
        for required_repository_id in value:
            if required_repository_id not in processed_tsr_ids:
                all_contained = False
                break
        if all_contained:
            return key
    # Return the first key / value pair that is not yet processed.  Hopefully this is all that is necessary
    # at this point.
    for key, value in prior_required_dict.items():
        if key in processed_tsr_ids:
            continue
        return key

def get_or_create_tool_shed_repository( trans, tool_shed, name, owner, changeset_revision ):
    """
    Return a tool shed repository database record defined by the combination of tool shed, repository name, repository owner and changeset_revision
    or installed_changeset_revision.  A new tool shed repository record will be created if one is not located.
    """
    # We store the port in the database.
    tool_shed = common_util.remove_protocol_from_tool_shed_url( tool_shed )
    # This method is used only in Galaxy, not the tool shed.
    repository = get_repository_for_dependency_relationship( trans.app, tool_shed, name, owner, changeset_revision )
    if not repository:
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( trans.app, tool_shed )
        repository_clone_url = os.path.join( tool_shed_url, 'repos', owner, name )
        ctx_rev = get_ctx_rev( trans.app, tool_shed_url, name, owner, changeset_revision )
        repository = create_or_update_tool_shed_repository( app=trans.app,
                                                            name=name,
                                                            description=None,
                                                            installed_changeset_revision=changeset_revision,
                                                            ctx_rev=ctx_rev,
                                                            repository_clone_url=repository_clone_url,
                                                            metadata_dict={},
                                                            status=trans.install_model.ToolShedRepository.installation_status.NEW,
                                                            current_changeset_revision=None,
                                                            owner=owner,
                                                            dist_to_shed=False )
    return repository

def get_ordered_metadata_changeset_revisions( repository, repo, downloadable=True ):
    """Return an ordered list of changeset_revisions that are associated with metadata where order is defined by the repository changelog."""
    if downloadable:
        metadata_revisions = repository.downloadable_revisions
    else:
        metadata_revisions = repository.metadata_revisions
    changeset_tups = []
    for repository_metadata in metadata_revisions:
        changeset_revision = repository_metadata.changeset_revision
        ctx = hg_util.get_changectx_for_changeset( repo, changeset_revision )
        if ctx:
            rev = '%04d' % ctx.rev()
        else:
            rev = '-1'
        changeset_tups.append( ( rev, changeset_revision ) )
    sorted_changeset_tups = sorted( changeset_tups )
    sorted_changeset_revisions = [ str( changeset_tup[ 1 ] ) for changeset_tup in sorted_changeset_tups ]
    return sorted_changeset_revisions

def get_previous_metadata_changeset_revision( repository, repo, before_changeset_revision, downloadable=True ):
    """
    Return the changeset_revision in the repository changelog that has associated metadata prior to the changeset to which
    before_changeset_revision refers.  If there isn't one, return the hash value of an empty repository changelog, INITIAL_CHANGELOG_HASH.
    """
    changeset_revisions = get_ordered_metadata_changeset_revisions( repository, repo, downloadable=downloadable )
    if len( changeset_revisions ) == 1:
        changeset_revision = changeset_revisions[ 0 ]
        if changeset_revision == before_changeset_revision:
            return INITIAL_CHANGELOG_HASH
        return changeset_revision
    previous_changeset_revision = None
    for changeset_revision in changeset_revisions:
        if changeset_revision == before_changeset_revision:
            if previous_changeset_revision:
                return previous_changeset_revision
            else:
                # Return the hash value of an empty repository changelog - note that this will not be a valid changeset revision.
                return INITIAL_CHANGELOG_HASH
        else:
            previous_changeset_revision = changeset_revision

def get_prior_import_or_install_required_dict( trans, tsr_ids, repo_info_dicts ):
    """
    This method is used in the Tool Shed when exporting a repository and its dependencies, and in Galaxy when a repository and its dependencies
    are being installed.  Return a dictionary whose keys are the received tsr_ids and whose values are a list of tsr_ids, each of which is contained
    in the received list of tsr_ids and whose associated repository must be imported or installed prior to the repository associated with the tsr_id key.
    """
    # Initialize the dictionary.
    prior_import_or_install_required_dict = {}
    for tsr_id in tsr_ids:
        prior_import_or_install_required_dict[ tsr_id ] = []
    # Inspect the repository dependencies for each repository about to be installed and populate the dictionary.
    for repo_info_dict in repo_info_dicts:
        repository, repository_dependencies = get_repository_and_repository_dependencies_from_repo_info_dict( trans, repo_info_dict )
        if repository:
            encoded_repository_id = trans.security.encode_id( repository.id )
            if encoded_repository_id in tsr_ids:
                # We've located the database table record for one of the repositories we're about to install, so find out if it has any repository
                # dependencies that require prior installation.
                prior_import_or_install_ids = get_repository_ids_requiring_prior_import_or_install( trans, tsr_ids, repository_dependencies )
                prior_import_or_install_required_dict[ encoded_repository_id ] = prior_import_or_install_ids
    return prior_import_or_install_required_dict

def get_query_for_setting_metadata_on_repositories( trans, my_writable=False, order=True ):
    """
    Return a query containing repositories for resetting metadata.  This method is called from both the
    Tool Shed and Galaxy.  The my_writable parameter is ignored unless called from the Tool Shed, and the
    order parameter is used for displaying the list of repositories ordered alphabetically for display on
    a page.  When called from either the Tool Shed or Galaxy API, order is False.
    """
    if trans.webapp.name == 'tool_shed':
        # When called from the Tool Shed API, the metadata is reset on all repositories of types
        # repository_suite_definition and tool_dependency_definition in addition to other selected
        # repositories.
        if my_writable:
            username = trans.user.username
            clause_list = []
            for repository in trans.sa_session.query( trans.model.Repository ) \
                                              .filter( trans.model.Repository.table.c.deleted == False ):
                # Always reset metadata on all repositories of types repository_suite_definition and
                # tool_dependency_definition.
                if repository.type in [ rt_util.REPOSITORY_SUITE_DEFINITION, rt_util.TOOL_DEPENDENCY_DEFINITION ]:
                    clause_list.append( trans.model.Repository.table.c.id == repository.id )
                else:
                    allow_push = repository.allow_push( trans.app )
                    if allow_push:
                        # Include all repositories that are writable by the current user.
                        allow_push_usernames = allow_push.split( ',' )
                        if username in allow_push_usernames:
                            clause_list.append( trans.model.Repository.table.c.id == repository.id )
            if clause_list:
                if order:
                    return trans.sa_session.query( trans.model.Repository ) \
                                           .filter( or_( *clause_list ) ) \
                                           .order_by( trans.model.Repository.table.c.name,
                                                      trans.model.Repository.table.c.user_id )
                else:
                    return trans.sa_session.query( trans.model.Repository ) \
                                           .filter( or_( *clause_list ) )
            else:
                # Return an empty query.
                return trans.sa_session.query( trans.model.Repository ) \
                                       .filter( trans.model.Repository.table.c.id == -1 )
        else:
            if order:
                return trans.sa_session.query( trans.model.Repository ) \
                                       .filter( trans.model.Repository.table.c.deleted == False ) \
                                       .order_by( trans.model.Repository.table.c.name,
                                                  trans.model.Repository.table.c.user_id )
            else:
                return trans.sa_session.query( trans.model.Repository ) \
                                       .filter( trans.model.Repository.table.c.deleted == False )
    else:
        # We're in Galaxy.
        if order:
            return trans.install_model.context.query( trans.install_model.ToolShedRepository ) \
                                   .filter( trans.install_model.ToolShedRepository.table.c.uninstalled == False ) \
                                   .order_by( trans.install_model.ToolShedRepository.table.c.name,
                                              trans.install_model.ToolShedRepository.table.c.owner )
        else:
            return trans.install_model.context.query( trans.install_model.ToolShedRepository ) \
                                   .filter( trans.install_model.ToolShedRepository.table.c.uninstalled == False )

def get_repo_info_tuple_contents( repo_info_tuple ):
    """Take care in handling the repo_info_tuple as it evolves over time as new tool shed features are introduced."""
    if len( repo_info_tuple ) == 6:
        description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple
        repository_dependencies = None
    elif len( repo_info_tuple ) == 7:
        description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = repo_info_tuple
    return description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies

def get_repository_and_repository_dependencies_from_repo_info_dict( trans, repo_info_dict ):
    """Return a tool_shed_repository or repository record defined by the information in the received repo_info_dict."""
    repository_name = repo_info_dict.keys()[ 0 ]
    repo_info_tuple = repo_info_dict[ repository_name ]
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
        get_repo_info_tuple_contents( repo_info_tuple )
    if trans.webapp.name == 'galaxy':
        tool_shed = get_tool_shed_from_clone_url( repository_clone_url )
        repository = get_repository_for_dependency_relationship( trans.app, tool_shed, repository_name, repository_owner, changeset_revision )
    else:
        # We're in the tool shed.
        repository = get_repository_by_name_and_owner( trans.app, repository_name, repository_owner )
    return repository, repository_dependencies

def get_repository_by_id( trans, id ):
    """Get a repository from the database via id."""
    if trans.webapp.name == 'galaxy':
        return trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( trans.security.decode_id( id ) )
    else:
        return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )

def get_repository_by_name( app, name ):
    """Get a repository from the database via name."""
    repository_query = get_repository_query( app )
    if app.name == 'galaxy':
        return repository_query.filter_by( name=name ).first()
    else:
        return repository_query.filter_by( name=name ).first()

def get_repository_by_name_and_owner( app, name, owner ):
    """Get a repository from the database via name and owner"""
    repository_query = get_repository_query( app )
    if app.name == 'galaxy':
        return repository_query \
                         .filter( and_( app.install_model.ToolShedRepository.table.c.name == name,
                                        app.install_model.ToolShedRepository.table.c.owner == owner ) ) \
                         .first()
    # We're in the tool shed.
    user = get_user_by_username( app, owner )
    if user:
        return repository_query \
                         .filter( and_( app.model.Repository.table.c.name == name,
                                        app.model.Repository.table.c.user_id == user.id ) ) \
                         .first()
    return None

def get_repository_dependency_types( repository_dependencies ):
    """
    Inspect the received list of repository_dependencies tuples and return boolean values
    for has_repository_dependencies and has_repository_dependencies_only_if_compiling_contained_td.
    """
    # Set has_repository_dependencies, which will be True only if at least one repository_dependency
    # is defined with the value of
    # only_if_compiling_contained_td as False.
    has_repository_dependencies = False
    for rd_tup in repository_dependencies:
        tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
            common_util.parse_repository_dependency_tuple( rd_tup )
        if not asbool( only_if_compiling_contained_td ):
            has_repository_dependencies = True
            break
    # Set has_repository_dependencies_only_if_compiling_contained_td, which will be True only if at
    # least one repository_dependency is defined with the value of only_if_compiling_contained_td as True.
    has_repository_dependencies_only_if_compiling_contained_td = False
    for rd_tup in repository_dependencies:
        tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
            common_util.parse_repository_dependency_tuple( rd_tup )
        if asbool( only_if_compiling_contained_td ):
            has_repository_dependencies_only_if_compiling_contained_td = True
            break
    return has_repository_dependencies, has_repository_dependencies_only_if_compiling_contained_td

def get_repository_for_dependency_relationship( app, tool_shed, name, owner, changeset_revision ):
    """
    Return an installed tool_shed_repository database record that is defined by either the current changeset
    revision or the installed_changeset_revision.
    """
    # This method is used only in Galaxy, not the Tool Shed.  We store the port (if one exists) in the database.
    tool_shed = common_util.remove_protocol_from_tool_shed_url( tool_shed )
    if tool_shed is None or name is None or owner is None or changeset_revision is None:
        message = "Unable to retrieve the repository record from the database because one or more of the following "
        message += "required parameters is None: tool_shed: %s, name: %s, owner: %s, changeset_revision: %s " % \
            ( str( tool_shed ), str( name ), str( owner ), str( changeset_revision ) )
        raise Exception( message )
    repository = get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( app=app,
                                                                                           tool_shed=tool_shed,
                                                                                           name=name,
                                                                                           owner=owner,
                                                                                           installed_changeset_revision=changeset_revision )
    if not repository:
        repository = get_tool_shed_repository_by_shed_name_owner_changeset_revision( app=app,
                                                                                     tool_shed=tool_shed,
                                                                                     name=name,
                                                                                     owner=owner,
                                                                                     changeset_revision=changeset_revision )
    if not repository:
        # The received changeset_revision is no longer installable, so get the next changeset_revision
        # in the repository's changelog in the tool shed that is associated with repository_metadata.
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( app, tool_shed )
        params = '?name=%s&owner=%s&changeset_revision=%s' % ( name, owner, changeset_revision )
        url = common_util.url_join( tool_shed_url,
                                    'repository/next_installable_changeset_revision%s' % params )
        text = common_util.tool_shed_get( app, tool_shed_url, url )
        if text:
            repository = get_tool_shed_repository_by_shed_name_owner_changeset_revision( app=app,
                                                                                         tool_shed=tool_shed,
                                                                                         name=name,
                                                                                         owner=owner,
                                                                                         changeset_revision=text )
    return repository

def get_repository_file_contents( file_path ):
    """Return the display-safe contents of a repository file for display in a browser."""
    if checkers.is_gzip( file_path ):
        return '<br/>gzip compressed file<br/>'
    elif checkers.is_bz2( file_path ):
        return '<br/>bz2 compressed file<br/>'
    elif checkers.check_zip( file_path ):
        return '<br/>zip compressed file<br/>'
    elif checkers.check_binary( file_path ):
        return '<br/>Binary file<br/>'
    else:
        safe_str = ''
        for i, line in enumerate( open( file_path ) ):
            safe_str = '%s%s' % ( safe_str, to_html_string( line ) )
            # Stop reading after string is larger than MAX_CONTENT_SIZE.
            if len( safe_str ) > MAX_CONTENT_SIZE:
                large_str = \
                    '<br/>File contents truncated because file size is larger than maximum viewing size of %s<br/>' % \
                    util.nice_size( MAX_CONTENT_SIZE )
                safe_str = '%s%s' % ( safe_str, large_str )
                break
        if len( safe_str ) > MAX_DISPLAY_SIZE:
            # Eliminate the middle of the file to display a file no larger than MAX_DISPLAY_SIZE.  This may not be ideal if the file is larger
            # than MAX_CONTENT_SIZE.
            join_by_str = \
                "<br/><br/>...some text eliminated here because file size is larger than maximum viewing size of %s...<br/><br/>" % \
                util.nice_size( MAX_DISPLAY_SIZE )
            safe_str = util.shrink_string_by_size( safe_str, MAX_DISPLAY_SIZE, join_by=join_by_str, left_larger=True, beginning_on_size_error=True )
        return safe_str

def get_repository_files( trans, folder_path ):
    """Return the file hierarchy of a tool shed repository."""
    contents = []
    for item in os.listdir( folder_path ):
        # Skip .hg directories
        if item.startswith( '.hg' ):
            continue
        if os.path.isdir( os.path.join( folder_path, item ) ):
            # Append a '/' character so that our jquery dynatree will function properly.
            item = '%s/' % item
        contents.append( item )
    if contents:
        contents.sort()
    return contents

def get_repository_from_refresh_on_change( trans, **kwd ):
    # The changeset_revision_select_field in several grids performs a refresh_on_change which sends in request parameters like
    # changeset_revison_1, changeset_revision_2, etc.  One of the many select fields on the grid performed the refresh_on_change,
    # so we loop through all of the received values to see which value is not the repository tip.  If we find it, we know the
    # refresh_on_change occurred and we have the necessary repository id and change set revision to pass on.
    repository_id = None
    v = None
    for k, v in kwd.items():
        changeset_revision_str = 'changeset_revision_'
        if k.startswith( changeset_revision_str ):
            repository_id = trans.security.encode_id( int( k.lstrip( changeset_revision_str ) ) )
            repository = get_repository_in_tool_shed( trans, repository_id )
            if repository.tip( trans.app ) != v:
                return v, repository
    # This should never be reached - raise an exception?
    return v, None

def get_repository_heads( repo ):
    """Return current repository heads, which are changesets with no child changesets."""
    heads = [ repo[ h ] for h in repo.heads( None ) ]
    return heads

def get_repository_ids_requiring_prior_import_or_install( trans, tsr_ids, repository_dependencies ):
    """
    This method is used in the Tool Shed when exporting a repository and its dependencies, and in Galaxy when a repository and its dependencies
    are being installed.  Inspect the received repository_dependencies and determine if the encoded id of each required repository is in the received
    tsr_ids.  If so, then determine whether that required repository should be imported / installed prior to its dependent repository.  Return a list
    of encoded repository ids, each of which is contained in the received list of tsr_ids, and whose associated repositories must be imported / installed
    prior to the dependent repository associated with the received repository_dependencies.
    """
    prior_tsr_ids = []
    if repository_dependencies:
        for key, rd_tups in repository_dependencies.items():
            if key in [ 'description', 'root_key' ]:
                continue
            for rd_tup in rd_tups:
                tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                    common_util.parse_repository_dependency_tuple( rd_tup )
                # If only_if_compiling_contained_td is False, then the repository dependency is not required to be installed prior to the dependent
                # repository even if prior_installation_required is True.  This is because the only meaningful content of the repository dependency
                # is its contained tool dependency, which is required in order to compile the dependent repository's tool dependency.  In the scenario
                # where the repository dependency is not installed prior to the dependent repository's tool dependency compilation process, the tool
                # dependency compilation framework will install the repository dependency prior to compilation of the dependent repository's tool
                # dependency.
                if not asbool( only_if_compiling_contained_td ):
                    if asbool( prior_installation_required ):
                        if trans.webapp.name == 'galaxy':
                            # We store the port, if one exists, in the database.
                            tool_shed = common_util.remove_protocol_from_tool_shed_url( tool_shed )
                            repository = get_repository_for_dependency_relationship( trans.app, tool_shed, name, owner, changeset_revision )
                        else:
                            repository = get_repository_by_name_and_owner( trans.app, name, owner )
                        if repository:
                            encoded_repository_id = trans.security.encode_id( repository.id )
                            if encoded_repository_id in tsr_ids:
                                prior_tsr_ids.append( encoded_repository_id )
    return prior_tsr_ids

def get_repository_in_tool_shed( trans, id ):
    """Get a repository on the tool shed side from the database via id."""
    return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )

def get_repository_metadata_by_changeset_revision( trans, id, changeset_revision ):
    """Get metadata for a specified repository change set from the database."""
    # Make sure there are no duplicate records, and return the single unique record for the changeset_revision.
    # Duplicate records were somehow created in the past.  The cause of this issue has been resolved, but we'll
    # leave this method as is for a while longer to ensure all duplicate records are removed.
    all_metadata_records = trans.sa_session.query( trans.model.RepositoryMetadata ) \
                                           .filter( and_( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ),
                                                          trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                                           .order_by( trans.model.RepositoryMetadata.table.c.update_time.desc() ) \
                                           .all()
    if len( all_metadata_records ) > 1:
        # Delete all records older than the last one updated.
        for repository_metadata in all_metadata_records[ 1: ]:
            trans.sa_session.delete( repository_metadata )
            trans.sa_session.flush()
        return all_metadata_records[ 0 ]
    elif all_metadata_records:
        return all_metadata_records[ 0 ]
    return None

def get_repository_metadata_by_id( trans, id ):
    return trans.sa_session.query( trans.model.RepositoryMetadata ).get( trans.security.decode_id( id ) )

def get_repository_owner( cleaned_repository_url ):
    """Gvien a "cleaned" repository clone URL, return the owner of the repository."""
    items = cleaned_repository_url.split( '/repos/' )
    repo_path = items[ 1 ]
    if repo_path.startswith( '/' ):
        repo_path = repo_path.replace( '/', '', 1 )
    return repo_path.lstrip( '/' ).split( '/' )[ 0 ]

def get_repository_owner_from_clone_url( repository_clone_url ):
    """Given a repository clone URL, return the owner of the repository."""
    tmp_url = common_util.remove_protocol_and_user_from_clone_url( repository_clone_url )
    tool_shed = tmp_url.split( '/repos/' )[ 0 ].rstrip( '/' )
    return get_repository_owner( tmp_url )

def get_repository_query( app ):
    if app.name == "galaxy":
        query = app.install_model.context.query( app.install_model.ToolShedRepository )
    else:
        query = app.model.context.query( app.model.Repository )
    return query

def get_repository_tools_tups( app, metadata_dict ):
    """Return a list of tuples of the form (relative_path, guid, tool) for each tool defined in the received tool shed repository metadata."""
    repository_tools_tups = []
    index, shed_conf_dict = get_shed_tool_conf_dict( app, metadata_dict.get( 'shed_config_filename' ) )
    if 'tools' in metadata_dict:
        for tool_dict in metadata_dict[ 'tools' ]:
            load_relative_path = relative_path = tool_dict.get( 'tool_config', None )
            if shed_conf_dict.get( 'tool_path' ):
                load_relative_path = os.path.join( shed_conf_dict.get( 'tool_path' ), relative_path )
            guid = tool_dict.get( 'guid', None )
            if relative_path and guid:
                tool = app.toolbox.load_tool( os.path.abspath( load_relative_path ), guid=guid )
            else:
                tool = None
            if tool:
                repository_tools_tups.append( ( relative_path, guid, tool ) )
    return repository_tools_tups

def get_reversed_changelog_changesets( repo ):
    """Return a list of changesets in reverse order from that provided by the repository manifest."""
    reversed_changelog = []
    for changeset in repo.changelog:
        reversed_changelog.insert( 0, changeset )
    return reversed_changelog

def get_shed_tool_conf_dict( app, shed_tool_conf ):
    """Return the in-memory version of the shed_tool_conf file, which is stored in the config_elems entry in the shed_tool_conf_dict associated with the file."""
    for index, shed_tool_conf_dict in enumerate( app.toolbox.shed_tool_confs ):
        if shed_tool_conf == shed_tool_conf_dict[ 'config_filename' ]:
            return index, shed_tool_conf_dict
        else:
            file_name = strip_path( shed_tool_conf_dict[ 'config_filename' ] )
            if shed_tool_conf == file_name:
                return index, shed_tool_conf_dict

def get_skip_tool_test_by_changeset_revision( trans, changeset_revision ):
    """Return a skip_tool_test record whose initial_changeset_revision is the received changeset_revision."""
    # There should only be one, but we'll use first() so callers won't have to handle exceptions.
    return trans.sa_session.query( trans.model.SkipToolTest ) \
                           .filter( trans.model.SkipToolTest.table.c.initial_changeset_revision == changeset_revision ) \
                           .first()

def get_tool_panel_config_tool_path_install_dir( app, repository ):
    """
    Return shed-related tool panel config, the tool_path configured in it, and the relative path to
    the directory where the repository is installed.  This method assumes all repository tools are
    defined in a single shed-related tool panel config.
    """
    tool_shed = common_util.remove_port_from_tool_shed_url( str( repository.tool_shed ) )
    relative_install_dir = '%s/repos/%s/%s/%s' % ( tool_shed,
                                                   str( repository.owner ),
                                                   str( repository.name ),
                                                   str( repository.installed_changeset_revision ) )
    # Get the relative tool installation paths from each of the shed tool configs.
    shed_config_dict = repository.get_shed_config_dict( app )
    if not shed_config_dict:
        # Just pick a semi-random shed config.
        for shed_config_dict in app.toolbox.shed_tool_confs:
            if ( repository.dist_to_shed and shed_config_dict[ 'config_filename' ] == app.config.migrated_tools_config ) \
                or ( not repository.dist_to_shed and shed_config_dict[ 'config_filename' ] != app.config.migrated_tools_config ):
                break
    shed_tool_conf = shed_config_dict[ 'config_filename' ]
    tool_path = shed_config_dict[ 'tool_path' ]
    return shed_tool_conf, tool_path, relative_install_dir

def get_tool_path_by_shed_tool_conf_filename( trans, shed_tool_conf ):
    """
    Return the tool_path config setting for the received shed_tool_conf file by searching the tool box's in-memory list of shed_tool_confs for the
    dictionary whose config_filename key has a value matching the received shed_tool_conf.
    """
    for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
        config_filename = shed_tool_conf_dict[ 'config_filename' ]
        if config_filename == shed_tool_conf:
            return shed_tool_conf_dict[ 'tool_path' ]
        else:
            file_name = strip_path( config_filename )
            if file_name == shed_tool_conf:
                return shed_tool_conf_dict[ 'tool_path' ]
    return None

def get_tool_shed_from_clone_url( repository_clone_url ):
    tmp_url = common_util.remove_protocol_and_user_from_clone_url( repository_clone_url )
    return tmp_url.split( '/repos/' )[ 0 ].rstrip( '/' )

def get_tool_shed_repository_by_id( trans, repository_id ):
    """Return a tool shed repository database record defined by the id."""
    # This method is used only in Galaxy, not the tool shed.
    return trans.install_model.context.query( trans.install_model.ToolShedRepository ) \
                                      .filter( trans.install_model.ToolShedRepository.table.c.id == trans.security.decode_id( repository_id ) ) \
                                      .first()

def get_tool_shed_repository_by_shed_name_owner_changeset_revision( app, tool_shed, name, owner, changeset_revision ):
    """
    Return a tool shed repository database record defined by the combination of a tool_shed, repository name,
    repository owner and current changeet_revision.
    """
    # This method is used only in Galaxy, not the Tool Shed.
    repository_query = get_repository_query( app )
    # We store the port, if one exists, in the database.
    tool_shed = common_util.remove_protocol_from_tool_shed_url( tool_shed )
    return repository_query \
        .filter( and_( app.install_model.ToolShedRepository.table.c.tool_shed == tool_shed,
                 app.install_model.ToolShedRepository.table.c.name == name,
                 app.install_model.ToolShedRepository.table.c.owner == owner,
                 app.install_model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
        .first()

def get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( app, tool_shed, name, owner,
                                                                              installed_changeset_revision ):
    """
    Return a tool shed repository database record defined by the combination of a tool_shed,
    repository name, repository owner and installed_changeet_revision.
    """
    # This method is used only in Galaxy, not the tool shed.
    repository_query = get_repository_query( app )
    # We store the port, if one exists, in the database.
    tool_shed = common_util.remove_protocol_from_tool_shed_url( tool_shed )
    return repository_query \
        .filter( and_( app.install_model.ToolShedRepository.table.c.tool_shed == tool_shed,
                 app.install_model.ToolShedRepository.table.c.name == name,
                 app.install_model.ToolShedRepository.table.c.owner == owner,
                 app.install_model.ToolShedRepository.table.c.installed_changeset_revision == installed_changeset_revision ) ) \
        .first()

def get_tool_shed_status_for_installed_repository( app, repository ):
    """
    Send a request to the tool shed to retrieve information about newer installable repository revisions,
    current revision updates, whether the repository revision is the latest downloadable revision, and
    whether the repository has been deprecated in the tool shed.  The received repository is a ToolShedRepository
    object from Galaxy.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( app, str( repository.tool_shed ) )
    params = '?name=%s&owner=%s&changeset_revision=%s' % ( str( repository.name ),
                                                           str( repository.owner ),
                                                           str( repository.changeset_revision ) )
    url = common_util.url_join( tool_shed_url,
                                'repository/status_for_installed_repository%s' % params )
    try:
        encoded_tool_shed_status_dict = common_util.tool_shed_get( app, tool_shed_url, url )
        tool_shed_status_dict = encoding_util.tool_shed_decode( encoded_tool_shed_status_dict )
        return tool_shed_status_dict
    except HTTPError, e:
        # This should handle backward compatility to the Galaxy 12/20/12 release.  We used to only handle updates for an installed revision
        # using a boolean value.
        log.debug( "Error attempting to get tool shed status for installed repository %s: %s\nAttempting older 'check_for_updates' method.\n" % \
            ( str( repository.name ), str( e ) ) )
        params = '?name=%s&owner=%s&changeset_revision=%s&from_update_manager=True' % ( str( repository.name ),
                                                                                        str( repository.owner ),
                                                                                        str( repository.changeset_revision ) )
        url = common_util.url_join( tool_shed_url,
                                    'repository/check_for_updates%s' % params )
        try:
            # The value of text will be 'true' or 'false', depending upon whether there is an update available for the installed revision.
            text = common_util.tool_shed_get( app, tool_shed_url, url )
            return dict( revision_update=text )
        except Exception, e:
            # The required tool shed may be unavailable, so default the revision_update value to 'false'.
            return dict( revision_update='false' )
    except Exception, e:
        log.exception( "Error attempting to get tool shed status for installed repository %s: %s" % ( str( repository.name ), str( e ) ) )
        return {}

def get_tool_shed_repository_status_label( trans, tool_shed_repository=None, name=None, owner=None, changeset_revision=None, repository_clone_url=None ):
    """Return a color-coded label for the status of the received tool-shed_repository installed into Galaxy."""
    if tool_shed_repository is None:
        if name is not None and owner is not None and repository_clone_url is not None:
            tool_shed = get_tool_shed_from_clone_url( repository_clone_url )
            tool_shed_repository = get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( trans.app,
                                                                                                             tool_shed,
                                                                                                             name,
                                                                                                             owner,
                                                                                                             changeset_revision )
    if tool_shed_repository:
        status_label = tool_shed_repository.status
        if tool_shed_repository.status in [ trans.install_model.ToolShedRepository.installation_status.CLONING,
                                            trans.install_model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                            trans.install_model.ToolShedRepository.installation_status.INSTALLING_REPOSITORY_DEPENDENCIES,
                                            trans.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                            trans.install_model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES ]:
            bgcolor = trans.install_model.ToolShedRepository.states.INSTALLING
        elif tool_shed_repository.status in [ trans.install_model.ToolShedRepository.installation_status.NEW,
                                              trans.install_model.ToolShedRepository.installation_status.UNINSTALLED ]:
            bgcolor = trans.install_model.ToolShedRepository.states.UNINSTALLED
        elif tool_shed_repository.status in [ trans.install_model.ToolShedRepository.installation_status.ERROR ]:
            bgcolor = trans.install_model.ToolShedRepository.states.ERROR
        elif tool_shed_repository.status in [ trans.install_model.ToolShedRepository.installation_status.DEACTIVATED ]:
            bgcolor = trans.install_model.ToolShedRepository.states.WARNING
        elif tool_shed_repository.status in [ trans.install_model.ToolShedRepository.installation_status.INSTALLED ]:
            if tool_shed_repository.repository_dependencies_being_installed:
                bgcolor = trans.install_model.ToolShedRepository.states.WARNING
                status_label = '%s, %s' % ( status_label, trans.install_model.ToolShedRepository.installation_status.INSTALLING_REPOSITORY_DEPENDENCIES )
            elif tool_shed_repository.missing_repository_dependencies:
                bgcolor = trans.install_model.ToolShedRepository.states.WARNING
                status_label = '%s, missing repository dependencies' % status_label
            elif tool_shed_repository.tool_dependencies_being_installed:
                bgcolor = trans.install_model.ToolShedRepository.states.WARNING
                status_label = '%s, %s' % (status_label, trans.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
            elif tool_shed_repository.missing_tool_dependencies:
                bgcolor = trans.install_model.ToolShedRepository.states.WARNING
                status_label = '%s, missing tool dependencies' % status_label
            else:
                bgcolor = trans.install_model.ToolShedRepository.states.OK
        else:
            bgcolor = trans.install_model.ToolShedRepository.states.ERROR
    else:
        bgcolor = trans.install_model.ToolShedRepository.states.WARNING
        status_label = 'unknown status'
    return '<div class="count-box state-color-%s">%s</div>' % ( bgcolor, status_label )

def get_updated_changeset_revisions( trans, name, owner, changeset_revision ):
    """
    Return a string of comma-separated changeset revision hashes for all available updates to the received changeset
    revision for the repository defined by the received name and owner.
    """
    repository = get_repository_by_name_and_owner( trans.app, name, owner )
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( hg_util.get_configured_ui(), repo_dir )
    # Get the upper bound changeset revision.
    upper_bound_changeset_revision = get_next_downloadable_changeset_revision( repository, repo, changeset_revision )
    # Build the list of changeset revision hashes defining each available update up to, but excluding, upper_bound_changeset_revision.
    changeset_hashes = []
    for changeset in reversed_lower_upper_bounded_changelog( repo, changeset_revision, upper_bound_changeset_revision ):
        # Make sure to exclude upper_bound_changeset_revision.
        if changeset != upper_bound_changeset_revision:
            changeset_hashes.append( str( repo.changectx( changeset ) ) )
    if changeset_hashes:
        changeset_hashes_str = ','.join( changeset_hashes )
        return changeset_hashes_str
    return ''

def get_updated_changeset_revisions_from_tool_shed( app, tool_shed_url, name, owner, changeset_revision ):
    """
    Get all appropriate newer changeset revisions for the repository defined by
    the received tool_shed_url / name / owner combination.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( app, tool_shed_url )
    if tool_shed_url is None or name is None or owner is None or changeset_revision is None:
        message = "Unable to get updated changeset revisions from the Tool Shed because one or more of the following "
        message += "required parameters is None: tool_shed_url: %s, name: %s, owner: %s, changeset_revision: %s " % \
            ( str( tool_shed_url ), str( name ), str( owner ), str( changeset_revision ) )
        raise Exception( message )
    params = '?name=%s&owner=%s&changeset_revision=%s' % ( name, owner, changeset_revision )
    url = common_util.url_join( tool_shed_url,
                                'repository/updated_changeset_revisions%s' % params )
    text = common_util.tool_shed_get( app, tool_shed_url, url )
    return text

def get_user( trans, id ):
    """Get a user from the database by id."""
    return trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( id ) )

def get_user_by_username( app, username ):
    """Get a user from the database by username."""
    sa_session = app.model.context.current
    try:
        user = sa_session.query( app.model.User ) \
                         .filter( app.model.User.table.c.username == username ) \
                         .one()
        return user
    except Exception, e:
        return None

def handle_email_alerts( trans, repository, content_alert_str='', new_repo_alert=False, admin_only=False ):
    """
    There are 2 complementary features that enable a tool shed user to receive email notification:
    1. Within User Preferences, they can elect to receive email when the first (or first valid)
       change set is produced for a new repository.
    2. When viewing or managing a repository, they can check the box labeled "Receive email alerts"
       which caused them to receive email alerts when updates to the repository occur.  This same feature
       is available on a per-repository basis on the repository grid within the tool shed.

    There are currently 4 scenarios for sending email notification when a change is made to a repository:
    1. An admin user elects to receive email when the first change set is produced for a new repository
       from User Preferences.  The change set does not have to include any valid content.  This allows for
       the capture of inappropriate content being uploaded to new repositories.
    2. A regular user elects to receive email when the first valid change set is produced for a new repository
       from User Preferences.  This differs from 1 above in that the user will not receive email until a
       change set tha tincludes valid content is produced.
    3. An admin user checks the "Receive email alerts" check box on the manage repository page.  Since the
       user is an admin user, the email will include information about both HTML and image content that was
       included in the change set.
    4. A regular user checks the "Receive email alerts" check box on the manage repository page.  Since the
       user is not an admin user, the email will not include any information about both HTML and image content
       that was included in the change set.
    """
    repo_dir = repository.repo_path( trans.app )
    repo = hg.repository( hg_util.get_configured_ui(), repo_dir )
    sharable_link = generate_sharable_link_for_repository_in_tool_shed( trans, repository, changeset_revision=None )
    smtp_server = trans.app.config.smtp_server
    if smtp_server and ( new_repo_alert or repository.email_alerts ):
        # Send email alert to users that want them.
        if trans.app.config.email_from is not None:
            email_from = trans.app.config.email_from
        elif trans.request.host.split( ':' )[0] == 'localhost':
            email_from = 'galaxy-no-reply@' + socket.getfqdn()
        else:
            email_from = 'galaxy-no-reply@' + trans.request.host.split( ':' )[0]
        tip_changeset = repo.changelog.tip()
        ctx = repo.changectx( tip_changeset )
        try:
            username = ctx.user().split()[0]
        except:
            username = ctx.user()
        # We'll use 2 template bodies because we only want to send content
        # alerts to tool shed admin users.
        if new_repo_alert:
            template = new_repo_email_alert_template
        else:
            template = email_alert_template
        display_date = hg_util.get_readable_ctx_date( ctx )
        admin_body = string.Template( template ).safe_substitute( host=trans.request.host,
                                                                  sharable_link=sharable_link,
                                                                  repository_name=repository.name,
                                                                  revision='%s:%s' %( str( ctx.rev() ), ctx ),
                                                                  display_date=display_date,
                                                                  description=ctx.description(),
                                                                  username=username,
                                                                  content_alert_str=content_alert_str )
        body = string.Template( template ).safe_substitute( host=trans.request.host,
                                                            sharable_link=sharable_link,
                                                            repository_name=repository.name,
                                                            revision='%s:%s' %( str( ctx.rev() ), ctx ),
                                                            display_date=display_date,
                                                            description=ctx.description(),
                                                            username=username,
                                                            content_alert_str='' )
        admin_users = trans.app.config.get( "admin_users", "" ).split( "," )
        frm = email_from
        if new_repo_alert:
            subject = "Galaxy tool shed alert for new repository named %s" % str( repository.name )
            subject = subject[ :80 ]
            email_alerts = []
            for user in trans.sa_session.query( trans.model.User ) \
                                        .filter( and_( trans.model.User.table.c.deleted == False,
                                                       trans.model.User.table.c.new_repo_alert == True ) ):
                if admin_only:
                    if user.email in admin_users:
                        email_alerts.append( user.email )
                else:
                    email_alerts.append( user.email )
        else:
            subject = "Galaxy tool shed update alert for repository named %s" % str( repository.name )
            email_alerts = json.from_json_string( repository.email_alerts )
        for email in email_alerts:
            to = email.strip()
            # Send it
            try:
                if to in admin_users:
                    util.send_mail( frm, to, subject, admin_body, trans.app.config )
                else:
                    util.send_mail( frm, to, subject, body, trans.app.config )
            except Exception, e:
                log.exception( "An error occurred sending a tool shed repository update alert by email." )

def have_shed_tool_conf_for_install( trans ):
    if not trans.app.toolbox.shed_tool_confs:
        return False
    migrated_tools_conf_path, migrated_tools_conf_name = os.path.split( trans.app.config.migrated_tools_config )
    for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
        shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
        shed_tool_conf_path, shed_tool_conf_name = os.path.split( shed_tool_conf )
        if shed_tool_conf_name != migrated_tools_conf_name:
            return True
    return False

def open_repository_files_folder( trans, folder_path ):
    """Return a list of dictionaries, each of which contains information for a file or directory contained within a directory in a repository file hierarchy."""
    try:
        files_list = get_repository_files( trans, folder_path )
    except OSError, e:
        if str( e ).find( 'No such file or directory' ) >= 0:
            # We have a repository with no contents.
            return []
    folder_contents = []
    for filename in files_list:
        is_folder = False
        if filename and filename[ -1 ] == os.sep:
            is_folder = True
        if filename:
            full_path = os.path.join( folder_path, filename )
            node = { "title" : filename,
                     "isFolder" : is_folder,
                     "isLazy" : is_folder,
                     "tooltip" : full_path,
                     "key" : full_path }
            folder_contents.append( node )
    return folder_contents

def pretty_print( dict=None ):
    if dict is not None:
        return json.to_json_string( dict, sort_keys=True, indent=4 )

def remove_dir( dir ):
    """Attempt to remove a directory from disk."""
    if dir:
        if os.path.exists( dir ):
            try:
                shutil.rmtree( dir )
            except:
                pass

def remove_file( file_name ):
    """Attempt to remove a file from disk."""
    if file_name:
        if os.path.exists( file_name ):
            try:
                os.remove( file_name )
            except:
                pass

def repository_was_previously_installed( trans, tool_shed_url, repository_name, repo_info_tuple ):
    """
    Find out if a repository is already installed into Galaxy - there are several scenarios where this
    is necessary.  For example, this method will handle the case where the repository was previously
    installed using an older changeset_revsion, but later the repository was updated in the tool shed
    and now we're trying to install the latest changeset revision of the same repository instead of
    updating the one that was previously installed.  We'll look in the database instead of on disk since
    the repository may be currently uninstalled.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( trans.app, tool_shed_url )
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
        get_repo_info_tuple_contents( repo_info_tuple )
    tool_shed = get_tool_shed_from_clone_url( repository_clone_url )
    # See if we can locate the repository using the value of changeset_revision.
    tool_shed_repository = get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( trans.app,
                                                                                                     tool_shed,
                                                                                                     repository_name,
                                                                                                     repository_owner,
                                                                                                     changeset_revision )
    if tool_shed_repository:
        return tool_shed_repository, changeset_revision
    # Get all previous changeset revisions from the tool shed for the repository back to, but excluding,
    # the previous valid changeset revision to see if it was previously installed using one of them.
    params = '?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s' % ( url_for( '/', qualified=True ),
                                                                         str( repository_name ),
                                                                         str( repository_owner ),
                                                                         changeset_revision )
    url = common_util.url_join( tool_shed_url,
                                'repository/previous_changeset_revisions%s' % params )
    text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
    if text:
        changeset_revisions = util.listify( text )
        for previous_changeset_revision in changeset_revisions:
            tool_shed_repository = get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( trans.app,
                                                                                                             tool_shed,
                                                                                                             repository_name,
                                                                                                             repository_owner,
                                                                                                             previous_changeset_revision )
            if tool_shed_repository:
                return tool_shed_repository, previous_changeset_revision
    return None, None

def reset_previously_installed_repository( trans, repository ):
    """
    Reset the atrributes of a tool_shed_repository that was previsouly installed.  The repository will be in some state other than INSTALLED,
    so all atributes will be set to the default NEW state.  This will enable the repository to be freshly installed.
    """
    debug_msg = "Resetting tool_shed_repository '%s' for installation.\n" % str( repository.name )
    debug_msg += "The current state of the tool_shed_repository is:\n"
    debug_msg += "deleted: %s\n" % str( repository.deleted )
    debug_msg += "tool_shed_status: %s\n" % str( repository.tool_shed_status )
    debug_msg += "uninstalled: %s\n" % str( repository.uninstalled )
    debug_msg += "status: %s\n" % str( repository.status )
    debug_msg += "error_message: %s\n" % str( repository.error_message )
    log.debug( debug_msg )
    repository.deleted = False
    repository.tool_shed_status = None
    repository.uninstalled = False
    repository.status = trans.install_model.ToolShedRepository.installation_status.NEW
    repository.error_message = None
    trans.install_model.context.add( repository )
    trans.install_model.context.flush()

def reversed_lower_upper_bounded_changelog( repo, excluded_lower_bounds_changeset_revision, included_upper_bounds_changeset_revision ):
    """
    Return a reversed list of changesets in the repository changelog after the excluded_lower_bounds_changeset_revision, but up to and
    including the included_upper_bounds_changeset_revision.  The value of excluded_lower_bounds_changeset_revision will be the value of
    INITIAL_CHANGELOG_HASH if no valid changesets exist before included_upper_bounds_changeset_revision.
    """
    # To set excluded_lower_bounds_changeset_revision, calling methods should do the following, where the value of changeset_revision
    # is a downloadable changeset_revision.
    # excluded_lower_bounds_changeset_revision = get_previous_metadata_changeset_revision( repository, repo, changeset_revision, downloadable=? )
    if excluded_lower_bounds_changeset_revision == INITIAL_CHANGELOG_HASH:
        appending_started = True
    else:
        appending_started = False
    reversed_changelog = []
    for changeset in repo.changelog:
        changeset_hash = str( repo.changectx( changeset ) )
        if appending_started:
            reversed_changelog.insert( 0, changeset )
        if changeset_hash == excluded_lower_bounds_changeset_revision and not appending_started:
            appending_started = True
        if changeset_hash == included_upper_bounds_changeset_revision:
            break
    return reversed_changelog

def reversed_upper_bounded_changelog( repo, included_upper_bounds_changeset_revision ):
    """Return a reversed list of changesets in the repository changelog up to and including the included_upper_bounds_changeset_revision."""
    return reversed_lower_upper_bounded_changelog( repo, INITIAL_CHANGELOG_HASH, included_upper_bounds_changeset_revision )

def set_image_paths( app, encoded_repository_id, text ):
    """
    Handle tool help image display for tools that are contained in repositories in the tool shed or installed into Galaxy as well as image
    display in repository README files.  This method will determine the location of the image file and return the path to it that will enable
    the caller to open the file.
    """
    if text:
        if app.name == 'galaxy':
            route_to_images = 'admin_toolshed/static/images/%s' % encoded_repository_id
        else:
            # We're in the tool shed.
            route_to_images = '/repository/static/images/%s' % encoded_repository_id
        # We used to require $PATH_TO_IMAGES, but we now eliminate it if it's used.
        text = text.replace( '$PATH_TO_IMAGES', '' )
        # Eliminate the invalid setting of ./static/images since the routes will properly display images contained in that directory.
        text = text.replace( './static/images', '' )
        # Eliminate the default setting of /static/images since the routes will properly display images contained in that directory.
        text = text.replace( '/static/images', '' )
        # Use regex to instantiate routes into the defined image paths, but replace paths that start with neither http:// nor https://,
        # which will allow for settings like .. images:: http_files/images/help.png
        for match in re.findall( '.. image:: (?!http)/?(.+)', text ):
            text = text.replace( match, match.replace( '/', '%2F' ) )
        text = re.sub( r'\.\. image:: (?!https?://)/?(.+)', r'.. image:: %s/\1' % route_to_images, text )
    return text

def set_only_if_compiling_contained_td( repository, required_repository ):
    """Return True if the received required_repository is only needed to compile a tool dependency defined for the received repository."""
    # This method is called only from Galaxy when rendering repository dependencies for an installed tool shed repository.
    # TODO: Do we need to check more than changeset_revision here?
    required_repository_tup = [ required_repository.tool_shed, required_repository.name, required_repository.owner, required_repository.changeset_revision ]
    for tup in repository.tuples_of_repository_dependencies_needed_for_compiling_td:
        partial_tup = tup[ 0:4 ]
        if partial_tup == required_repository_tup:
            return 'True'
    return 'False'

def set_prior_installation_required( app, repository, required_repository ):
    """Return True if the received required_repository must be installed before the received repository."""
    # This method is called only from Galaxy when rendering repository dependencies for an installed Tool Shed repository.
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( app, str( required_repository.tool_shed ) )
    required_repository_tup = [ tool_shed_url,
                                str( required_repository.name ),
                                str( required_repository.owner ),
                                str( required_repository.changeset_revision ) ]
    # Get the list of repository dependency tuples associated with the received repository where prior_installation_required is True.
    required_rd_tups_that_must_be_installed = repository.requires_prior_installation_of
    for required_rd_tup in required_rd_tups_that_must_be_installed:
        # Repository dependency tuples in metadata include a prior_installation_required value, so strip it for comparision.
        partial_required_rd_tup = required_rd_tup[ 0:4 ]
        if partial_required_rd_tup == required_repository_tup:
            # Return the string value of prior_installation_required, which defaults to 'False'.
            return str( required_rd_tup[ 4 ] )
    return 'False'

def size_string( raw_text, size=MAX_DISPLAY_SIZE ):
    """Return a subset of a string (up to MAX_DISPLAY_SIZE) translated to a safe string for display in a browser."""
    if raw_text and len( raw_text ) >= size:
        large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( size )
        raw_text = '%s%s' % ( raw_text[ 0:size ], large_str )
    return raw_text or ''

def stringify( list ):
    if list:
        return ','.join( list )
    return ''

def strip_path( fpath ):
    """Attempt to strip the path from a file name."""
    if not fpath:
        return fpath
    try:
        file_path, file_name = os.path.split( fpath )
    except:
        file_name = fpath
    return file_name

def to_html_string( text ):
    """Translates the characters in text to an html string"""
    if text:
        try:
            text = unicodify( text )
        except UnicodeDecodeError, e:
            return "Error decoding string: %s" % str( e )
        text = unicode( markupsafe.escape( text ) )
        text = text.replace( '\n', '<br/>' )
        text = text.replace( '    ', '&nbsp;&nbsp;&nbsp;&nbsp;' )
        text = text.replace( ' ', '&nbsp;' )
    return text

def tool_shed_from_repository_clone_url( repository_clone_url ):
    """Given a repository clone URL, return the tool shed that contains the repository."""
    return common_util.remove_protocol_and_user_from_clone_url( repository_clone_url ).split( '/repos/' )[ 0 ].rstrip( '/' )

def tool_shed_is_this_tool_shed( toolshed_base_url ):
    """Determine if a tool shed is the current tool shed."""
    cleaned_toolshed_base_url = common_util.remove_protocol_from_tool_shed_url( toolshed_base_url )
    cleaned_tool_shed = common_util.remove_protocol_from_tool_shed_url( str( url_for( '/', qualified=True ) ) )
    return cleaned_toolshed_base_url == cleaned_tool_shed

def update_in_shed_tool_config( app, repository ):
    """
    A tool shed repository is being updated so change the shed_tool_conf file.  Parse the config
    file to generate the entire list of config_elems instead of using the in-memory list.
    """
    shed_conf_dict = repository.get_shed_config_dict( app )
    shed_tool_conf = shed_conf_dict[ 'config_filename' ]
    tool_path = shed_conf_dict[ 'tool_path' ]
    tool_panel_dict = generate_tool_panel_dict_from_shed_tool_conf_entries( app, repository )
    repository_tools_tups = get_repository_tools_tups( app, repository.metadata )
    clone_url = common_util.generate_clone_url_for_installed_repository( app, repository )
    cleaned_repository_clone_url = common_util.remove_protocol_and_user_from_clone_url( clone_url )
    tool_shed = tool_shed_from_repository_clone_url( cleaned_repository_clone_url )
    owner = repository.owner
    if not owner:
        owner = get_repository_owner( cleaned_repository_clone_url )
    guid_to_tool_elem_dict = {}
    for tool_config_filename, guid, tool in repository_tools_tups:
        guid_to_tool_elem_dict[ guid ] = generate_tool_elem( tool_shed,
                                                             repository.name,
                                                             repository.changeset_revision,
                                                             repository.owner or '',
                                                             tool_config_filename,
                                                             tool,
                                                             None )
    config_elems = []
    tree, error_message = xml_util.parse_xml( shed_tool_conf )
    if tree:
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'section':
                for i, tool_elem in enumerate( elem ):
                    guid = tool_elem.attrib.get( 'guid' )
                    if guid in guid_to_tool_elem_dict:
                        elem[i] = guid_to_tool_elem_dict[ guid ]
            elif elem.tag == 'tool':
                guid = elem.attrib.get( 'guid' )
                if guid in guid_to_tool_elem_dict:
                    elem = guid_to_tool_elem_dict[ guid ]
            config_elems.append( elem )
        config_elems_to_xml_file( app, config_elems, shed_tool_conf, tool_path )

def update_tool_shed_repository_status( app, tool_shed_repository, status, error_message=None ):
    """Update the status of a tool shed repository in the process of being installed into Galaxy."""
    context = app.install_model.context
    tool_shed_repository.status = status
    if error_message:
        tool_shed_repository.error_message = str( error_message )
    context.add( tool_shed_repository )
    context.flush()
