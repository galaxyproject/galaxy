import os, string, socket, logging
from time import strftime
from datetime import *
from galaxy.tools import *
from galaxy.util.json import from_json_string, to_json_string
from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.model.orm import *
from galaxy.model.item_attrs import UsesItemRatings
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

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
def get_repository_metadata_by_changeset_revision( trans, id, changeset_revision ):
    """Get metadata for a specified repository change set from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( and_( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ),
                                          trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                           .first()
def get_repository_metadata_by_id( trans, id ):
    """Get repository metadata from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ).get( trans.security.decode_id( id ) )
def get_revision_label( trans, repository, changeset_revision ):
    """
    Return a string consisting of the human read-able 
    changeset rev and the changeset revision string.
    """
    repo = hg.repository( get_configured_ui(), repository.repo_path )
    ctx = get_changectx_for_changeset( trans, repo, changeset_revision )
    if ctx:
        return "%s:%s" % ( str( ctx.rev() ), changeset_revision )
    else:
        return "-1:%s" % changeset_revision
def get_latest_repository_metadata( trans, id ):
    """Get last metadata defined for a specified repository from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) ) \
                           .order_by( trans.model.RepositoryMetadata.table.c.update_time.desc() ) \
                           .first()
def generate_workflow_metadata( trans, id, changeset_revision, exported_workflow_dict, metadata_dict ):
    """
    Update the received metadata_dict with changes that have been applied
    to the received exported_workflow_dict.  Store everything except the
    workflow steps in the database.
    """
    workflow_dict = { 'a_galaxy_workflow' : exported_workflow_dict[ 'a_galaxy_workflow' ],
                      'name' :exported_workflow_dict[ 'name' ],
                      'annotation' : exported_workflow_dict[ 'annotation' ],
                      'format-version' : exported_workflow_dict[ 'format-version' ] }
    if 'workflows' in metadata_dict:
        metadata_dict[ 'workflows' ].append( workflow_dict )
    else:
        metadata_dict[ 'workflows' ] = [ workflow_dict ]
    return metadata_dict
def new_workflow_metadata_required( trans, id, metadata_dict ):
    """
    TODO: Currently everything about an exported workflow except the name is hard-coded, so
    there's no real way to differentiate versions of exported workflows.  If this changes at
    some future time, this method should be enhanced accordingly...
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
    # The received metadata_dict includes no metadata for workflows, so a new repository_metadata table
    # record is not needed.
    return False
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
def generate_tool_metadata( trans, id, changeset_revision, root, name, tool, metadata_dict ):
    """
    Update the received metadata_dict with changes that have been
    applied to the received tool.
    """
    repository = get_repository( trans, id )
    tool_requirements = []
    for tr in tool.requirements:
        requirement_dict = dict( name=tr.name,
                                 type=tr.type,
                                 version=tr.version )
        tool_requirements.append( requirement_dict )
    tool_tests = []
    if tool.tests:
        for ttb in tool.tests:
            test_dict = dict( name=ttb.name,
                              required_files=ttb.required_files,
                              inputs=ttb.inputs,
                              outputs=ttb.outputs )
            tool_tests.append( test_dict )
    tool_dict = dict( id=tool.id,
                      guid = generate_tool_guid( trans, repository, tool ),
                      name=tool.name,
                      version=tool.version,
                      description=tool.description,
                      version_string_cmd = tool.version_string_cmd,
                      tool_config=os.path.join( root, name ),
                      requirements=tool_requirements,
                      tests=tool_tests )
    if 'tools' in metadata_dict:
        metadata_dict[ 'tools' ].append( tool_dict )
    else:
        metadata_dict[ 'tools' ] = [ tool_dict ]
    return metadata_dict
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
def set_repository_metadata( trans, id, changeset_revision, **kwd ):
    """Set repository metadata"""
    message = ''
    status = 'done'
    repository = get_repository( trans, id )
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    invalid_files = []
    ctx = get_changectx_for_changeset( trans, repo, changeset_revision )
    if ctx is not None:
        metadata_dict = {}
        for root, dirs, files in os.walk( repo_dir ):
            if not root.find( '.hg' ) >= 0 and not root.find( 'hgrc' ) >= 0:
                if '.hg' in dirs:
                    # Don't visit .hg directories - should be impossible since we don't
                    # allow uploaded archives that contain .hg dirs, but just in case...
                    dirs.remove( '.hg' )
                if 'hgrc' in files:
                     # Don't include hgrc files in commit.
                    files.remove( 'hgrc' )
                for name in files:
                    # Find all tool configs.
                    if name.endswith( '.xml' ):
                        try:
                            full_path = os.path.abspath( os.path.join( root, name ) )
                            tool = load_tool( trans, full_path )
                            if tool is not None:
                                # Update the list metadata dictionaries for tools in metadata_dict.
                                metadata_dict = generate_tool_metadata( trans, id, changeset_revision, root, name, tool, metadata_dict )
                        except Exception, e:
                            invalid_files.append( ( name, str( e ) ) )
                    # Find all exported workflows
                    elif name.endswith( '.ga' ):
                        try:
                            full_path = os.path.abspath( os.path.join( root, name ) )
                            # Convert workflow data from json
                            fp = open( full_path, 'rb' )
                            workflow_text = fp.read()
                            fp.close()
                            exported_workflow_dict = from_json_string( workflow_text )
                            # Update the list of metadata dictionaries for workflows in metadata_dict.
                            metadata_dict = generate_workflow_metadata( trans, id, changeset_revision, exported_workflow_dict, metadata_dict )
                        except Exception, e:
                            invalid_files.append( ( name, str( e ) ) )
        if metadata_dict:
            if new_tool_metadata_required( trans, id, metadata_dict ) or new_workflow_metadata_required( trans, id, metadata_dict ):
                # Create a new repository_metadata table row.
                repository_metadata = trans.model.RepositoryMetadata( repository.id, changeset_revision, metadata_dict )
                trans.sa_session.add( repository_metadata )
                trans.sa_session.flush()
            else:
                # Update the last saved repository_metadata table row.
                repository_metadata = get_latest_repository_metadata( trans, id )
                repository_metadata.changeset_revision = changeset_revision
                repository_metadata.metadata = metadata_dict
                trans.sa_session.add( repository_metadata )
                trans.sa_session.flush()
    else:
        # change_set is None
        message = "Repository does not include changeset revision '%s'." % str( changeset_revision )
        status = 'error'
    if invalid_files:
        message = "Metadata cannot be defined for change set revision '%s'.  Correct the following problems and reset metadata.<br/>" % str( changeset_revision )
        for itc_tup in invalid_files:
            tool_file = itc_tup[0]
            exception_msg = itc_tup[1]
            if exception_msg.find( 'No such file or directory' ) >= 0:
                exception_items = exception_msg.split()
                missing_file_items = exception_items[7].split( '/' )
                missing_file = missing_file_items[-1].rstrip( '\'' )
                correction_msg = "This file refers to a missing file <b>%s</b>.  " % str( missing_file )
                if exception_msg.find( '.loc' ) >= 0:
                    # Handle the special case where a tool depends on a missing xxx.loc file by telliing
                    # the user to upload xxx.loc.sample to the repository so that it can be copied to
                    # ~/tool-data/xxx.loc.  In this case, exception_msg will look something like:
                    # [Errno 2] No such file or directory: '/Users/gvk/central/tool-data/blast2go.loc'
                    sample_loc_file = '%s.sample' % str( missing_file )
                    correction_msg += "Upload a file named <b>%s</b> to the repository to correct this error." % sample_loc_file
                else:
                    correction_msg += "Upload a file named <b>%s</b> to the repository to correct this error." % missing_file
            elif exception_msg.find( 'Data table named' ) >= 0:
                # Handle the special case where the tool requires an entry in the tool_data_table.conf file.
                # In this case, exception_msg will look something like:
                # Data table named 'tmap_indexes' is required by tool but not configured
                exception_items = exception_msg.split()
                name_attr = exception_items[3].lstrip( '\'' ).rstrip( '\'' )
                message += "<b>%s</b> - This tool requires an entry in the tool_data_table_conf.xml file.  " % tool_file
                message += "Complete and <b>Save</b> the form below to resolve this issue.<br/>"
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='add_tool_data_table_entry',
                                                                  name_attr=name_attr,
                                                                  repository_id=id,
                                                                  message=message,
                                                                  status='error' ) )
            else:
               correction_msg = exception_msg
            message += "<b>%s</b> - %s<br/>" % ( tool_file, correction_msg )
        status = 'error'
    return message, status
