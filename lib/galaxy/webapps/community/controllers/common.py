import os, string, socket, logging, simplejson, binascii
from time import strftime
from datetime import *
from galaxy.datatypes.checkers import *
from galaxy.tools import *
from galaxy.util.json import from_json_string, to_json_string
from galaxy.util.hash_util import *
from galaxy.util.shed_util import copy_sample_file, generate_datatypes_metadata, generate_tool_dependency_metadata, generate_tool_metadata
from galaxy.util.shed_util import generate_workflow_metadata, get_changectx_for_changeset, get_config, get_configured_ui, get_named_tmpfile_from_ctx
from galaxy.util.shed_util import handle_sample_tool_data_table_conf_file, INITIAL_CHANGELOG_HASH, make_tmp_directory, NOT_TOOL_CONFIGS, reset_tool_data_tables
from galaxy.util.shed_util import reversed_upper_bounded_changelog, strip_path, to_html_escaped, to_html_str, update_repository
from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.model.orm import *
from galaxy.model.item_attrs import UsesItemRatings

from galaxy import eggs
eggs.require('mercurial')
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

new_repo_email_alert_template = """
GALAXY TOOL SHED NEW REPOSITORY ALERT
-----------------------------------------------------------------------------
You received this alert because you registered to receive email when
new repositories were created in the Galaxy tool shed named "${host}".
-----------------------------------------------------------------------------

Repository name:       ${repository_name}
Date content uploaded: ${display_date}
Uploaded by:           ${username}

Revision: ${revision}
Change description:
${description}

${content_alert_str}

-----------------------------------------------------------------------------
This change alert was sent from the Galaxy tool shed hosted on the server
"${host}"
"""

