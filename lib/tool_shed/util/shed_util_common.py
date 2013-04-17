import logging
import os
import shutil
import string
import tempfile
from datetime import datetime
from time import gmtime
from time import strftime
from galaxy import util
from galaxy.util import json
from galaxy.web import url_for
from galaxy.web.form_builder import SelectField
from galaxy.datatypes import checkers
from galaxy.model.orm import and_
import sqlalchemy.orm.exc
from tool_shed.util import common_util
from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree
from elementtree import ElementInclude
from elementtree.ElementTree import Element
from elementtree.ElementTree import SubElement

eggs.require( 'markupsafe' )
import markupsafe
        
log = logging.getLogger( __name__ )

INITIAL_CHANGELOG_HASH = '000000000000'
MAX_CONTENT_SIZE = 32768
VALID_CHARS = set( string.letters + string.digits + "'\"-=_.()/+*^,:?!#[]%\\$@;{}&<>" )

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

def build_repository_ids_select_field( trans, name='repository_ids', multiple=True, display='checkboxes' ):
    """Method called from both Galaxy and the Tool Shed to generate the current list of repositories for resetting metadata."""
    repositories_select_field = SelectField( name=name, multiple=multiple, display=display )
    if trans.webapp.name == 'tool_shed':
        # We're in the tool shed.
        for repository in trans.sa_session.query( trans.model.Repository ) \
                                          .filter( trans.model.Repository.table.c.deleted == False ) \
                                          .order_by( trans.model.Repository.table.c.name,
                                                     trans.model.Repository.table.c.user_id ):
            owner = repository.user.username
            option_label = '%s (%s)' % ( repository.name, owner )
            option_value = '%s' % trans.security.encode_id( repository.id )
            repositories_select_field.add_option( option_label, option_value )
    else:
        # We're in Galaxy.
        for repository in trans.sa_session.query( trans.model.ToolShedRepository ) \
                                          .filter( trans.model.ToolShedRepository.table.c.uninstalled == False ) \
                                          .order_by( trans.model.ToolShedRepository.table.c.name,
                                                     trans.model.ToolShedRepository.table.c.owner ):
            option_label = '%s (%s)' % ( repository.name, repository.owner )
            option_value = trans.security.encode_id( repository.id )
            repositories_select_field.add_option( option_label, option_value )
    return repositories_select_field

def changeset_is_malicious( trans, id, changeset_revision, **kwd ):
    """Check the malicious flag in repository metadata for a specified change set"""
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
    if repository_metadata:
        return repository_metadata.malicious
    return False

def changeset_is_valid( app, repository, changeset_revision ):
    """Make sure a changeset hash is valid for a specified repository."""
    repo = hg.repository( get_configured_ui(), repository.repo_path( app ) )
    for changeset in repo.changelog:
        changeset_hash = str( repo.changectx( changeset ) )
        if changeset_revision == changeset_hash:
            return True
    return False

def clean_repository_clone_url( repository_clone_url ):
    """Return a URL that can be used to clone a tool shed repository, eliminating the protocol and user if either exists."""
    if repository_clone_url.find( '@' ) > 0:
        # We have an url that includes an authenticated user, something like:
        # http://test@bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split( '@' )
        tmp_url = items[ 1 ]
    elif repository_clone_url.find( '//' ) > 0:
        # We have an url that includes only a protocol, something like:
        # http://bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split( '//' )
        tmp_url = items[ 1 ]
    else:
        tmp_url = repository_clone_url
    return tmp_url

def clean_tool_shed_url( tool_shed_url ):
    """Return a tool shed URL, eliminating the port if it exists."""
    if tool_shed_url.find( ':' ) > 0:
        # Eliminate the port, if any, since it will result in an invalid directory name.
        return tool_shed_url.split( ':' )[ 0 ]
    return tool_shed_url.rstrip( '/' )

def clone_repository( repository_clone_url, repository_file_dir, ctx_rev ):   
    """Clone the repository up to the specified changeset_revision.  No subsequent revisions will be present in the cloned repository."""
    try:
        commands.clone( get_configured_ui(),
                        str( repository_clone_url ),
                        dest=str( repository_file_dir ),
                        pull=True,
                        noupdate=False,
                        rev=util.listify( str( ctx_rev ) ) )
        return True, None
    except Exception, e:
        error_message = 'Error cloning repository: %s' % str( e )
        log.debug( error_message )
        return False, error_message

def config_elems_to_xml_file( app, config_elems, config_filename, tool_path ):
    """Persist the current in-memory list of config_elems to a file named by the value of config_filename."""
    fd, filename = tempfile.mkstemp()
    os.write( fd, '<?xml version="1.0"?>\n' )
    os.write( fd, '<toolbox tool_path="%s">\n' % str( tool_path ) )
    for elem in config_elems:
        os.write( fd, '%s' % util.xml_to_string( elem, pretty=True ) )
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