def get_repository_by_name( trans, name ):
    """Get a repository from the database via name"""
    return trans.sa_session.query( app.model.Repository ).filter_by( name=name ).one()
def get_changectx_for_changeset( trans, repo, changeset_revision, **kwd ):
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
def copy_sample_loc_file( trans, filename ):
    """Copy xxx.loc.sample to ~/tool-data/xxx.loc"""
    sample_loc_file = os.path.split( filename )[1]
    loc_file = os.path.split( filename )[1].rstrip( '.sample' )
    tool_data_path = os.path.abspath( trans.app.config.tool_data_path )
    if not ( os.path.exists( os.path.join( tool_data_path, loc_file ) ) or os.path.exists( os.path.join( tool_data_path, sample_loc_file ) ) ):
        shutil.copy( os.path.abspath( filename ), os.path.join( tool_data_path, sample_loc_file ) )
        shutil.copy( os.path.abspath( filename ), os.path.join( tool_data_path, loc_file ) )
def get_configured_ui():
    # Configure any desired ui settings.
    _ui = ui.ui()
    # The following will suppress all messages.  This is
    # the same as adding the following setting to the repo
    # hgrc file' [ui] section:
    # quiet = True
    _ui.setconfig( 'ui', 'quiet', True )
    return _ui
def get_user( trans, id ):
    """Get a user from the database"""
    return trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( id ) )