email_alert_template = """
GALAXY TOOL SHED REPOSITORY UPDATE ALERT
-----------------------------------------------------------------------------
You received this alert because you registered to receive email whenever
changes were made to the repository named "${repository_name}".
-----------------------------------------------------------------------------

Date of change: ${display_date}
Changed by:     ${username}

Revision: ${revision}
Change description:
${description}

${content_alert_str}

-----------------------------------------------------------------------------
This change alert was sent from the Galaxy tool shed hosted on the server
"${host}"
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

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

malicious_error = "  This changeset cannot be downloaded because it potentially produces malicious behavior or contains inappropriate content."
malicious_error_can_push = "  Correct this changeset as soon as possible, it potentially produces malicious behavior or contains inappropriate content."

class ItemRatings( UsesItemRatings ):
    """Overrides rate_item method since we also allow for comments"""
    def rate_item( self, trans, user, item, rating, comment='' ):
        """ Rate an item. Return type is <item_class>RatingAssociation. """
        item_rating = self.get_user_item_rating( trans.sa_session, user, item, webapp_model=trans.model )
        if not item_rating:
            # User has not yet rated item; create rating.
            item_rating_assoc_class = self._get_item_rating_assoc_class( item, webapp_model=trans.model )
            item_rating = item_rating_assoc_class()
            item_rating.user = trans.user
            item_rating.set_item( item )
            item_rating.rating = rating
            item_rating.comment = comment
            trans.sa_session.add( item_rating )
            trans.sa_session.flush()
        elif item_rating.rating != rating or item_rating.comment != comment:
            # User has previously rated item; update rating.
            item_rating.rating = rating
            item_rating.comment = comment
            trans.sa_session.add( item_rating )
            trans.sa_session.flush()
        return item_rating

## ---- Utility methods -------------------------------------------------------

def add_repository_metadata_tool_versions( trans, id, changeset_revisions ):
    # If a repository includes tools, build a dictionary of { 'tool id' : 'parent tool id' }
    # pairs for each tool in each changeset revision.
    for index, changeset_revision in enumerate( changeset_revisions ):
        tool_versions_dict = {}
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                tool_dicts = metadata.get( 'tools', [] )
                if index == 0:
                    # The first changset_revision is a special case because it will have no ancestor
                    # changeset_revisions in which to match tools.  The parent tool id for tools in
                    # the first changeset_revision will be the "old_id" in the tool config.
                    for tool_dict in tool_dicts:
                        tool_versions_dict[ tool_dict[ 'guid' ] ] = tool_dict[ 'id' ]
                else:
                    for tool_dict in tool_dicts:
                        # We have at least 2 changeset revisions to compare tool guids and tool ids.
                        parent_id = get_parent_id( trans, id, tool_dict[ 'id' ], tool_dict[ 'version' ], tool_dict[ 'guid' ], changeset_revisions[ 0:index ] )
                        tool_versions_dict[ tool_dict[ 'guid' ] ] = parent_id
                if tool_versions_dict:
                    repository_metadata.tool_versions = tool_versions_dict
                    trans.sa_session.add( repository_metadata )
                    trans.sa_session.flush()
def build_changeset_revision_select_field( trans, repository, selected_value=None, add_id_to_name=True ):
    """
    Build a SelectField whose options are the changeset_revision
    strings of all downloadable_revisions of the received repository.
    """
    repo = hg.repository( get_configured_ui(), repository.repo_path )
    options = []
    changeset_tups = []
    refresh_on_change_values = []
    for repository_metadata in repository.downloadable_revisions:
        changeset_revision = repository_metadata.changeset_revision
        ctx = get_changectx_for_changeset( repo, changeset_revision )
        if ctx:
            rev = '%04d' % ctx.rev()
            label = "%s:%s" % ( str( ctx.rev() ), changeset_revision )
        else:
            rev = '-1'
            label = "-1:%s" % changeset_revision
        changeset_tups.append( ( rev, label, changeset_revision ) )
        refresh_on_change_values.append( changeset_revision )
    # Sort options by the revision label.  Even though the downloadable_revisions query sorts by update_time,
    # the changeset revisions may not be sorted correctly because setting metadata over time will reset update_time.
    for changeset_tup in sorted( changeset_tups ):
        # Display the latest revision first.
        options.insert( 0, ( changeset_tup[1], changeset_tup[2] ) )
    if add_id_to_name:
        name = 'changeset_revision_%d' % repository.id
    else:
        name = 'changeset_revision'
    select_field = SelectField( name=name,
                                refresh_on_change=True,
                                refresh_on_change_values=refresh_on_change_values )
    for option_tup in options:
        selected = selected_value and option_tup[1] == selected_value
        select_field.add_option( option_tup[0], option_tup[1], selected=selected )
    return select_field
def changeset_is_malicious( trans, id, changeset_revision, **kwd ):
    """Check the malicious flag in repository metadata for a specified change set"""
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
    if repository_metadata:
        return repository_metadata.malicious
    return False
def check_file_contents( trans ):
    # See if any admin users have chosen to receive email alerts when a repository is updated.
    # If so, the file contents of the update must be checked for inappropriate content.
    admin_users = trans.app.config.get( "admin_users", "" ).split( "," )
    for repository in trans.sa_session.query( trans.model.Repository ) \
                                      .filter( trans.model.Repository.table.c.email_alerts != None ):
        email_alerts = from_json_string( repository.email_alerts )
        for user_email in email_alerts:
            if user_email in admin_users:
                return True
    return False
def check_tool_input_params( trans, repo, repo_dir, ctx, xml_file_in_ctx, tool, sample_files, invalid_files, tool_data_path, dir ):
    """
    Check all of the tool's input parameters, looking for any that are dynamically generated using external data files to make 
    sure the files exist.  This method is called only from the tool shed when generating metadata for a specified changeset revision.
    """
    can_set_metadata = True
    correction_msg = ''
    # Keep track of copied files so they can be removed after metadata generation.
    sample_files_copied = []
    for input_param in tool.input_params:
        if isinstance( input_param, galaxy.tools.parameters.basic.SelectToolParameter ) and input_param.is_dynamic:
            # If the tool refers to .loc files or requires an entry in the tool_data_table_conf.xml, make sure all requirements exist.
            options = input_param.dynamic_options or input_param.options
            if options:
                if options.tool_data_table or options.missing_tool_data_table_name:
                    # Make sure the repository contains a tool_data_table_conf.xml.sample file.
                    sample_tool_data_table_conf = get_config( 'tool_data_table_conf.xml.sample', repo, ctx, dir )
                    if sample_tool_data_table_conf:
                        error, correction_msg = handle_sample_tool_data_table_conf_file( trans.app, sample_tool_data_table_conf )
                        if error:
                            can_set_metadata = False
                            invalid_files.append( ( 'tool_data_table_conf.xml.sample', correction_msg ) )
                        else:
                            options.missing_tool_data_table_name = None
                    else:
                        can_set_metadata = False
                        correction_msg = "This file requires an entry in the tool_data_table_conf.xml file.  Upload a file named tool_data_table_conf.xml.sample "
                        correction_msg += "to the repository that includes the required entry to correct this error.<br/>"
                        invalid_files.append( ( xml_file_in_ctx, correction_msg ) )
                if options.index_file or options.missing_index_file:
                    # Make sure the repository contains the required xxx.loc.sample file.
                    index_file = options.index_file or options.missing_index_file
                    index_file_name = strip_path( index_file )
                    sample_found = False
                    for sample_file in sample_files:
                        sample_file_name = strip_path( sample_file )
                        if sample_file_name == '%s.sample' % index_file_name:
                            # If sample_file_name is on disk, copy it to dir.
                            copied_sample_file = copy_file_from_disk( sample_file_name, repo_dir, dir )
                            if not copied_sample_file:
                                # Get sample_file_name from the repository manifest.
                                copied_sample_file = copy_file_from_manifest( repo, ctx, sample_file_name, dir )
                            copy_sample_file( trans.app, copied_sample_file, dest_path=tool_data_path )
                            sample_files_copied.append( sample_file_name )
                            options.index_file = index_file_name
                            options.missing_index_file = None
                            if options.tool_data_table:
                                options.tool_data_table.missing_index_file = None
                            sample_found = True
                            break
                    if not sample_found:
                        can_set_metadata = False
                        correction_msg = "This file refers to a file named <b>%s</b>.  " % str( index_file )
                        correction_msg += "Upload a file named <b>%s.sample</b> to the repository to correct this error." % str( index_file_name )
                        invalid_files.append( ( xml_file_in_ctx, correction_msg ) )
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    reset_tool_data_tables( trans.app )
    return sample_files_copied, can_set_metadata, invalid_files
def clean_repository_metadata( trans, id, changeset_revisions ):
    # Delete all repository_metadata reecords associated with the repository that have a changeset_revision that is not in changeset_revisions.
    for repository_metadata in trans.sa_session.query( trans.model.RepositoryMetadata ) \
                                               .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) ):
        if repository_metadata.changeset_revision not in changeset_revisions:
            trans.sa_session.delete( repository_metadata )
            trans.sa_session.flush()
def compare_changeset_revisions( ancestor_changeset_revision, ancestor_metadata_dict, current_changeset_revision, current_metadata_dict ):
    # The metadata associated with ancestor_changeset_revision is ancestor_metadata_dict.  This changeset_revision is an ancestor of
    # current_changeset_revision which is associated with current_metadata_dict.
    #
    # A new repository_metadata record will be created only when this method returns the string 'not equal and not subset'.  However, we're
    # currently also returning the strings 'no metadata', 'equal' and 'subset', depending upon how the 2 change sets compare.  We'll leave
    # things this way for the current time in case we discover a use for these additional result strings.
    ancestor_datatypes = ancestor_metadata_dict.get( 'datatypes', [] )
    ancestor_tools = ancestor_metadata_dict.get( 'tools', [] )
    ancestor_guids = [ tool_dict[ 'guid' ] for tool_dict in ancestor_tools ]
    ancestor_guids.sort()
    ancestor_tool_dependencies = ancestor_metadata_dict.get( 'tool_dependencies', [] )
    ancestor_workflows = ancestor_metadata_dict.get( 'workflows', [] )
    current_datatypes = current_metadata_dict.get( 'datatypes', [] )
    current_tools = current_metadata_dict.get( 'tools', [] )
    current_guids = [ tool_dict[ 'guid' ] for tool_dict in current_tools ]
    current_guids.sort()
    current_tool_dependencies = current_metadata_dict.get( 'tool_dependencies', [] ) 
    current_workflows = current_metadata_dict.get( 'workflows', [] )
    # Handle case where no metadata exists for either changeset.
    if not ancestor_guids and not current_guids and not ancestor_workflows and not current_workflows and not ancestor_datatypes and not current_datatypes:
        return 'no metadata'
    workflow_comparison = compare_workflows( ancestor_workflows, current_workflows )
    datatype_comparison = compare_datatypes( ancestor_datatypes, current_datatypes )
    # Handle case where all metadata is the same.
    if ancestor_guids == current_guids and workflow_comparison == 'equal' and datatype_comparison == 'equal':
        return 'equal'
    if workflow_comparison == 'subset' and datatype_comparison == 'subset':
        is_subset = True
        for guid in ancestor_guids:
            if guid not in current_guids:
                is_subset = False
                break
        if is_subset:
            return 'subset'
    return 'not equal and not subset'
def compare_datatypes( ancestor_datatypes, current_datatypes ):
    # Determine if ancestor_datatypes is the same as current_datatypes
    # or if ancestor_datatypes is a subset of current_datatypes.  Each
    # datatype dict looks something like:
    # {"dtype": "galaxy.datatypes.images:Image", "extension": "pdf", "mimetype": "application/pdf"}
    if len( ancestor_datatypes ) <= len( current_datatypes ):
        for ancestor_datatype in ancestor_datatypes:
            # Currently the only way to differentiate datatypes is by name.
            ancestor_datatype_dtype = ancestor_datatype[ 'dtype' ]
            ancestor_datatype_extension = ancestor_datatype[ 'extension' ]
            ancestor_datatype_mimetype = ancestor_datatype.get( 'mimetype', None )
            found_in_current = False
            for current_datatype in current_datatypes:
                if current_datatype[ 'dtype' ] == ancestor_datatype_dtype and \
                    current_datatype[ 'extension' ] == ancestor_datatype_extension and \
                    current_datatype.get( 'mimetype', None ) == ancestor_datatype_mimetype:
                    found_in_current = True
                    break
            if not found_in_current:
                return 'not equal and not subset'
        if len( ancestor_datatypes ) == len( current_datatypes ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'
def compare_workflows( ancestor_workflows, current_workflows ):
    # Determine if ancestor_workflows is the same as current_workflows
    # or if ancestor_workflows is a subset of current_workflows.
    if len( ancestor_workflows ) <= len( current_workflows ):
        for ancestor_workflow_tup in ancestor_workflows:
            # ancestor_workflows is a list of tuples where each contained tuple is
            # [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
            ancestor_workflow_dict = ancestor_workflow_tup[1]
            # Currently the only way to differentiate workflows is by name.
            ancestor_workflow_name = ancestor_workflow_dict[ 'name' ]
            num_ancestor_workflow_steps = len( ancestor_workflow_dict[ 'steps' ] )
            found_in_current = False
            for current_workflow_tup in current_workflows:
                current_workflow_dict = current_workflow_tup[1]
                # Assume that if the name and number of steps are euqal,
                # then the workflows are the same.  Of course, this may
                # not be true...
                if current_workflow_dict[ 'name' ] == ancestor_workflow_name and len( current_workflow_dict[ 'steps' ] ) == num_ancestor_workflow_steps:
                    found_in_current = True
                    break
            if not found_in_current:
                return 'not equal and not subset'
        if len( ancestor_workflows ) == len( current_workflows ):
            return 'equal'
        else:
            return 'subset'
    return 'not equal and not subset'
def copy_file_from_disk( filename, repo_dir, dir ):
    file_path = None
    found = False
    for root, dirs, files in os.walk( repo_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == filename:
                    file_path = os.path.abspath( os.path.join( root, name ) )
                    found = True
                    break
        if found:
            break
    if file_path:
        tmp_filename = os.path.join( dir, filename )
        shutil.copy( file_path, tmp_filename )
    else:
        tmp_filename = None
    return tmp_filename
def copy_file_from_manifest( repo, ctx, filename, dir ):
    """
    Copy the latest version of the file named filename from the repository manifest to the directory to which dir refers.
    """
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
def create_or_update_repository_metadata( trans, id, repository, changeset_revision, metadata_dict ):
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
    if repository_metadata:
        # Update RepositoryMetadata.metadata.
        repository_metadata.metadata = metadata_dict
        trans.sa_session.add( repository_metadata )
        trans.sa_session.flush()
    else:
        # Create a new repository_metadata table row.
        repository_metadata = trans.model.RepositoryMetadata( repository.id, changeset_revision, metadata_dict )
        trans.sa_session.add( repository_metadata )
        trans.sa_session.flush()
def decode( value ):
    # Extract and verify hash
    a, b = value.split( ":" )
    value = binascii.unhexlify( b )
    test = hmac_new( 'ToolShedAndGalaxyMustHaveThisSameKey', value )
    assert a == test
    # Restore from string
    try:
        values = json_fix( simplejson.loads( value ) )
    except Exception, e:
        # We do not have a json string
        values = value
    return values
def encode( val ):
    if isinstance( val, dict ):
        value = simplejson.dumps( val )
    else:
        value = val
    a = hmac_new( 'ToolShedAndGalaxyMustHaveThisSameKey', value )
    b = binascii.hexlify( value )
    return "%s:%s" % ( a, b )
def generate_clone_url( trans, repository_id ):
    """Generate the URL for cloning a repository."""
    repository = get_repository( trans, repository_id )
    protocol, base = trans.request.base.split( '://' )
    if trans.user:
        username = '%s@' % trans.user.username
    else:
        username = ''
    return '%s://%s%s/repos/%s/%s' % ( protocol, username, base, repository.user.username, repository.name )
def generate_metadata_for_changeset_revision( trans, repo, id, ctx, changeset_revision, repo_dir, updating_tip=False ):
    if updating_tip:
        # If a push from the command line is occurring, update the repository files on disk before setting metadata.
        update_repository( repo, str( ctx.rev() ) )
    metadata_dict = {}
    invalid_files = []
    invalid_tool_configs = []
    original_tool_data_path = trans.app.config.tool_data_path
    work_dir = make_tmp_directory()
    datatypes_config = get_config( 'datatypes_conf.xml', repo, ctx, work_dir  )
    if datatypes_config:
        metadata_dict = generate_datatypes_metadata( datatypes_config, metadata_dict )    
    sample_files, deleted_sample_files = get_list_of_copied_sample_files( repo, ctx, dir=work_dir )
    # Handle the tool_data_table_conf.xml.sample file if it is included in the repository.
    if 'tool_data_table_conf.xml.sample' in sample_files:
        tool_data_table_config = copy_file_from_manifest( repo, ctx, 'tool_data_table_conf.xml.sample', work_dir )
        error, correction_msg = handle_sample_tool_data_table_conf_file( trans.app, tool_data_table_config )
    if sample_files:
        trans.app.config.tool_data_path = work_dir
    for filename in ctx:
        # Find all tool configs.
        ctx_file_name = strip_path( filename )
        if ctx_file_name not in NOT_TOOL_CONFIGS and filename.endswith( '.xml' ):
            is_tool_config, valid, tool, error_message = load_tool_from_tmp_directory( trans, repo, repo_dir, ctx, filename, work_dir )
            if is_tool_config and valid and tool is not None:
                sample_files_copied, can_set_metadata, invalid_files = check_tool_input_params( trans,
                                                                                                repo,
                                                                                                repo_dir,
                                                                                                ctx,
                                                                                                filename,
                                                                                                tool,
                                                                                                sample_files,
                                                                                                invalid_files,
                                                                                                original_tool_data_path,
                                                                                                work_dir )
                if can_set_metadata:
                    # Update the list of metadata dictionaries for tools in metadata_dict.
                    repository_clone_url = generate_clone_url( trans, id )
                    metadata_dict = generate_tool_metadata( filename, tool, repository_clone_url, metadata_dict )
                else:
                    invalid_tool_configs.append( ctx_file_name )
                # Remove all copied sample files from both the original tool data path (~/shed-tool-data) and the temporary
                # value of trans.app.config.tool_data_path, which is work_dir.
                for copied_sample_file in sample_files_copied:
                    copied_file = copied_sample_file.replace( '.sample', '' )
                    try:
                        os.unlink( os.path.join( trans.app.config.tool_data_path, copied_sample_file ) )
                    except:
                        pass
                    try:
                        os.unlink( os.path.join( trans.app.config.tool_data_path, copied_file ) )
                    except:
                        pass
                    if trans.app.config.tool_data_path == work_dir:
                        try:
                            os.unlink( os.path.join( original_tool_data_path, copied_sample_file ) )
                        except:
                            pass
                        try:
                            os.unlink( os.path.join( original_tool_data_path, copied_file ) )
                        except:
                            pass
            elif is_tool_config:
                if not error_message:
                    error_message = 'Unknown problems loading tool.'
                # We have a tool config but it is invalid or the tool does not properly load.
                invalid_files.append( ( ctx_file_name, error_message ) )
                invalid_tool_configs.append( ctx_file_name )
        # Find all exported workflows.
        elif filename.endswith( '.ga' ):
            try:
                fctx = ctx[ filename ]
                workflow_text = fctx.data()
                exported_workflow_dict = from_json_string( workflow_text )
                if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                    metadata_dict = generate_workflow_metadata( '', exported_workflow_dict, metadata_dict )
            except Exception, e:
                invalid_files.append( ( ctx_file_name, str( e ) ) )
    if 'tools' in metadata_dict:
        # Find tool_dependencies.xml if it exists.  This step must be done after metadata for tools has been defined.
        tool_dependencies_config = get_config( 'tool_dependencies.xml', repo, ctx, work_dir )
        if tool_dependencies_config:
            metadata_dict = generate_tool_dependency_metadata( tool_dependencies_config, metadata_dict )
    if invalid_tool_configs:
        metadata_dict [ 'invalid_tools' ] = invalid_tool_configs
    if sample_files:
        # Don't forget to reset the value of trans.app.config.tool_data_path!
        trans.app.config.tool_data_path = original_tool_data_path
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    reset_tool_data_tables( trans.app )
    try:
        shutil.rmtree( work_dir )
    except:
        pass
    return metadata_dict, invalid_files, deleted_sample_files
def generate_tool_guid( trans, repository, tool ):
    """
    Generate a guid for the received tool.  The form of the guid is    
    <tool shed host>/repos/<tool shed username>/<tool shed repo name>/<tool id>/<tool version>
    """
    return '%s/repos/%s/%s/%s/%s' % ( trans.request.host,
                                      repository.user.username,
                                      repository.name,
                                      tool.id,
                                      tool.version )
def get_category( trans, id ):
    """Get a category from the database"""
    return trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( id ) )
def get_categories( trans ):
    """Get all categories from the database"""
    return trans.sa_session.query( trans.model.Category ) \
                           .filter( trans.model.Category.table.c.deleted==False ) \
                           .order_by( trans.model.Category.table.c.name ).all()
def get_file_context_from_ctx( ctx, filename ):
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
def get_latest_repository_metadata( trans, id ):
    """Get last metadata defined for a specified repository from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) ) \
                           .order_by( trans.model.RepositoryMetadata.table.c.id.desc() ) \
                           .first()