def create_or_update_tool_shed_repository( app, name, description, installed_changeset_revision, ctx_rev, repository_clone_url, metadata_dict,
                                           status, current_changeset_revision=None, owner='', dist_to_shed=False ):
    """
    Update a tool shed repository record i the Galaxy database with the new information received.  If a record defined by the received tool shed, repository name
    and owner does not exists, create a new record with the received information.
    """
    # The received value for dist_to_shed will be True if the InstallManager is installing a repository that contains tools or datatypes that used
    # to be in the Galaxy distribution, but have been moved to the main Galaxy tool shed.
    log.debug( "Adding new row (or updating an existing row) for repository '%s' in the tool_shed_repository table." % name )
    if current_changeset_revision is None:
        # The current_changeset_revision is not passed if a repository is being installed for the first time.  If a previously installed repository
        # was later uninstalled, this value should be received as the value of that change set to which the repository had been updated just prior
        # to it being uninstalled.
        current_changeset_revision = installed_changeset_revision
    sa_session = app.model.context.current  
    tool_shed = get_tool_shed_from_clone_url( repository_clone_url )
    if not owner:
        owner = get_repository_owner_from_clone_url( repository_clone_url )
    includes_datatypes = 'datatypes' in metadata_dict
    if status in [ app.model.ToolShedRepository.installation_status.DEACTIVATED ]:
        deleted = True
        uninstalled = False
    elif status in [ app.model.ToolShedRepository.installation_status.UNINSTALLED ]:
        deleted = True
        uninstalled = True
    else:
        deleted = False
        uninstalled = False
    tool_shed_repository = get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( app,
                                                                                                     tool_shed,
                                                                                                     name,
                                                                                                     owner,
                                                                                                     installed_changeset_revision )
    if tool_shed_repository:
        tool_shed_repository.description = description
        tool_shed_repository.changeset_revision = current_changeset_revision
        tool_shed_repository.ctx_rev = ctx_rev
        tool_shed_repository.metadata = metadata_dict
        tool_shed_repository.includes_datatypes = includes_datatypes
        tool_shed_repository.deleted = deleted
        tool_shed_repository.uninstalled = uninstalled
        tool_shed_repository.status = status
    else:
        tool_shed_repository = app.model.ToolShedRepository( tool_shed=tool_shed,
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
    sa_session.add( tool_shed_repository )
    sa_session.flush()
    return tool_shed_repository

def generate_clone_url_for_installed_repository( app, repository ):
    """Generate the URL for cloning a repository that has been installed into a Galaxy instance."""
    tool_shed_url = get_url_from_tool_shed( app, repository.tool_shed )
    return url_join( tool_shed_url, 'repos', repository.owner, repository.name )

def generate_clone_url_for_repository_in_tool_shed( trans, repository ):
    """Generate the URL for cloning a repository that is in the tool shed."""
    base_url = url_for( '/', qualified=True ).rstrip( '/' )
    if trans and trans.user:
        protocol, base = base_url.split( '://' )
        username = '%s@' % trans.user.username
        return '%s://%s%s/repos/%s/%s' % ( protocol, username, base, repository.user.username, repository.name )
    else:
        return '%s/repos/%s/%s' % ( base_url, repository.user.username, repository.name )

def generate_clone_url_from_repo_info_tup( repo_info_tup ):
    """Generate teh URL for cloning a repositoyr given a tuple of toolshed, name, owner, changeset_revision."""
    # Example tuple: ['http://localhost:9009', 'blast_datatypes', 'test', '461a4216e8ab', False]
    toolshed, name, owner, changeset_revision, prior_installation_required = parse_repository_dependency_tuple( repo_info_tup )
    # Don't include the changeset_revision in clone urls.
    return url_join( toolshed, 'repos', owner, name )

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
        tool_elem = SubElement( tool_section, 'tool' )
    else:
        tool_elem = Element( 'tool' )
    tool_elem.attrib[ 'file' ] = tool_file_path
    tool_elem.attrib[ 'guid' ] = tool.guid
    tool_shed_elem = SubElement( tool_elem, 'tool_shed' )
    tool_shed_elem.text = tool_shed
    repository_name_elem = SubElement( tool_elem, 'repository_name' )
    repository_name_elem.text = repository_name
    repository_owner_elem = SubElement( tool_elem, 'repository_owner' )
    repository_owner_elem.text = owner
    changeset_revision_elem = SubElement( tool_elem, 'installed_changeset_revision' )
    changeset_revision_elem.text = changeset_revision
    id_elem = SubElement( tool_elem, 'id' )
    id_elem.text = tool.id
    version_elem = SubElement( tool_elem, 'version' )
    version_elem.text = tool.version
    return tool_elem

def generate_tool_guid( repository_clone_url, tool ):
    """
    Generate a guid for the installed tool.  It is critical that this guid matches the guid for
    the tool in the Galaxy tool shed from which it is being installed.  The form of the guid is    
    <tool shed host>/repos/<repository owner>/<repository name>/<tool id>/<tool version>
    """
    tmp_url = clean_repository_clone_url( repository_clone_url )
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
    for tool_dict in metadata[ 'tools' ]:
        guid = tool_dict[ 'guid' ]
        tool_config = tool_dict[ 'tool_config' ]
        file_name = strip_path( tool_config )
        guids_and_configs[ guid ] = file_name
    # Parse the shed_tool_conf file in which all of this repository's tools are defined and generate the tool_panel_dict. 
    tree = util.parse_xml( shed_tool_conf )
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
    Generate a repository installation directory that guarantees repositories with the same name will always be installed in different directories.
    The tool path will be of the form: <tool shed url>/repos/<repository owner>/<repository name>/<installed changeset revision>
    """
    tmp_url = clean_repository_clone_url( repository_clone_url )
    # Now tmp_url is something like: bx.psu.edu:9009/repos/some_username/column
    items = tmp_url.split( '/repos/' )
    tool_shed_url = items[ 0 ]
    repo_path = items[ 1 ]
    tool_shed_url = clean_tool_shed_url( tool_shed_url )
    return url_join( tool_shed_url, 'repos', repo_path, changeset_revision )

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

def get_changectx_for_changeset( repo, changeset_revision, **kwd ):
    """Retrieve a specified changectx from a repository."""
    for changeset in repo.changelog:
        ctx = repo.changectx( changeset )
        if str( ctx ) == changeset_revision:
            return ctx
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

def get_configured_ui():
    """Configure any desired ui settings."""
    _ui = ui.ui()
    # The following will suppress all messages.  This is
    # the same as adding the following setting to the repo
    # hgrc file' [ui] section:
    # quiet = True
    _ui.setconfig( 'ui', 'quiet', True )
    return _ui

def get_ctx_rev( app, tool_shed_url, name, owner, changeset_revision ):
    """
    Send a request to the tool shed to retrieve the ctx_rev for a repository defined by the combination of a name, owner and changeset
    revision.
    """
    url = url_join( tool_shed_url, 
                    'repository/get_ctx_rev?name=%s&owner=%s&changeset_revision=%s' % ( name, owner, changeset_revision ) )
    ctx_rev = common_util.tool_shed_get( app, tool_shed_url, url )
    return ctx_rev

def get_ctx_file_path_from_manifest( filename, repo, changeset_revision ):
    """Get the ctx file path for the latest revision of filename from the repository manifest up to the value of changeset_revision."""
    stripped_filename = strip_path( filename )
    for changeset in reversed_upper_bounded_changelog( repo, changeset_revision ):
        manifest_changeset_revision = str( repo.changectx( changeset ) )
        manifest_ctx = repo.changectx( changeset )
        for ctx_file in manifest_ctx.files():
            ctx_file_name = strip_path( ctx_file )
            if ctx_file_name == stripped_filename:
                return manifest_ctx, ctx_file
    return None, None

def get_file_context_from_ctx( ctx, filename ):
    """Return the mercurial file context for a specified file."""
    # We have to be careful in determining if we found the correct file because multiple files with the same name may be in different directories
    # within ctx if the files were moved within the change set.  For example, in the following ctx.files() list, the former may have been moved to
    # the latter: ['tmap_wrapper_0.0.19/tool_data_table_conf.xml.sample', 'tmap_wrapper_0.3.3/tool_data_table_conf.xml.sample'].  Another scenario
    # is that the file has been deleted.
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

def get_installed_tool_shed_repository( trans, id ):
    """Get a tool shed repository record from the Galaxy database defined by the id."""
    return trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( id ) )

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
                fh = tempfile.NamedTemporaryFile( 'wb', dir=dir )
                tmp_filename = fh.name
                fh.close()
                fh = open( tmp_filename, 'wb' )
                fh.write( fctx.data() )
                fh.close()
                return tmp_filename
    return None

def get_next_downloadable_changeset_revision( repository, repo, after_changeset_revision ):
    """
    Return the installable changeset_revision in the repository changelog after the changeset to which after_changeset_revision refers.  If there
    isn't one, return None.
    """
    changeset_revisions = get_ordered_downloadable_changeset_revisions( repository, repo )
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

def get_or_create_tool_shed_repository( trans, tool_shed, name, owner, changeset_revision ):
    """
    Return a tool shed repository database record defined by the combination of tool shed, repository name, repository owner and changeset_revision
    or installed_changeset_revision.  A new tool shed repository record will be created if one is not located.
    """
    # This method is used only in Galaxy, not the tool shed.
    repository = get_repository_for_dependency_relationship( trans.app, tool_shed, name, owner, changeset_revision )
    if not repository:
        tool_shed_url = get_url_from_tool_shed( trans.app, tool_shed )
        repository_clone_url = os.path.join( tool_shed_url, 'repos', owner, name )
        ctx_rev = get_ctx_rev( trans.app, tool_shed_url, name, owner, changeset_revision )
        repository = create_or_update_tool_shed_repository( app=trans.app,
                                                            name=name,
                                                            description=None,
                                                            installed_changeset_revision=changeset_revision,
                                                            ctx_rev=ctx_rev,
                                                            repository_clone_url=repository_clone_url,
                                                            metadata_dict={},
                                                            status=trans.model.ToolShedRepository.installation_status.NEW,
                                                            current_changeset_revision=None,
                                                            owner=owner,
                                                            dist_to_shed=False )
    return repository

def get_ordered_downloadable_changeset_revisions( repository, repo ):
    """Return an ordered list of changeset_revisions defined by a repository changelog."""
    changeset_tups = []
    for repository_metadata in repository.downloadable_revisions:
        changeset_revision = repository_metadata.changeset_revision
        ctx = get_changectx_for_changeset( repo, changeset_revision )
        if ctx:
            rev = '%04d' % ctx.rev()
        else:
            rev = '-1'
        changeset_tups.append( ( rev, changeset_revision ) )
    sorted_changeset_tups = sorted( changeset_tups )
    sorted_changeset_revisions = [ changeset_tup[ 1 ] for changeset_tup in sorted_changeset_tups ]
    return sorted_changeset_revisions

def get_previous_downloadable_changeset_revision( repository, repo, before_changeset_revision ):
    """
    Return the installable changeset_revision in the repository changelog prior to the changeset to which before_changeset_revision
    refers.  If there isn't one, return the hash value of an empty repository changelog, INITIAL_CHANGELOG_HASH.
    """
    changeset_revisions = get_ordered_downloadable_changeset_revisions( repository, repo )
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

def get_repo_info_tuple_contents( repo_info_tuple ):
    """Take care in handling the repo_info_tuple as it evolves over time as new tool shed features are introduced."""
    if len( repo_info_tuple ) == 6:
        description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple
        repository_dependencies = None
    elif len( repo_info_tuple ) == 7:
        description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = repo_info_tuple
    return description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies

def get_repository_by_id( trans, id ):
    """Get a repository from the database via id."""
    if trans.webapp.name == 'galaxy':
        return trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( id ) )
    else:
        return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )

def get_repository_by_name( app, name ):
    """Get a repository from the database via name."""
    sa_session = app.model.context.current
    if app.name == 'galaxy':
        return sa_session.query( app.model.ToolShedRepository ).filter_by( name=name ).first()
    else:
        return sa_session.query( app.model.Repository ).filter_by( name=name ).first()

def get_repository_by_name_and_owner( app, name, owner ):
    """Get a repository from the database via name and owner"""
    sa_session = app.model.context.current
    if app.name == 'galaxy':
        return sa_session.query( app.model.ToolShedRepository ) \
                         .filter( and_( app.model.ToolShedRepository.table.c.name == name,
                                        app.model.ToolShedRepository.table.c.owner == owner ) ) \
                         .first()
    # We're in the tool shed.
    user = get_user_by_username( app, owner )
    if user:
        return sa_session.query( app.model.Repository ) \
                         .filter( and_( app.model.Repository.table.c.name == name,
                                        app.model.Repository.table.c.user_id == user.id ) ) \
                         .first()
    return None

def get_repository_for_dependency_relationship( app, tool_shed, name, owner, changeset_revision ):
    """Return a tool shed repository database record that is defined by either the current changeset revision or the installed_changeset_revision."""
    # This method is used only in Galaxy, not the tool shed.
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
    return repository

def get_repository_file_contents( file_path ):
    """Return the display-safe contents of a repository file."""
    if checkers.is_gzip( file_path ):
        safe_str = to_safe_string( '\ngzip compressed file\n' )
    elif checkers.is_bz2( file_path ):
        safe_str = to_safe_string( '\nbz2 compressed file\n' )
    elif checkers.check_zip( file_path ):
        safe_str = to_safe_string( '\nzip compressed file\n' )
    elif checkers.check_binary( file_path ):
        safe_str = to_safe_string( '\nBinary file\n' )
    else:
        safe_str = ''
        for i, line in enumerate( open( file_path ) ):
            safe_str = '%s%s' % ( safe_str, to_safe_string( line ) )
            if len( safe_str ) > MAX_CONTENT_SIZE:
                large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
                safe_str = '%s%s' % ( safe_str, to_safe_string( large_str ) )
                break
    return safe_str

def get_repository_files( trans, folder_path ):
    """Return the file hierarchy of a tool shed repository."""
    contents = []
    for item in os.listdir( folder_path ):
        # Skip .hg directories
        if str( item ).startswith( '.hg' ):
            continue
        if os.path.isdir( os.path.join( folder_path, item ) ):
            # Append a '/' character so that our jquery dynatree will function properly.
            item = '%s/' % item
        contents.append( item )
    if contents:
        contents.sort()
    return contents

def get_repository_in_tool_shed( trans, id ):
    """Get a repository on the tool shed side from the database via id."""
    return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )

def get_repository_metadata_by_changeset_revision( trans, id, changeset_revision ):
    """Get metadata for a specified repository change set from the database."""
    # Make sure there are no duplicate records, and return the single unique record for the changeset_revision.  Duplicate records were somehow
    # created in the past.  The cause of this issue has been resolved, but we'll leave this method as is for a while longer to ensure all duplicate
    # records are removed.
    all_metadata_records = trans.sa_session.query( trans.model.RepositoryMetadata ) \
                                           .filter( and_( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ),
                                                          trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                                           .order_by( trans.model.RepositoryMetadata.table.c.update_time.desc() ) \
                                           .all()
    if len( all_metadata_records ) > 1:
        # Delete all recrds older than the last one updated.
        for repository_metadata in all_metadata_records[ 1: ]:
            trans.sa_session.delete( repository_metadata )
            trans.sa_session.flush()
        return all_metadata_records[ 0 ]
    elif all_metadata_records:
        return all_metadata_records[ 0 ]
    return None

def get_repository_owner( cleaned_repository_url ):
    """Gvien a "cleaned" repository clone URL, return the owner of the repository."""
    items = cleaned_repository_url.split( '/repos/' )
    repo_path = items[ 1 ]
    if repo_path.startswith( '/' ):
        repo_path = repo_path.replace( '/', '', 1 )
    return repo_path.lstrip( '/' ).split( '/' )[ 0 ]

def get_repository_owner_from_clone_url( repository_clone_url ):
    """Given a repository clone URL, return the owner of the repository."""
    tmp_url = clean_repository_clone_url( repository_clone_url )
    tool_shed = tmp_url.split( '/repos/' )[ 0 ].rstrip( '/' )
    return get_repository_owner( tmp_url )

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

def get_revision_label( trans, repository, changeset_revision ):
    """Return a string consisting of the human read-able changeset rev and the changeset revision string."""
    repo = hg.repository( get_configured_ui(), repository.repo_path( trans.app ) )
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        return "%s:%s" % ( str( ctx.rev() ), changeset_revision )
    else:
        return "-1:%s" % changeset_revision

def get_rev_label_from_changeset_revision( repo, changeset_revision ):
    """Given a changeset revision hash, return two strings, the changeset rev and the changeset revision hash."""
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        rev = '%04d' % ctx.rev()
        label = "%s:%s" % ( str( ctx.rev() ), changeset_revision )
    else:
        rev = '-1'
        label = "-1:%s" % changeset_revision
    return rev, label

def get_shed_tool_conf_dict( app, shed_tool_conf ):
    """Return the in-memory version of the shed_tool_conf file, which is stored in the config_elems entry in the shed_tool_conf_dict associated with the file."""
    for index, shed_tool_conf_dict in enumerate( app.toolbox.shed_tool_confs ):
        if shed_tool_conf == shed_tool_conf_dict[ 'config_filename' ]:
            return index, shed_tool_conf_dict
        else:
            file_name = strip_path( shed_tool_conf_dict[ 'config_filename' ] )
            if shed_tool_conf == file_name:
                return index, shed_tool_conf_dict

def get_tool_panel_config_tool_path_install_dir( app, repository ):
    """
    Return shed-related tool panel config, the tool_path configured in it, and the relative path to the directory where the repository is installed.
    This method assumes all repository tools are defined in a single shed-related tool panel config.
    """
    tool_shed = clean_tool_shed_url( repository.tool_shed )
    partial_install_dir = '%s/repos/%s/%s/%s' % ( tool_shed, repository.owner, repository.name, repository.installed_changeset_revision )
    # Get the relative tool installation paths from each of the shed tool configs.
    relative_install_dir = None
    shed_config_dict = repository.get_shed_config_dict( app )
    if not shed_config_dict:
        # Just pick a semi-random shed config.
        for shed_config_dict in app.toolbox.shed_tool_confs:
            if ( repository.dist_to_shed and shed_config_dict[ 'config_filename' ] == app.config.migrated_tools_config ) \
                or ( not repository.dist_to_shed and shed_config_dict[ 'config_filename' ] != app.config.migrated_tools_config ):
                break
    shed_tool_conf = shed_config_dict[ 'config_filename' ]
    tool_path = shed_config_dict[ 'tool_path' ]
    relative_install_dir = partial_install_dir
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

def get_tool_shed_repository_by_id( trans, repository_id ):
    """Return a tool shed repository database record defined by the id."""
    # This method is used only in Galaxy, not the tool shed.
    return trans.sa_session.query( trans.model.ToolShedRepository ) \
                           .filter( trans.model.ToolShedRepository.table.c.id == trans.security.decode_id( repository_id ) ) \
                           .first()

def get_tool_shed_repository_by_shed_name_owner_changeset_revision( app, tool_shed, name, owner, changeset_revision ):
    """Return a tool shed repository database record defined by the combination of a tool_shed, repository name, repository owner and current changeet_revision."""
    # This method is used only in Galaxy, not the tool shed.
    sa_session = app.model.context.current
    if tool_shed.find( '//' ) > 0:
        tool_shed = tool_shed.split( '//' )[1]
    tool_shed = tool_shed.rstrip( '/' )
    return sa_session.query( app.model.ToolShedRepository ) \
                     .filter( and_( app.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                    app.model.ToolShedRepository.table.c.name == name,
                                    app.model.ToolShedRepository.table.c.owner == owner,
                                    app.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                     .first()

def get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( app, tool_shed, name, owner, installed_changeset_revision ):
    """Return a tool shed repository database record defined by the combination of a tool_shed, repository name, repository owner and installed_changeet_revision."""
    # This method is used only in Galaxy, not the tool shed.
    sa_session = app.model.context.current
    if tool_shed.find( '//' ) > 0:
        tool_shed = tool_shed.split( '//' )[1]
    tool_shed = tool_shed.rstrip( '/' )
    return sa_session.query( app.model.ToolShedRepository ) \
                     .filter( and_( app.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                    app.model.ToolShedRepository.table.c.name == name,
                                    app.model.ToolShedRepository.table.c.owner == owner,
                                    app.model.ToolShedRepository.table.c.installed_changeset_revision == installed_changeset_revision ) ) \
                     .first()

def get_tool_shed_from_clone_url( repository_clone_url ):
    tmp_url = clean_repository_clone_url( repository_clone_url )
    return tmp_url.split( '/repos/' )[ 0 ].rstrip( '/' )

def get_url_from_tool_shed( app, tool_shed ):
    """
    The value of tool_shed is something like: toolshed.g2.bx.psu.edu.  We need the URL to this tool shed, which is something like:
    http://toolshed.g2.bx.psu.edu/
    """
    for shed_name, shed_url in app.tool_shed_registry.tool_sheds.items():
        if shed_url.find( tool_shed ) >= 0:
            if shed_url.endswith( '/' ):
                shed_url = shed_url.rstrip( '/' )
            return shed_url
    # The tool shed from which the repository was originally installed must no longer be configured in tool_sheds_conf.xml.
    return None

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
    repo = hg.repository( get_configured_ui(), repo_dir )
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
        t, tz = ctx.date()
        date = datetime( *gmtime( float( t ) - tz )[:6] )
        display_date = date.strftime( "%Y-%m-%d" )
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

def handle_galaxy_url( trans, **kwd ):
    galaxy_url = kwd.get( 'galaxy_url', None )
    if galaxy_url:
        trans.set_cookie( galaxy_url, name='toolshedgalaxyurl' )
    else:
        galaxy_url = trans.get_cookie( name='toolshedgalaxyurl' )
    return galaxy_url

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

def parse_repository_dependency_tuple( repository_dependency_tuple, contains_error=False ):
    if contains_error:
        if len( repository_dependency_tuple ) == 5:
            # Metadata should have been reset on the repository containing this repository_dependency definition.
            tool_shed, name, owner, changeset_revision, error = repository_dependency_tuple
            # Default prior_installation_required to False.
            prior_installation_required = False
        elif len( repository_dependency_tuple ) == 6:
            toolshed, name, owner, changeset_revision, prior_installation_required, error = repository_dependency_tuple
        prior_installation_required = util.asbool( str( prior_installation_required ) )
        return toolshed, name, owner, changeset_revision, prior_installation_required, error
    else:
        if len( repository_dependency_tuple ) == 4:
            # Metadata should have been reset on the repository containing this repository_dependency definition.
            tool_shed, name, owner, changeset_revision = repository_dependency_tuple
            # Default prior_installation_required to False.
            prior_installation_required = False
        elif len( repository_dependency_tuple ) == 5:
            tool_shed, name, owner, changeset_revision, prior_installation_required = repository_dependency_tuple
        prior_installation_required = util.asbool( str( prior_installation_required ) )
        return tool_shed, name, owner, changeset_revision, prior_installation_required

def remove_dir( dir ):
    """Attempt to remove a directory from disk."""
    if os.path.exists( dir ):
        try:
            shutil.rmtree( dir )
        except:
            pass

def repository_was_previously_installed( trans, tool_shed_url, repository_name, repo_info_tuple ):
    """
    Handle the case where the repository was previously installed using an older changeset_revsion, but later the repository was updated
    in the tool shed and now we're trying to install the latest changeset revision of the same repository instead of updating the one
    that was previously installed.  We'll look in the database instead of on disk since the repository may be uninstalled.
    """
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
        get_repo_info_tuple_contents( repo_info_tuple )
    tool_shed = get_tool_shed_from_clone_url( repository_clone_url )
    # Get all previous change set revisions from the tool shed for the repository back to, but excluding, the previous valid changeset
    # revision to see if it was previously installed using one of them.
    url = url_join( tool_shed_url,
                    'repository/previous_changeset_revisions?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s' % \
                    ( url_for( '/', qualified=True ), repository_name, repository_owner, changeset_revision ) )
    text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
    if text:
        changeset_revisions = util.listify( text )
        for previous_changeset_revision in changeset_revisions:
            tool_shed_repository = get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( trans.app,
                                                                                                             tool_shed,
                                                                                                             repository_name,
                                                                                                             repository_owner,
                                                                                                             previous_changeset_revision )
            if tool_shed_repository and tool_shed_repository.status not in [ trans.model.ToolShedRepository.installation_status.NEW ]:
                return tool_shed_repository, previous_changeset_revision
    return None, None

def reversed_lower_upper_bounded_changelog( repo, excluded_lower_bounds_changeset_revision, included_upper_bounds_changeset_revision ):
    """
    Return a reversed list of changesets in the repository changelog after the excluded_lower_bounds_changeset_revision, but up to and
    including the included_upper_bounds_changeset_revision.  The value of excluded_lower_bounds_changeset_revision will be the value of
    INITIAL_CHANGELOG_HASH if no valid changesets exist before included_upper_bounds_changeset_revision.
    """
    # To set excluded_lower_bounds_changeset_revision, calling methods should do the following, where the value of changeset_revision
    # is a downloadable changeset_revision.
    # excluded_lower_bounds_changeset_revision = get_previous_downloadable_changeset_revision( repository, repo, changeset_revision )
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

def set_repository_attributes( trans, repository, status, error_message, deleted, uninstalled, remove_from_disk=False ):
    if remove_from_disk:
        relative_install_dir = repository.repo_path( trans.app )
        if relative_install_dir:
            clone_dir = os.path.abspath( relative_install_dir )
            shutil.rmtree( clone_dir )
            log.debug( "Removed repository installation directory: %s" % str( clone_dir ) )
    repository.error_message = error_message
    repository.status = status
    repository.deleted = deleted
    repository.uninstalled = uninstalled
    trans.sa_session.add( repository )
    trans.sa_session.flush()

def set_prior_installation_required( repository, required_repository ):
    """Return True if the received required_repository must be installed before the received repository."""
    # This method is called only from Galaxy when rendering repository dependencies for an installed tool shed repository.
    required_repository_tup = [ required_repository.tool_shed, required_repository.name, required_repository.owner, required_repository.changeset_revision ]
    # Get the list of repository dependency tuples associated with the received repository where prior_installation_required is True.
    required_rd_tups_that_must_be_installed = repository.requires_prior_installation_of
    for required_rd_tup in required_rd_tups_that_must_be_installed:
        # Repository dependency tuples in metadata include a prior_installation_required value, so strip it for comparision.
        partial_required_rd_tup = required_rd_tup[ 0:4 ]
        if partial_required_rd_tup == required_repository_tup:
            # Return the boolean value of prior_installation_required, which defaults to False.
            return required_rd_tup[ 4 ]
    return False
    
def strip_path( fpath ):
    """Attempt to strip the path from a file name."""
    if not fpath:
        return fpath
    try:
        file_path, file_name = os.path.split( fpath )
    except:
        file_name = fpath
    return file_name

def to_safe_string( text, to_html=True ):
    """Translates the characters in text to an html string"""
    if text:
        if to_html:
            try:
                escaped_text = text.decode( 'utf-8' )
                escaped_text = escaped_text.encode( 'ascii', 'ignore' )
                escaped_text = str( markupsafe.escape( escaped_text ) )
            except UnicodeDecodeError, e:
                escaped_text = "Error decoding string: %s" % str( e )
        else:
            escaped_text = str( text )
        translated = []
        for c in escaped_text:
            if c in VALID_CHARS:
                translated.append( c )
            elif c in [ '\n' ]:
                if to_html:
                    translated.append( '<br/>' )
                else:
                    translated.append( c )
            elif c in [ '\r' ]:
                continue
            elif c in [ ' ', '    ' ]:
                if to_html:
                    if c == ' ':
                        translated.append( '&nbsp;' )
                    else:
                        translated.append( '&nbsp;&nbsp;&nbsp;&nbsp;' )
                else:
                    translated.append( c )
            else:
                translated.append( '' )
        return ''.join( translated )
    return text

def tool_shed_from_repository_clone_url( repository_clone_url ):
    """Given a repository clone URL, return the tool shed that contains the repository."""
    return clean_repository_clone_url( repository_clone_url ).split( '/repos/' )[ 0 ].rstrip( '/' )

def tool_shed_is_this_tool_shed( toolshed_base_url ):
    """Determine if a tool shed is the current tool shed."""
    return toolshed_base_url.rstrip( '/' ) == str( url_for( '/', qualified=True ) ).rstrip( '/' )

def translate_string( raw_text, to_html=True ):
    """Return a subset of a string (up to MAX_CONTENT_SIZE) translated to a safe string for display in a browser."""
    if raw_text:
        if len( raw_text ) <= MAX_CONTENT_SIZE:
            translated_string = to_safe_string( raw_text, to_html=to_html )
        else:
            large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
            translated_string = to_safe_string( '%s%s' % ( raw_text[ 0:MAX_CONTENT_SIZE ], large_str ), to_html=to_html )
    else:
        translated_string = ''
    return translated_string

def update_in_shed_tool_config( app, repository ):
    """
    A tool shed repository is being updated so change the shed_tool_conf file.  Parse the config file to generate the entire list
    of config_elems instead of using the in-memory list.
    """
    shed_conf_dict = repository.get_shed_config_dict( app )
    shed_tool_conf = shed_conf_dict[ 'config_filename' ]
    tool_path = shed_conf_dict[ 'tool_path' ]
    tool_panel_dict = generate_tool_panel_dict_from_shed_tool_conf_entries( app, repository )
    repository_tools_tups = get_repository_tools_tups( app, repository.metadata )
    cleaned_repository_clone_url = clean_repository_clone_url( generate_clone_url_for_installed_repository( app, repository ) )
    tool_shed = tool_shed_from_repository_clone_url( cleaned_repository_clone_url )
    owner = repository.owner
    if not owner:
        owner = get_repository_owner( cleaned_repository_clone_url )
    guid_to_tool_elem_dict = {}
    for tool_config_filename, guid, tool in repository_tools_tups:
        guid_to_tool_elem_dict[ guid ] = generate_tool_elem( tool_shed, repository.name, repository.changeset_revision, repository.owner or '', tool_config_filename, tool, None )
    config_elems = []
    tree = util.parse_xml( shed_tool_conf )
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

def update_repository( repo, ctx_rev=None ):
    """
    Update the cloned repository to changeset_revision.  It is critical that the installed repository is updated to the desired
    changeset_revision before metadata is set because the process for setting metadata uses the repository files on disk.
    """
    # TODO: We may have files on disk in the repo directory that aren't being tracked, so they must be removed.
    # The codes used to show the status of files are as follows.
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    # It would be nice if we could use mercurial's purge extension to remove untracked files.  The problem is that
    # purging is not supported by the mercurial API.
    commands.update( get_configured_ui(), repo, rev=ctx_rev )

def update_tool_shed_repository_status( app, tool_shed_repository, status ):
    """Update the status of a tool shed repository in the process of being installed into Galaxy."""
    sa_session = app.model.context.current
    tool_shed_repository.status = status
    sa_session.add( tool_shed_repository )
    sa_session.flush()

def url_join( *args ):
    """Return a valid URL produced by appending a base URL and a set of request parameters."""
    parts = []
    for arg in args:
        parts.append( arg.strip( '/' ) )
    return '/'.join( parts )
