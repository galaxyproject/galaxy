import os, string, socket, logging, simplejson, binascii
from time import strftime
from datetime import *
from galaxy.datatypes.checkers import *
from galaxy.tools import *
from galaxy.util.json import from_json_string, to_json_string
from galaxy.util.hash_util import *
from galaxy.util.shed_util import copy_sample_file, get_configured_ui, generate_datatypes_metadata, generate_tool_metadata, generate_workflow_metadata
from galaxy.util.shed_util import handle_sample_tool_data_table_conf_file, to_html_escaped, to_html_str, update_repository
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

def get_categories( trans ):
    """Get all categories from the database"""
    return trans.sa_session.query( trans.model.Category ) \
                           .filter( trans.model.Category.table.c.deleted==False ) \
                           .order_by( trans.model.Category.table.c.name ).all()
def get_category( trans, id ):
    """Get a category from the database"""
    return trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( id ) )
def get_repository( trans, id ):
    """Get a repository from the database via id"""
    return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )
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
def get_latest_repository_metadata( trans, id ):
    """Get last metadata defined for a specified repository from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) ) \
                           .order_by( trans.model.RepositoryMetadata.table.c.id.desc() ) \
                           .first()
def generate_clone_url( trans, repository_id ):
    """Generate the URL for cloning a repository."""
    repository = get_repository( trans, repository_id )
    protocol, base = trans.request.base.split( '://' )
    if trans.user:
        username = '%s@' % trans.user.username
    else:
        username = ''
    return '%s://%s%s/repos/%s/%s' % ( protocol, username, base, repository.user.username, repository.name )
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
def check_tool_input_params( trans, name, tool, sample_files, invalid_files ):
    """
    Check all of the tool's input parameters, looking for any that are dynamically generated
    using external data files to make sure the files exist.
    """
    can_set_metadata = True
    correction_msg = ''
    for input_param in tool.input_params:
        if isinstance( input_param, galaxy.tools.parameters.basic.SelectToolParameter ) and input_param.is_dynamic:
            # If the tool refers to .loc files or requires an entry in the
            # tool_data_table_conf.xml, make sure all requirements exist.
            options = input_param.dynamic_options or input_param.options
            if options:
                if options.tool_data_table or options.missing_tool_data_table_name:
                    # Make sure the repository contains a tool_data_table_conf.xml.sample file.
                    sample_found = False
                    for sample_file in sample_files:
                        head, tail = os.path.split( sample_file )
                        if tail == 'tool_data_table_conf.xml.sample':
                            sample_found = True
                            error, correction_msg = handle_sample_tool_data_table_conf_file( trans.app, sample_file )
                            if error:
                                can_set_metadata = False
                                invalid_files.append( ( tail, correction_msg ) ) 
                            else:
                                options.missing_tool_data_table_name = None
                            break
                    if not sample_found:
                        can_set_metadata = False
                        correction_msg = "This file requires an entry in the tool_data_table_conf.xml file.  "
                        correction_msg += "Upload a file named tool_data_table_conf.xml.sample to the repository "
                        correction_msg += "that includes the required entry to correct this error.<br/>"
                        invalid_files.append( ( name, correction_msg ) )
                if options.index_file or options.missing_index_file:
                    # Make sure the repository contains the required xxx.loc.sample file.
                    index_file = options.index_file or options.missing_index_file
                    index_file_path, index_file_name = os.path.split( index_file )
                    sample_found = False
                    for sample_file in sample_files:
                        sample_file_path, sample_file_name = os.path.split( sample_file )
                        if sample_file_name == '%s.sample' % index_file_name:
                            copy_sample_file( trans.app, sample_file )
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
                        invalid_files.append( ( name, correction_msg ) )
    return can_set_metadata, invalid_files
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
def generate_metadata_for_repository_tip( trans, id, ctx, changeset_revision, repo, repo_dir ):
    """
    Browse the repository tip files on disk to generate metadata.  This is faster than the
    generate_metadata_for_changeset_revision() method below because fctx.data() does not have
    to be written to disk to load tools.  We also handle things like .loc.sample files and
    invalid_tool_configs here, while they are ignored in older revisions.
    """
    # If a push from the command line is occurring, update the repository files on disk before setting metadata.
    update_repository( repo, str( ctx.rev() ) )
    metadata_dict = {}
    invalid_files = []
    invalid_tool_configs = []
    sample_files = []
    datatypes_config = None
    # Find datatypes_conf.xml if it exists.
    for root, dirs, files in os.walk( repo_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == 'datatypes_conf.xml':
                    datatypes_config = os.path.abspath( os.path.join( root, name ) )
                    break
    if datatypes_config:
        metadata_dict = generate_datatypes_metadata( datatypes_config, metadata_dict )
    # Find all special .sample files.
    for root, dirs, files in os.walk( repo_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name.endswith( '.sample' ):
                    sample_files.append( os.path.abspath( os.path.join( root, name ) ) )
    # Find all tool configs and exported workflows.
    for root, dirs, files in os.walk( repo_dir ):
        if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
            if '.hg' in dirs:
                dirs.remove( '.hg' )
            for name in files:
                # Find all tool configs.
                if name != 'datatypes_conf.xml' and name.endswith( '.xml' ):
                    full_path = os.path.abspath( os.path.join( root, name ) )
                    if not ( check_binary( full_path ) or check_image( full_path ) or check_gzip( full_path )[ 0 ]
                             or check_bz2( full_path )[ 0 ] or check_zip( full_path ) ):
                        try:
                            # Make sure we're looking at a tool config and not a display application config or something else.
                            element_tree = util.parse_xml( full_path )
                            element_tree_root = element_tree.getroot()
                            is_tool = element_tree_root.tag == 'tool'
                        except Exception, e:
                            log.debug( "Error parsing %s, exception: %s" % ( full_path, str( e ) ) )
                            is_tool = False
                        if is_tool:
                            try:
                                tool = load_tool( trans, full_path )
                                valid = True
                            except Exception, e:
                                valid = False
                                invalid_files.append( ( name, str( e ) ) )
                                invalid_tool_configs.append( name )
                            if valid and tool is not None:
                                can_set_metadata, invalid_files = check_tool_input_params( trans, name, tool, sample_files, invalid_files )
                                if can_set_metadata:
                                    # Update the list of metadata dictionaries for tools in metadata_dict.
                                    tool_config = os.path.join( root, name )
                                    repository_clone_url = generate_clone_url( trans, id )
                                    metadata_dict = generate_tool_metadata( tool_config, tool, repository_clone_url, metadata_dict )
                                else:
                                    invalid_tool_configs.append( name )
                # Find all exported workflows
                elif name.endswith( '.ga' ):
                    try:
                        relative_path = os.path.join( root, name )
                        # Convert workflow data from json
                        fp = open( relative_path, 'rb' )
                        workflow_text = fp.read()
                        fp.close()
                        exported_workflow_dict = from_json_string( workflow_text )
                        if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                            metadata_dict = generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict )
                    except Exception, e:
                        invalid_files.append( ( name, str( e ) ) )
    if invalid_tool_configs:
        metadata_dict[ 'invalid_tools' ] = invalid_tool_configs
    return metadata_dict, invalid_files
def generate_metadata_for_changeset_revision( trans, id, ctx, changeset_revision, repo_dir ):
    # Browse repository files within a change set to generate metadata.
    metadata_dict = {}
    invalid_files = []
    sample_files = []
    tmp_datatypes_config = None
    # Find datatypes_conf.xml if it exists.
    for filename in ctx:
        if filename == 'datatypes_conf.xml':
            fctx = ctx[ filename ]
            # Write the contents of datatypes_config.xml to a temporary file.
            fh = tempfile.NamedTemporaryFile( 'w' )
            tmp_datatypes_config = fh.name
            fh.close()
            fh = open( tmp_datatypes_config, 'w' )
            fh.write( fctx.data() )
            fh.close()
            break
    if tmp_datatypes_config:
        metadata_dict = generate_datatypes_metadata( tmp_datatypes_config, metadata_dict )
        try:
            os.unlink( tmp_datatypes_config )
        except:
            pass
    # Get all tool config file names from the hgweb url, something like:
    # /repos/test/convert_chars1/file/e58dcf0026c7/convert_characters.xml
    for filename in ctx:
        # Find all tool configs.
        if filename != 'datatypes_conf.xml' and filename.endswith( '.xml' ):
            fctx = ctx[ filename ]
            # Write the contents of the old tool config to a temporary file.
            # TODO: figure out how to enhance the load_tool method so that a
            # temporary disk file is not necessary in order to pass the tool
            # config.
            fh = tempfile.NamedTemporaryFile( 'w' )
            tmp_filename = fh.name
            fh.close()
            fh = open( tmp_filename, 'w' )
            fh.write( fctx.data() )
            fh.close()
            if not ( check_binary( tmp_filename ) or check_image( tmp_filename ) or check_gzip( tmp_filename )[ 0 ]
                     or check_bz2( tmp_filename )[ 0 ] or check_zip( tmp_filename ) ):
                try:
                    # Make sure we're looking at a tool config and not a display application config or something else.
                    element_tree = util.parse_xml( tmp_filename )
                    element_tree_root = element_tree.getroot()
                    is_tool = element_tree_root.tag == 'tool'
                except:
                    is_tool = False
                if is_tool:
                    try:
                        tool = load_tool( trans, tmp_filename )
                        valid = True
                    except Exception, e:
                        invalid_files.append( ( filename, str( e ) ) )
                        valid = False
                    if valid and tool is not None:
                        # Update the list of metadata dictionaries for tools in metadata_dict.  Note that filename
                        # here is the relative path to the config file within the change set context, something
                        # like filtering.xml, but when the change set was the repository tip, the value was
                        # something like database/community_files/000/repo_1/filtering.xml.  This shouldn't break
                        # anything, but may result in a bit of confusion when maintaining the code / data over time.
                        # IMPORTANT NOTE:  Here we are assuming that since the current change set is not the repository
                        # tip, we do not have to handle any .loc.sample files since they would have been handled previously.
                        repository_clone_url = generate_clone_url( trans, id )
                        metadata_dict = generate_tool_metadata( filename, tool, repository_clone_url, metadata_dict )
            try:
                os.unlink( tmp_filename )
            except:
                pass
        # Find all exported workflows.
        elif filename.endswith( '.ga' ):
            try:
                fctx = ctx[ filename ]
                workflow_text = fctx.data()
                exported_workflow_dict = from_json_string( workflow_text )
                if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                    metadata_dict = generate_workflow_metadata( '', exported_workflow_dict, metadata_dict )
            except Exception, e:
                invalid_files.append( ( name, str( e ) ) )
    return metadata_dict, invalid_files
def set_repository_metadata( trans, id, changeset_revision, content_alert_str='', **kwd ):
    """Set repository metadata"""
    message = ''
    status = 'done'
    repository = get_repository( trans, id )
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    metadata_dict = {}
    invalid_files = []
    if ctx is not None:
        if changeset_revision == repository.tip:
            metadata_dict, invalid_files = generate_metadata_for_repository_tip( trans, id, ctx, changeset_revision, repo, repo_dir )
        else:
            metadata_dict, invalid_files = generate_metadata_for_changeset_revision( trans, id, ctx, changeset_revision, repo_dir )
        if metadata_dict:
            if changeset_revision == repository.tip:
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
        else:
            message = "Revision '%s' includes no tools, datatypes or exported workflows for which metadata can " % str( changeset_revision )
            message += "be defined so this revision cannot be automatically installed into a local Galaxy instance."
            status = "error"
    else:
        # change_set is None
        message = "This repository does not include revision '%s'." % str( changeset_revision )
        status = 'error'
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
                missing_file_items = exception_items[7].split( '/' )
                missing_file = missing_file_items[-1].rstrip( '\'' )
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
def reset_all_repository_metadata( trans, id, **kwd ):
    params = util.Params( kwd )
    message = util.restore_text( params.get( 'message', ''  ) )
    status = params.get( 'status', 'done' )
    repository = get_repository( trans, id )
    log.debug( "Resetting all metadata on repository: %s" % repository.name )
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    if len( repo ) == 1:
        message, status = set_repository_metadata( trans, id, repository.tip, **kwd )
        add_repository_metadata_tool_versions( trans, id, [ repository.tip ] )
    else:
        # The list of changeset_revisions refers to repository_metadata records that have been
        # created or updated.  When the following loop completes, we'll delete all repository_metadata
        # records for this repository that do not have a changeset_revision value in this list.
        changeset_revisions = []
        ancestor_changeset_revision = None
        ancestor_metadata_dict = None
        for changeset in repo.changelog:
            current_changeset_revision = str( repo.changectx( changeset ) )
            ctx = get_changectx_for_changeset( repo, current_changeset_revision )
            if current_changeset_revision == repository.tip:
                current_metadata_dict, invalid_files = generate_metadata_for_repository_tip( trans, id, ctx, current_changeset_revision, repo, repo_dir )
            else:
                current_metadata_dict, invalid_files = generate_metadata_for_changeset_revision( trans, id, ctx, current_changeset_revision, repo_dir )
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
                # Our current change set has no metadata, but our ancestor change set has metadata, so save it.
                create_or_update_repository_metadata( trans, id, repository, ancestor_changeset_revision, ancestor_metadata_dict )
                # Keep track of the changeset_revisions that we've persisted.
                changeset_revisions.append( ancestor_changeset_revision )
                ancestor_changeset_revision = None
                ancestor_metadata_dict = None
        clean_repository_metadata( trans, id, changeset_revisions )
        add_repository_metadata_tool_versions( trans, id, changeset_revisions )
def clean_repository_metadata( trans, id, changeset_revisions ):
    # Delete all repository_metadata reecords associated with the repository
    # that have a changeset_revision that is not in changeset_revisions.
    for repository_metadata in trans.sa_session.query( trans.model.RepositoryMetadata ) \
                                               .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) ):
        if repository_metadata.changeset_revision not in changeset_revisions:
            trans.sa_session.delete( repository_metadata )
            trans.sa_session.flush()
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
def compare_changeset_revisions( ancestor_changeset_revision, ancestor_metadata_dict, current_changeset_revision, current_metadata_dict ):
    # The metadata associated with ancestor_changeset_revision is ancestor_metadata_dict.  This changeset_revision
    # is an ancestor of current_changeset_revision which is associated with current_metadata_dict.
    #
    # TODO: a new repository_metadata record will be created only when this method returns the string
    # 'not equal and not subset'.  However, we're currently also returning the strings 'no metadata',
    # 'equal' and 'subset', depending upon how the 2 change sets compare.  We'll leave things this way
    # for the current time in case we discover a use for these additional result strings.
    #
    # Get information about tools.
    if 'tools' in ancestor_metadata_dict:
        ancestor_tools = ancestor_metadata_dict[ 'tools' ]
    else:
        ancestor_tools = []
    if 'tools' in current_metadata_dict:
        current_tools = current_metadata_dict[ 'tools' ]
    else:
        current_tools = []
    ancestor_guids = []
    for tool_dict in ancestor_tools:
        ancestor_guids.append( tool_dict[ 'guid' ] )
    ancestor_guids.sort()
    current_guids = []
    for tool_dict in current_tools:
        current_guids.append( tool_dict[ 'guid' ] )
    current_guids.sort()
    # Get information about workflows.
    if 'workflows' in ancestor_metadata_dict:
        ancestor_workflows = ancestor_metadata_dict[ 'workflows' ]
    else:
        ancestor_workflows = []
    if 'workflows' in current_metadata_dict:
        current_workflows = current_metadata_dict[ 'workflows' ]
    else:
        current_workflows = []
    # Get information about datatypes.
    if 'datatypes' in ancestor_metadata_dict:
        ancestor_datatypes = ancestor_metadata_dict[ 'datatypes' ]
    else:
        ancestor_datatypes = []
    if 'datatypes' in current_metadata_dict:
        current_datatypes = current_metadata_dict[ 'datatypes' ]
    else:
        current_datatypes = []
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
def get_repository_by_name( trans, name ):
    """Get a repository from the database via name"""
    return trans.sa_session.query( trans.model.Repository ).filter_by( name=name ).one()
def get_changectx_for_changeset( repo, changeset_revision, **kwd ):
    """Retrieve a specified changectx from a repository"""
    for changeset in repo.changelog:
        ctx = repo.changectx( changeset )
        if str( ctx ) == changeset_revision:
            return ctx
    return None
def change_set_is_malicious( trans, id, changeset_revision, **kwd ):
    """Check the malicious flag in repository metadata for a specified change set"""
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
    if repository_metadata:
        return repository_metadata.malicious
    return False
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
def load_tool( trans, config_file ):
    """
    Load a single tool from the file named by `config_file` and return 
    an instance of `Tool`.
    """
    # Parse XML configuration file and get the root element
    tree = util.parse_xml( config_file )
    root = tree.getroot()
    if root.tag == 'tool':
        # Allow specifying a different tool subclass to instantiate
        if root.find( "type" ) is not None:
            type_elem = root.find( "type" )
            module = type_elem.get( 'module', 'galaxy.tools' )
            cls = type_elem.get( 'class' )
            mod = __import__( module, globals(), locals(), [cls])
            ToolClass = getattr( mod, cls )
        elif root.get( 'tool_type', None ) is not None:
            ToolClass = tool_types.get( root.get( 'tool_type' ) )
        else:
            ToolClass = Tool
        return ToolClass( config_file, root, trans.app )
    return None
def load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_config ):
    repository = get_repository( trans, repository_id )
    repo = hg.repository( get_configured_ui(), repository.repo_path )
    tool = None
    message = ''
    if changeset_revision == repository.tip:
        try:
            tool = load_tool( trans, os.path.abspath( tool_config ) )
        except Exception, e:
            tool = None
            message = "Error loading tool: %s.  Clicking <b>Reset metadata</b> may correct this error." % str( e )
    else:
        # Get the tool config file name from the hgweb url, something like:
        # /repos/test/convert_chars1/file/e58dcf0026c7/convert_characters.xml
        old_tool_config_file_name = tool_config.split( '/' )[ -1 ]
        ctx = get_changectx_for_changeset( repo, changeset_revision )
        fctx = None
        for filename in ctx:
            filename_head, filename_tail = os.path.split( filename )
            if filename_tail == old_tool_config_file_name:
                fctx = ctx[ filename ]
                break
        if fctx:
            # Write the contents of the old tool config to a temporary file.
            fh = tempfile.NamedTemporaryFile( 'w' )
            tmp_filename = fh.name
            fh.close()
            fh = open( tmp_filename, 'w' )
            fh.write( fctx.data() )
            fh.close()
            try:
                tool = load_tool( trans, tmp_filename )
            except Exception, e:
                tool = None
                message = "Error loading tool: %s.  Clicking <b>Reset metadata</b> may correct this error." % str( e )
            try:
                os.unlink( tmp_filename )
            except:
                pass
        else:
            tool = None
    return tool, message
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
def encode( val ):
    if isinstance( val, dict ):
        value = simplejson.dumps( val )
    else:
        value = val
    a = hmac_new( 'ToolShedAndGalaxyMustHaveThisSameKey', value )
    b = binascii.hexlify( value )
    return "%s:%s" % ( a, b )
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