def get_list_of_copied_sample_files( repo, ctx, dir ):
    """
    Find all sample files (files in the repository with the special .sample extension) in the reversed repository manifest up to ctx.  Copy
    each discovered file to dir and return the list of filenames.  If a .sample file was added in a changeset and then deleted in a later
    changeset, it will be returned in the deleted_sample_files list.  The caller will set the value of app.config.tool_data_path to dir in
    order to load the tools and generate metadata for them.
    """
    deleted_sample_files = []
    sample_files = []
    for changeset in reversed_upper_bounded_changelog( repo, ctx ):
        changeset_ctx = repo.changectx( changeset )
        for ctx_file in changeset_ctx.files():
            ctx_file_name = strip_path( ctx_file )
            # If we decide in the future that files deleted later in the changelog should not be used, we can use the following if statement.
            # if ctx_file_name.endswith( '.sample' ) and ctx_file_name not in sample_files and ctx_file_name not in deleted_sample_files:
            if ctx_file_name.endswith( '.sample' ) and ctx_file_name not in sample_files:
                fctx = get_file_context_from_ctx( changeset_ctx, ctx_file )
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
def get_parent_id( trans, id, old_id, version, guid, changeset_revisions ):
    parent_id = None
    # Compare from most recent to oldest.
    changeset_revisions.reverse()
    for changeset_revision in changeset_revisions:
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
        metadata = repository_metadata.metadata
        tools_dicts = metadata.get( 'tools', [] )
        for tool_dict in tools_dicts:
            if tool_dict[ 'guid' ] == guid:
                # The tool has not changed between the compared changeset revisions.
                continue
            if tool_dict[ 'id' ] == old_id and tool_dict[ 'version' ] != version:
                # The tool version is different, so we've found the parent.
                return tool_dict[ 'guid' ]
    if parent_id is None:
        # The tool did not change through all of the changeset revisions.
        return old_id