def handle_email_alerts( trans, repository ):
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    smtp_server = trans.app.config.smtp_server
    if smtp_server and repository.email_alerts:
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
        # Build the email message
        body = string.Template( email_alert_template ) \
            .safe_substitute( host=trans.request.host,
                              repository_name=repository.name,
                              revision='%s:%s' %( str( ctx.rev() ), ctx ),
                              display_date=display_date,
                              description=ctx.description(),
                              username=username )
        frm = email_from
        subject = "Galaxy tool shed repository update alert"
        email_alerts = from_json_string( repository.email_alerts )
        for email in email_alerts:
            to = email.strip()
            # Send it
            try:
                util.send_mail( frm, to, subject, body, trans.app.config )
            except Exception, e:
                log.exception( "An error occurred sending a tool shed repository update alert by email." )
def update_for_browsing( trans, repository, current_working_dir, commit_message='' ):
    # Make a copy of a repository's files for browsing, remove from disk all files that
    # are not tracked, and commit all added, modified or removed files that have not yet
    # been committed.
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    # The following will delete the disk copy of only the files in the repository.
    #os.system( 'hg update -r null > /dev/null 2>&1' )
    repo.ui.pushbuffer()
    commands.status( repo.ui, repo, all=True )
    status_and_file_names = repo.ui.popbuffer().strip().split( "\n" )
    # status_and_file_names looks something like:
    # ['? README', '? tmap_tool/tmap-0.0.9.tar.gz', '? dna_filtering.py', 'C filtering.py', 'C filtering.xml']
    # The codes used to show the status of files are:
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    files_to_remove_from_disk = []
    files_to_commit = []
    for status_and_file_name in status_and_file_names:
        if status_and_file_name.startswith( '?' ) or status_and_file_name.startswith( 'I' ):
            files_to_remove_from_disk.append( os.path.abspath( os.path.join( repo_dir, status_and_file_name.split()[1] ) ) )
        elif status_and_file_name.startswith( 'M' ) or status_and_file_name.startswith( 'A' ) or status_and_file_name.startswith( 'R' ):
            files_to_commit.append( os.path.abspath( os.path.join( repo_dir, status_and_file_name.split()[1] ) ) )
    for full_path in files_to_remove_from_disk:
        # We'll remove all files that are not tracked or ignored.
        if os.path.isdir( full_path ):
            try:
                os.rmdir( full_path )
            except OSError, e:
                # The directory is not empty
                pass
        elif os.path.isfile( full_path ):
            os.remove( full_path )
            dir = os.path.split( full_path )[0]
            try:
                os.rmdir( dir )
            except OSError, e:
                # The directory is not empty
                pass
    if files_to_commit:
        if not commit_message:
            commit_message = 'Committed changes to: %s' % ', '.join( files_to_commit )
        repo.dirstate.write()
        repo.commit( user=trans.user.username, text=commit_message )
    os.chdir( repo_dir )
    os.system( 'hg update > /dev/null 2>&1' )
    os.chdir( current_working_dir )
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
def build_changeset_revision_select_field( trans, repository, selected_value=None, add_id_to_name=True ):
    """
    Build a SelectField whose options are the changeset_revision
    strings of all downloadable_revisions of the received repository.
    """
    repo = hg.repository( get_configured_ui(), repository.repo_path )
    options = []
    refresh_on_change_values = []
    for repository_metadata in repository.downloadable_revisions:
        changeset_revision = repository_metadata.changeset_revision
        revision_label = get_revision_label( trans, repository, changeset_revision )
        options.append( ( revision_label, changeset_revision ) )
        refresh_on_change_values.append( changeset_revision )
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