def get_previous_valid_changset_revision( repository, repo, before_changeset_revision ):
    """
    Return the downloadable changeset_revision in the repository changelog just prior to the changeset to which before_changeset_revision
    refers.  If there isn't one, return the hash value of an empty repository changlog, INITIAL_CHANGELOG_HASH.
    """
    changeset_tups = []
    for repository_metadata in repository.downloadable_revisions:
        changeset_revision = repository_metadata.changeset_revision
        ctx = get_changectx_for_changeset( repo, changeset_revision )
        if ctx:
            rev = '%04d' % ctx.rev()
        else:
            rev = '-1'
        changeset_tups.append( ( rev, changeset_revision ) )
    previous_changeset_revision = None
    current_changeset_revision = None
    for changeset_tup in sorted( changeset_tups ):
        current_changeset_revision = changeset_tup[ 1 ]
        if current_changeset_revision == before_changeset_revision:
            if previous_changeset_revision:
                return previous_changeset_revision
            else:
                # Return the hash value of an empty repository changlog - note that this will not be a valid changset revision.
                return INITIAL_CHANGELOG_HASH
        else:
            previous_changeset_revision = current_changeset_revision
def get_repository( trans, id ):
    """Get a repository from the database via id"""
    return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )
def get_repository_by_name( trans, name ):
    """Get a repository from the database via name"""
    return trans.sa_session.query( trans.model.Repository ).filter_by( name=name ).one()
def get_repository_by_name_and_owner( trans, name, owner ):
    """Get a repository from the database via name and owner"""
    user = get_user_by_username( trans, owner )
    return trans.sa_session.query( trans.model.Repository ) \
                             .filter( and_( trans.model.Repository.table.c.name == name,
                                            trans.model.Repository.table.c.user_id == user.id ) ) \
                             .first()
def get_repository_metadata_by_changeset_revision( trans, id, changeset_revision ):
    """Get metadata for a specified repository change set from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( and_( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ),
                                          trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                           .first()
def get_repository_metadata_by_id( trans, id ):
    """Get repository metadata from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ).get( trans.security.decode_id( id ) )
def get_repository_metadata_by_repository_id( trans, id ):
    """Get all metadata records for a specified repository."""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) )
def get_revision_label( trans, repository, changeset_revision ):
    """
    Return a string consisting of the human read-able 
    changeset rev and the changeset revision string.
    """
    repo = hg.repository( get_configured_ui(), repository.repo_path )
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        return "%s:%s" % ( str( ctx.rev() ), changeset_revision )
    else:
        return "-1:%s" % changeset_revision
def get_user( trans, id ):
    """Get a user from the database by id"""
    return trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( id ) )
def handle_email_alerts( trans, repository, content_alert_str='', new_repo_alert=False, admin_only=False ):
    # There are 2 complementary features that enable a tool shed user to receive email notification:
    # 1. Within User Preferences, they can elect to receive email when the first (or first valid)
    #    change set is produced for a new repository.
    # 2. When viewing or managing a repository, they can check the box labeled "Receive email alerts"
    #    which caused them to receive email alerts when updates to the repository occur.  This same feature
    #    is available on a per-repository basis on the repository grid within the tool shed.
    #
    # There are currently 4 scenarios for sending email notification when a change is made to a repository:
    # 1. An admin user elects to receive email when the first change set is produced for a new repository
    #    from User Preferences.  The change set does not have to include any valid content.  This allows for
    #    the capture of inappropriate content being uploaded to new repositories.
    # 2. A regular user elects to receive email when the first valid change set is produced for a new repository
    #    from User Preferences.  This differs from 1 above in that the user will not receive email until a
    #    change set tha tincludes valid content is produced.
    # 3. An admin user checks the "Receive email alerts" check box on the manage repository page.  Since the
    #    user is an admin user, the email will include information about both HTML and image content that was
    #    included in the change set.
    # 4. A regular user checks the "Receive email alerts" check box on the manage repository page.  Since the
    #    user is not an admin user, the email will not include any information about both HTML and image content
    #    that was included in the change set.
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
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
        date = datetime( *time.gmtime( float( t ) - tz )[:6] )
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
                                                                  repository_name=repository.name,
                                                                  revision='%s:%s' %( str( ctx.rev() ), ctx ),
                                                                  display_date=display_date,
                                                                  description=ctx.description(),
                                                                  username=username,
                                                                  content_alert_str=content_alert_str )
        body = string.Template( template ).safe_substitute( host=trans.request.host,
                                                            repository_name=repository.name,
                                                            revision='%s:%s' %( str( ctx.rev() ), ctx ),
                                                            display_date=display_date,
                                                            description=ctx.description(),
                                                            username=username,
                                                            content_alert_str='' )
        admin_users = trans.app.config.get( "admin_users", "" ).split( "," )
        frm = email_from
        if new_repo_alert:
            subject = "New Galaxy tool shed repository alert"
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
            subject = "Galaxy tool shed repository update alert"
            email_alerts = from_json_string( repository.email_alerts )
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
def load_tool( trans, config_file ):
    """Load a single tool from the file named by `config_file` and return an instance of `Tool`."""
    # Parse XML configuration file and get the root element
    tree = util.parse_xml( config_file )
    root = tree.getroot()
    if root.tag == 'tool':
        # Allow specifying a different tool subclass to instantiate
        if root.find( "type" ) is not None:
            type_elem = root.find( "type" )
            module = type_elem.get( 'module', 'galaxy.tools' )
            cls = type_elem.get( 'class' )
            mod = __import__( module, globals(), locals(), [cls] )
            ToolClass = getattr( mod, cls )
        elif root.get( 'tool_type', None ) is not None:
            ToolClass = tool_types.get( root.get( 'tool_type' ) )
        else:
            ToolClass = Tool
        return ToolClass( config_file, root, trans.app )
    return None
def load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_config_filename ):
    """
    Return a loaded tool whose tool config file name (e.g., filtering.xml) is the value of tool_config_filename.  The value of changeset_revision
    is a valid (downloadable) changset revision.  The tool config will be located in the repository manifest between the received valid changeset
    revision and the first changeset revision in the repository, searching backwards.
    """
    def load_from_tmp_config( ctx, ctx_file, work_dir ):
        tool = None
        message = ''
        tmp_tool_config = get_named_tmpfile_from_ctx( ctx, ctx_file, work_dir )
        if tmp_tool_config:
            element_tree = util.parse_xml( tmp_tool_config )
            element_tree_root = element_tree.getroot()
            # Look for code files required by the tool config.
            tmp_code_files = []
            for code_elem in element_tree_root.findall( 'code' ):
                code_file_name = code_elem.get( 'file' )
                tmp_code_file_name = copy_file_from_manifest( repo, ctx, code_file_name, work_dir )
                if tmp_code_file_name:
                    tmp_code_files.append( tmp_code_file_name )
            try:
                tool = load_tool( trans, tmp_tool_config )
            except Exception, e:
                tool = None
                message = "Error loading tool: %s.  " % str( e )
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
    tool_config_filename = strip_path( tool_config_filename )
    repository = get_repository( trans, repository_id )
    repo_files_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_files_dir )
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    tool = None
    message = ''
    work_dir = make_tmp_directory()
    # Load entries into the tool_data_tables if the tool requires them.
    tool_data_table_config = copy_file_from_manifest( repo, ctx, 'tool_data_table_conf.xml.sample', work_dir )
    if tool_data_table_config:
        error, correction_msg = handle_sample_tool_data_table_conf_file( trans.app, tool_data_table_config )
    found = False
    # Get the latest revision of the tool config from the repository manifest up to the value of changeset_revision.
    for changeset in reversed_upper_bounded_changelog( repo, changeset_revision ):
        manifest_changeset_revision = str( repo.changectx( changeset ) )
        manifest_ctx = repo.changectx( changeset )
        for ctx_file in manifest_ctx.files():
            ctx_file_name = strip_path( ctx_file )
            if ctx_file_name == tool_config_filename:
                found = True
                break
        if found:
            tool, message = load_from_tmp_config( manifest_ctx, ctx_file, work_dir )
            break
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    reset_tool_data_tables( trans.app )
    try:
        shutil.rmtree( work_dir )
    except:
        pass
    return tool, message
def load_tool_from_tmp_directory( trans, repo, repo_dir, ctx, filename, dir ):
    is_tool_config = False
    tool = None
    valid = False
    error_message = ''
    tmp_config = get_named_tmpfile_from_ctx( ctx, filename, dir )
    if tmp_config:
        if not ( check_binary( tmp_config ) or check_image( tmp_config ) or check_gzip( tmp_config )[ 0 ]
                 or check_bz2( tmp_config )[ 0 ] or check_zip( tmp_config ) ):
            try:
                # Make sure we're looking at a tool config and not a display application config or something else.
                element_tree = util.parse_xml( tmp_config )
                element_tree_root = element_tree.getroot()
                is_tool_config = element_tree_root.tag == 'tool'
            except Exception, e:
                log.debug( "Error parsing %s, exception: %s" % ( tmp_config, str( e ) ) )
                is_tool_config = False
            if is_tool_config:
                # Load entries into the tool_data_tables if the tool requires them.
                tool_data_table_config = copy_file_from_manifest( repo, ctx, 'tool_data_table_conf.xml.sample', dir )
                if tool_data_table_config:
                    error, correction_msg = handle_sample_tool_data_table_conf_file( trans.app, tool_data_table_config )
                # Look for code files required by the tool config.  The directory to which dir refers should be removed by the caller.
                for code_elem in element_tree_root.findall( 'code' ):
                    code_file_name = code_elem.get( 'file' )
                    if not os.path.exists( os.path.join( dir, code_file_name ) ):
                        tmp_code_file_name = copy_file_from_disk( code_file_name, repo_dir, dir )
                        if tmp_code_file_name is None:
                            tmp_code_file_name = copy_file_from_manifest( repo, ctx, code_file_name, dir )
                try:
                    tool = load_tool( trans, tmp_config )
                    valid = True
                except KeyError, e:
                    valid = False
                    error_message = 'This file requires an entry for "%s" in the tool_data_table_conf.xml file.  Upload a file ' % str( e )
                    error_message += 'named tool_data_table_conf.xml.sample to the repository that includes the required entry to correct '
                    error_message += 'this error.  '
                except Exception, e:
                    valid = False
                    error_message = str( e )
                # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
                reset_tool_data_tables( trans.app )
    return is_tool_config, valid, tool, error_message
def new_tool_metadata_required( trans, id, metadata_dict ):
    """
    Compare the last saved metadata for each tool in the repository with the new metadata
    in metadata_dict to determine if a new repository_metadata table record is required, or
    if the last saved metadata record can updated instead.
    """
    if 'tools' in metadata_dict:
        repository_metadata = get_latest_repository_metadata( trans, id )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata and 'tools' in metadata:
                saved_tool_ids = []
                # The metadata for one or more tools was successfully generated in the past
                # for this repository, so we first compare the version string for each tool id
                # in metadata_dict with what was previously saved to see if we need to create
                # a new table record or if we can simply update the existing record.
                for new_tool_metadata_dict in metadata_dict[ 'tools' ]:
                    for saved_tool_metadata_dict in metadata[ 'tools' ]:
                        if saved_tool_metadata_dict[ 'id' ] not in saved_tool_ids:
                            saved_tool_ids.append( saved_tool_metadata_dict[ 'id' ] )
                        if new_tool_metadata_dict[ 'id' ] == saved_tool_metadata_dict[ 'id' ]:
                            if new_tool_metadata_dict[ 'version' ] != saved_tool_metadata_dict[ 'version' ]:
                                return True
                # So far, a new metadata record is not required, but we still have to check to see if
                # any new tool ids exist in metadata_dict that are not in the saved metadata.  We do
                # this because if a new tarball was uploaded to a repository that included tools, it
                # may have removed existing tool files if they were not included in the uploaded tarball.
                for new_tool_metadata_dict in metadata_dict[ 'tools' ]:
                    if new_tool_metadata_dict[ 'id' ] not in saved_tool_ids:
                        return True
            else:
                # We have repository metadata that does not include metadata for any tools in the
                # repository, so we can update the existing repository metadata.
                return False
        else:
            # There is no saved repository metadata, so we need to create a new repository_metadata
            # table record.
            return True
    # The received metadata_dict includes no metadata for tools, so a new repository_metadata table
    # record is not needed.
    return False
def new_workflow_metadata_required( trans, id, metadata_dict ):
    """
    Currently everything about an exported workflow except the name is hard-coded, so there's
    no real way to differentiate versions of exported workflows.  If this changes at some future
    time, this method should be enhanced accordingly.
    """
    if 'workflows' in metadata_dict:
        repository_metadata = get_latest_repository_metadata( trans, id )
        if repository_metadata:
            if repository_metadata.metadata:
                # The repository has metadata, so update the workflows value - no new record is needed.
                return False
        else:
            # There is no saved repository metadata, so we need to create a new repository_metadata table record.
            return True
    # The received metadata_dict includes no metadata for workflows, so a new repository_metadata table record is not needed.
    return False
def reset_all_metadata_on_repository( trans, id, **kwd ):
    params = util.Params( kwd )
    message = util.restore_text( params.get( 'message', ''  ) )
    status = params.get( 'status', 'done' )
    repository = get_repository( trans, id )
    log.debug( "Resetting all metadata on repository: %s" % repository.name )
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    missing_sample_files = []
    if len( repo ) == 1:
        error_message, status = set_repository_metadata( trans, id, repository.tip, **kwd )
        if error_message:
            return error_message, status
        else:
            add_repository_metadata_tool_versions( trans, id, [ repository.tip ] )
    else:
        # The list of changeset_revisions refers to repository_metadata records that have been created or updated.  When the following loop
        # completes, we'll delete all repository_metadata records for this repository that do not have a changeset_revision value in this list.
        changeset_revisions = []
        ancestor_changeset_revision = None
        ancestor_metadata_dict = None
        for changeset in repo.changelog:
            current_changeset_revision = str( repo.changectx( changeset ) )
            ctx = get_changectx_for_changeset( repo, current_changeset_revision )
            current_metadata_dict, invalid_files, deleted_sample_files = generate_metadata_for_changeset_revision( trans,
                                                                                                                   repo,
                                                                                                                   id,
                                                                                                                   ctx,
                                                                                                                   current_changeset_revision,
                                                                                                                   repo_dir,
                                                                                                                   updating_tip=current_changeset_revision==repository.tip )
            for deleted_sample_file in deleted_sample_files:
                if deleted_sample_file not in missing_sample_files:
                    missing_sample_files.append( deleted_sample_file )
            if current_metadata_dict:
                if ancestor_changeset_revision:
                    # Compare metadata from ancestor and current.  The value of comparsion will be one of:
                    # 'no metadata' - no metadata for either ancestor or current, so continue from current
                    # 'equal' - ancestor metadata is equivalent to current metadata, so continue from current
                    # 'subset' - ancestor metadata is a subset of current metadata, so continue from current
                    # 'not equal and not subset' - ancestor metadata is neither equal to nor a subset of current
                    #                              metadata, so persist ancestor metadata.
                    comparison = compare_changeset_revisions( ancestor_changeset_revision,
                                                              ancestor_metadata_dict,
                                                              current_changeset_revision,
                                                              current_metadata_dict )
                    if comparison in [ 'no metadata', 'equal', 'subset' ]:
                        ancestor_changeset_revision = current_changeset_revision
                        ancestor_metadata_dict = current_metadata_dict
                    elif comparison == 'not equal and not subset':
                        create_or_update_repository_metadata( trans, id, repository, ancestor_changeset_revision, ancestor_metadata_dict )
                        # Keep track of the changeset_revisions that we've persisted.
                        changeset_revisions.append( ancestor_changeset_revision )
                        ancestor_changeset_revision = current_changeset_revision
                        ancestor_metadata_dict = current_metadata_dict
                else:
                    # We're either at the first change set in the change log or we have just created or updated
                    # a repository_metadata record.  At this point we set the ancestor changeset to the current
                    # changeset for comparison in the next iteration.
                    ancestor_changeset_revision = current_changeset_revision
                    ancestor_metadata_dict = current_metadata_dict
                if not ctx.children():
                    # We're at the end of the change log.
                    create_or_update_repository_metadata( trans, id, repository, current_changeset_revision, current_metadata_dict )
                    changeset_revisions.append( current_changeset_revision )
                    ancestor_changeset_revision = None
                    ancestor_metadata_dict = None
            elif ancestor_metadata_dict:
                if not ctx.children():
                    # We're at the end of the change log.
                    create_or_update_repository_metadata( trans, id, repository, current_changeset_revision, ancestor_metadata_dict )
                    changeset_revisions.append( current_changeset_revision )
                    ancestor_changeset_revision = None
                    ancestor_metadata_dict = None
        clean_repository_metadata( trans, id, changeset_revisions )
        add_repository_metadata_tool_versions( trans, id, changeset_revisions )
    if missing_sample_files:
        message += "Metadata was successfully reset, but the following required sample files have been deleted from the repository so the version "
        message += "of each file just prior to its deletion is being used.  These files should be re-added to the repository as soon as possible:  "
        message += "<b>%s</b><br/>" % ', '.join( missing_sample_files )
        return message, 'ok'
    return '', 'ok'
def set_repository_metadata( trans, id, changeset_revision, content_alert_str='', **kwd ):
    """
    Set repository metadata on the repository tip, returning specific error messages (if any) to alert the repository owner that the changeset
    has problems.
    """
    message = ''
    status = 'done'
    repository = get_repository( trans, id )
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    metadata_dict = {}
    invalid_files = []
    updating_tip = changeset_revision == repository.tip
    if ctx is not None:
        metadata_dict, invalid_files, deleted_sample_files = generate_metadata_for_changeset_revision( trans,
                                                                                                       repo,
                                                                                                       id,
                                                                                                       ctx,
                                                                                                       changeset_revision,
                                                                                                       repo_dir,
                                                                                                       updating_tip=updating_tip )
        if metadata_dict:
            if updating_tip:
                if new_tool_metadata_required( trans, id, metadata_dict ) or new_workflow_metadata_required( trans, id, metadata_dict ):
                    # Create a new repository_metadata table row.
                    repository_metadata = trans.model.RepositoryMetadata( repository.id, changeset_revision, metadata_dict )
                    trans.sa_session.add( repository_metadata )
                    try:
                        trans.sa_session.flush()
                        # If this is the first record stored for this repository, see if we need to send any email alerts.
                        if len( repository.downloadable_revisions ) == 1:
                            handle_email_alerts( trans, repository, content_alert_str='', new_repo_alert=True, admin_only=False )
                    except TypeError, e:
                        message = "Unable to save metadata for this repository probably due to a tool config file that doesn't conform to the Cheetah template syntax."
                        status = 'error'
                else:
                    repository_metadata = get_latest_repository_metadata( trans, id )
                    if repository_metadata:
                        # Update the last saved repository_metadata table row.
                        repository_metadata.changeset_revision = changeset_revision
                        repository_metadata.metadata = metadata_dict
                        trans.sa_session.add( repository_metadata )
                        try:
                            trans.sa_session.flush()
                        except TypeError, e:
                            message = "Unable to save metadata for this repository probably due to a tool config file that doesn't conform to the Cheetah template syntax."
                            status = 'error'
                    else:
                        # There are no tools in the repository, and we're setting metadata on the repository tip.
                        repository_metadata = trans.model.RepositoryMetadata( repository.id, changeset_revision, metadata_dict )
                        trans.sa_session.add( repository_metadata )
                        trans.sa_session.flush()
            else:
                # We're re-generating metadata for an old repository revision.
                repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
                repository_metadata.metadata = metadata_dict
                trans.sa_session.add( repository_metadata )
                trans.sa_session.flush()
        elif updating_tip and len( repo ) == 1 and not invalid_files:
            message = "Revision '%s' includes no tools, datatypes or exported workflows for which metadata can " % str( changeset_revision )
            message += "be defined so this revision cannot be automatically installed into a local Galaxy instance."
            status = "error"
    else:
        # Here ctx is None.
        message = "This repository does not include revision '%s'." % str( changeset_revision )
        status = 'error'
    if deleted_sample_files:
        message += "Metadata was successfully reset, but the following required sample files have been deleted from the repository so the version "
        message += "of each file just prior to its deletion is being used.  These files should be re-added to the repository as soon as possible:  "
        message += "<b>%s</b><br/>" % ', '.join( deleted_sample_files )
    if invalid_files:
        if metadata_dict:
            message = "Metadata was defined for some items in revision '%s'.  " % str( changeset_revision )
            message += "Correct the following problems if necessary and reset metadata.<br/>"
        else:
            message = "Metadata cannot be defined for revision '%s' so this revision cannot be automatically " % str( changeset_revision )
            message += "installed into a local Galaxy instance.  Correct the following problems and reset metadata.<br/>"
        for itc_tup in invalid_files:
            tool_file, exception_msg = itc_tup
            if exception_msg.find( 'No such file or directory' ) >= 0:
                exception_items = exception_msg.split()
                missing_file_items = exception_items[ 7 ].split( '/' )
                missing_file = missing_file_items[ -1 ].rstrip( '\'' )
                if missing_file.endswith( '.loc' ):
                    sample_ext = '%s.sample' % missing_file
                else:
                    sample_ext = missing_file
                correction_msg = "This file refers to a missing file <b>%s</b>.  " % str( missing_file )
                correction_msg += "Upload a file named <b>%s</b> to the repository to correct this error." % sample_ext
            else:
               correction_msg = exception_msg
            message += "<b>%s</b> - %s<br/>" % ( tool_file, correction_msg )            
        status = 'error'
    return message, status
def set_repository_metadata_due_to_new_tip( trans, id, repository, content_alert_str=None, **kwd ):
    # Set metadata on the repository tip.
    error_message, status = set_repository_metadata( trans, id, repository.tip, content_alert_str=content_alert_str, **kwd )
    if not error_message:
        # If no error occurred in setting metadata on the repository tip, reset metadata on all changeset revisions for the repository.
        # This will result in a more standardized set of valid repository revisions that can be installed.
        error_message, status = reset_all_metadata_on_repository( trans, id, **kwd )
    if error_message:
        # If there is an error, display it.
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='manage_repository',
                                                          id=id,
                                                          message=error_message,
                                                          status='error' ) )
def update_for_browsing( trans, repository, current_working_dir, commit_message='' ):
    # This method id deprecated, but we'll keep it around for a while in case we need it.  The problem is that hg purge
    # is not supported by the mercurial API.
    # Make a copy of a repository's files for browsing, remove from disk all files that are not tracked, and commit all
    # added, modified or removed files that have not yet been committed.
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    # The following will delete the disk copy of only the files in the repository.
    #os.system( 'hg update -r null > /dev/null 2>&1' )
    files_to_remove_from_disk = []
    files_to_commit = []
    # We may have files on disk in the repo directory that aren't being tracked, so they must be removed.
    # The codes used to show the status of files are as follows.
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    # We'll use mercurial's purge extension to remove untracked file.  Using this extension requires the
    # following entry in the repository's hgrc file which was not required for some time, so we'll add it
    # if it's missing.
    # [extensions]
    # hgext.purge=
    lines = repo.opener( 'hgrc', 'rb' ).readlines()
    if not '[extensions]\n' in lines:
        # No extensions have been added at all, so just append to the file.
        fp = repo.opener( 'hgrc', 'a' )
        fp.write( '[extensions]\n' )
        fp.write( 'hgext.purge=\n' )
        fp.close()
    elif not 'hgext.purge=\n' in lines:
        # The file includes and [extensions] section, but we need to add the
        # purge extension.
        fp = repo.opener( 'hgrc', 'wb' )
        for line in lines:
            if line.startswith( '[extensions]' ):
                fp.write( line )
                fp.write( 'hgext.purge=\n' )
            else:
                fp.write( line )
        fp.close()
    cmd = 'hg purge'
    os.chdir( repo_dir )
    proc = subprocess.Popen( args=cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
    return_code = proc.wait()
    os.chdir( current_working_dir )
    if return_code != 0:
        output = proc.stdout.read( 32768 )
        log.debug( 'hg purge failed in repository directory %s, reason: %s' % ( repo_dir, output ) )
    if files_to_commit:
        if not commit_message:
            commit_message = 'Committed changes to: %s' % ', '.join( files_to_commit )
        repo.dirstate.write()
        repo.commit( user=trans.user.username, text=commit_message )
    cmd = 'hg update > /dev/null 2>&1'
    os.chdir( repo_dir )
    proc = subprocess.Popen( args=cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
    return_code = proc.wait()
    os.chdir( current_working_dir )
    if return_code != 0:
        output = proc.stdout.read( 32768 )
        log.debug( 'hg update > /dev/null 2>&1 failed in repository directory %s, reason: %s' % ( repo_dir, output ) )
