import os, string, socket, logging, simplejson, binascii, tempfile, filecmp
from time import strftime
from datetime import *
from galaxy.datatypes.checkers import *
from galaxy.tools import *
from galaxy.util.json import from_json_string, to_json_string
from galaxy.util.hash_util import *
# TODO: re-factor shed_util to eliminate the following restricted imports
from galaxy.util.shed_util import check_tool_input_params, clone_repository, concat_messages, copy_sample_file, create_or_update_repository_metadata
from galaxy.util.shed_util import generate_clone_url_for_repository_in_tool_shed, generate_message_for_invalid_tools, generate_metadata_for_changeset_revision
from galaxy.util.shed_util import get_changectx_for_changeset, get_config_from_disk, get_configured_ui, get_file_context_from_ctx, get_named_tmpfile_from_ctx
from galaxy.util.shed_util import get_parent_id, get_repository_in_tool_shed, get_repository_metadata_by_changeset_revision
from galaxy.util.shed_util import handle_sample_files_and_load_tool_from_disk, handle_sample_files_and_load_tool_from_tmp_config, INITIAL_CHANGELOG_HASH
from galaxy.util.shed_util import is_downloadable, load_tool_from_config, remove_dir, reset_tool_data_tables, reversed_upper_bounded_changelog, strip_path
from galaxy.web.base.controller import *
from galaxy.web.base.controllers.admin import *
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

# String separator
STRSEP = '__ESEP__'

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

def add_tool_versions( trans, id, repository_metadata, changeset_revisions ):
    # Build a dictionary of { 'tool id' : 'parent tool id' } pairs for each tool in repository_metadata.
    metadata = repository_metadata.metadata
    tool_versions_dict = {}
    for tool_dict in metadata.get( 'tools', [] ):
        # We have at least 2 changeset revisions to compare tool guids and tool ids.
        parent_id = get_parent_id( trans,
                                   id,
                                   tool_dict[ 'id' ],
                                   tool_dict[ 'version' ],
                                   tool_dict[ 'guid' ],
                                   changeset_revisions )
        tool_versions_dict[ tool_dict[ 'guid' ] ] = parent_id
    if tool_versions_dict:
        repository_metadata.tool_versions = tool_versions_dict
        trans.sa_session.add( repository_metadata )
        trans.sa_session.flush()
def can_use_tool_config_disk_file( trans, repository, repo, file_path, changeset_revision ):
    """
    Determine if repository's tool config file on disk can be used.  This method is restricted to tool config files since, with the
    exception of tool config files, multiple files with the same name will likely be in various directories in the repository and we're
    comparing file names only (not relative paths).
    """
    if not file_path or not os.path.exists( file_path ):
        # The file no longer exists on disk, so it must have been deleted at some previous point in the change log.
        return False
    if changeset_revision == repository.tip:
        return True
    file_name = strip_path( file_path )
    latest_version_of_file = get_latest_tool_config_revision_from_repository_manifest( repo, file_name, changeset_revision )
    can_use_disk_file = filecmp.cmp( file_path, latest_version_of_file )
    try:
        os.unlink( latest_version_of_file )
    except:
        pass
    return can_use_disk_file
def changeset_is_malicious( trans, id, changeset_revision, **kwd ):
    """Check the malicious flag in repository metadata for a specified change set"""
    repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
    if repository_metadata:
        return repository_metadata.malicious
    return False
def changeset_revision_reviewed_by_user( trans, user, repository, changeset_revision ):
    """Determine if the current changeset revision has been reviewed by the current user."""
    changeset_revision_reviewed_by_user = False
    for review in repository.reviews:
        if review.changeset_revision == changeset_revision and review.user == user:
            return True
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
def get_absolute_path_to_file_in_repository( repo_files_dir, file_name ):
    file_path = None
    found = False
    for root, dirs, files in os.walk( repo_files_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == file_name:
                    file_path = os.path.abspath( os.path.join( root, name ) )
                    found = True
                    break
        if found:
            break
    return file_path
def get_category( trans, id ):
    """Get a category from the database"""
    return trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( id ) )
def get_category_by_name( trans, name ):
    """Get a category from the database via name"""
    try:
        return trans.sa_session.query( trans.model.Category ).filter_by( name=name ).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return None
def get_categories( trans ):
    """Get all categories from the database"""
    return trans.sa_session.query( trans.model.Category ) \
                           .filter( trans.model.Category.table.c.deleted==False ) \
                           .order_by( trans.model.Category.table.c.name ) \
                           .all()
def get_component( trans, id ):
    """Get a component from the database"""
    return trans.sa_session.query( trans.model.Component ).get( trans.security.decode_id( id ) )
def get_component_by_name( trans, name ):
    return trans.sa_session.query( trans.app.model.Component ) \
                           .filter( trans.app.model.Component.table.c.name==name ) \
                           .first()
def get_component_review( trans, id ):
    """Get a component_review from the database"""
    return trans.sa_session.query( trans.model.ComponentReview ).get( trans.security.decode_id( id ) )
def get_component_review_by_repository_review_id_component_id( trans, repository_review_id, component_id ):
    """Get a component_review from the database via repository_review_id and component_id"""
    return trans.sa_session.query( trans.model.ComponentReview ) \
                           .filter( and_( trans.model.ComponentReview.table.c.repository_review_id == trans.security.decode_id( repository_review_id ),
                                          trans.model.ComponentReview.table.c.component_id == trans.security.decode_id( component_id ) ) ) \
                           .first()
def get_components( trans ):
    return trans.sa_session.query( trans.app.model.Component ) \
                           .order_by( trans.app.model.Component.name ) \
                           .all()
def get_latest_repository_metadata( trans, decoded_repository_id ):
    """Get last metadata defined for a specified repository from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( trans.model.RepositoryMetadata.table.c.repository_id == decoded_repository_id ) \
                           .order_by( trans.model.RepositoryMetadata.table.c.id.desc() ) \
                           .first()
def get_latest_tool_config_revision_from_repository_manifest( repo, filename, changeset_revision ):
    """
    Get the latest revision of a tool config file named filename from the repository manifest up to the value of changeset_revision.
    This method is restricted to tool_config files rather than any file since it is likely that, with the exception of tool config files,
    multiple files will have the same name in various directories within the repository.
    """
    stripped_filename = strip_path( filename )
    for changeset in reversed_upper_bounded_changelog( repo, changeset_revision ):
        manifest_ctx = repo.changectx( changeset )
        for ctx_file in manifest_ctx.files():
            ctx_file_name = strip_path( ctx_file )
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
def get_previous_downloadable_changset_revision( repository, repo, before_changeset_revision ):
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
    if len( changeset_tups ) == 1:
        changeset_tup = changeset_tups[ 0 ]
        current_changeset_revision = changeset_tup[ 1 ]
        if current_changeset_revision == before_changeset_revision:
            return INITIAL_CHANGELOG_HASH
        return current_changeset_revision
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
def get_previous_repository_reviews( trans, repository, changeset_revision ):
    """Return an ordered dictionary of repository reviews up to and including the received changeset revision."""
    repo = hg.repository( get_configured_ui(), repository.repo_path )
    reviewed_revision_hashes = [ review.changeset_revision for review in repository.reviews ]
    previous_reviews_dict = odict()
    for changeset in reversed_upper_bounded_changelog( repo, changeset_revision ):
        previous_changeset_revision = str( repo.changectx( changeset ) )
        if previous_changeset_revision in reviewed_revision_hashes:
            previous_rev, previous_changeset_revision_label = get_rev_label_from_changeset_revision( repo, previous_changeset_revision )
            revision_reviews = get_reviews_by_repository_id_changeset_revision( trans,
                                                                                trans.security.encode_id( repository.id ),
                                                                                previous_changeset_revision )
            previous_reviews_dict[ previous_changeset_revision ] = dict( changeset_revision_label=previous_changeset_revision_label,
                                                                         reviews=revision_reviews )
    return previous_reviews_dict
def get_rev_label_changeset_revision_from_repository_metadata( repository_metadata, repository=None ):
    if repository is None:
        repository = repository_metadata.repository
    repo = hg.repository( get_configured_ui(), repository.repo_path )
    changeset_revision = repository_metadata.changeset_revision
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        rev = '%04d' % ctx.rev()
        label = "%s:%s" % ( str( ctx.rev() ), changeset_revision )
    else:
        rev = '-1'
        label = "-1:%s" % changeset_revision
    return rev, label, changeset_revision
def get_rev_label_from_changeset_revision( repo, changeset_revision ):
    ctx = get_changectx_for_changeset( repo, changeset_revision )
    if ctx:
        rev = '%04d' % ctx.rev()
        label = "%s:%s" % ( str( ctx.rev() ), changeset_revision )
    else:
        rev = '-1'
        label = "-1:%s" % changeset_revision
    return rev, label
def get_reversed_changelog_changesets( repo ):
    reversed_changelog = []
    for changeset in repo.changelog:
        reversed_changelog.insert( 0, changeset )
    return reversed_changelog
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
def get_repository_metadata_by_id( trans, id ):
    """Get repository metadata from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ).get( trans.security.decode_id( id ) )
def get_repository_metadata_by_repository_id( trans, id ):
    """Get all metadata records for a specified repository."""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ) )
def get_repository_metadata_revisions_for_review( repository, reviewed=True ):
    repository_metadata_revisions = []
    metadata_changeset_revision_hashes = []
    if reviewed:
        for metadata_revision in repository.metadata_revisions:
            metadata_changeset_revision_hashes.append( metadata_revision.changeset_revision )
        for review in repository.reviews:
            if review.changeset_revision in metadata_changeset_revision_hashes:
                rmcr_hashes = [ rmr.changeset_revision for rmr in repository_metadata_revisions ]
                if review.changeset_revision not in rmcr_hashes:
                    repository_metadata_revisions.append( review.repository_metadata )
    else:
        for review in repository.reviews:
            if review.changeset_revision not in metadata_changeset_revision_hashes:
                metadata_changeset_revision_hashes.append( review.changeset_revision )
        for metadata_revision in repository.metadata_revisions:
            if metadata_revision.changeset_revision not in metadata_changeset_revision_hashes:
                repository_metadata_revisions.append( metadata_revision )
    return repository_metadata_revisions
def get_review( trans, id ):
    """Get a repository_review from the database via id"""
    return trans.sa_session.query( trans.model.RepositoryReview ).get( trans.security.decode_id( id ) )
def get_review_by_repository_id_changeset_revision_user_id( trans, repository_id, changeset_revision, user_id ):
    """Get a repository_review from the database via repository id, changeset_revision and user_id"""
    return trans.sa_session.query( trans.model.RepositoryReview ) \
                           .filter( and_( trans.model.RepositoryReview.repository_id == trans.security.decode_id( repository_id ),
                                          trans.model.RepositoryReview.changeset_revision == changeset_revision,
                                          trans.model.RepositoryReview.user_id == trans.security.decode_id( user_id ) ) ) \
                           .first()
def get_reviews_by_repository_id_changeset_revision( trans, repository_id, changeset_revision ):
    """Get all repository_reviews from the database via repository id and changeset_revision"""
    return trans.sa_session.query( trans.model.RepositoryReview ) \
                           .filter( and_( trans.model.RepositoryReview.repository_id == trans.security.decode_id( repository_id ),
                                          trans.model.RepositoryReview.changeset_revision == changeset_revision ) ) \
                           .all()
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
def has_previous_repository_reviews( trans, repository, changeset_revision ):
    """Determine if a repository has a changeset revision review prior to the received changeset revision."""
    repo = hg.repository( get_configured_ui(), repository.repo_path )
    reviewed_revision_hashes = [ review.changeset_revision for review in repository.reviews ]
    for changeset in reversed_upper_bounded_changelog( repo, changeset_revision ):
        previous_changeset_revision = str( repo.changectx( changeset ) )
        if previous_changeset_revision in reviewed_revision_hashes:
            return True
    return False
def load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_config_filename ):
    """
    Return a loaded tool whose tool config file name (e.g., filtering.xml) is the value of tool_config_filename.  The value of changeset_revision
    is a valid (downloadable) changset revision.  The tool config will be located in the repository manifest between the received valid changeset
    revision and the first changeset revision in the repository, searching backwards.
    """
    original_tool_data_path = trans.app.config.tool_data_path
    repository = get_repository_in_tool_shed( trans, repository_id )
    repo_files_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_files_dir )
    message = ''
    tool = None
    can_use_disk_file = False
    tool_config_filepath = get_absolute_path_to_file_in_repository( repo_files_dir, tool_config_filename )
    work_dir = tempfile.mkdtemp()
    can_use_disk_file = can_use_tool_config_disk_file( trans, repository, repo, tool_config_filepath, changeset_revision )
    if can_use_disk_file:
        trans.app.config.tool_data_path = work_dir
        tool, valid, message, sample_files = handle_sample_files_and_load_tool_from_disk( trans, repo_files_dir, tool_config_filepath, work_dir )
        if tool is not None:
            invalid_files_and_errors_tups = check_tool_input_params( trans.app,
                                                                     repo_files_dir,
                                                                     tool_config_filename,
                                                                     tool,
                                                                     sample_files )
            if invalid_files_and_errors_tups:
                message2 = generate_message_for_invalid_tools( invalid_files_and_errors_tups,
                                                               repository,
                                                               metadata_dict=None,
                                                               as_html=True,
                                                               displaying_invalid_tool=True )
                message = concat_messages( message, message2 )
                status = 'error'
    else:
        tool, message, sample_files = handle_sample_files_and_load_tool_from_tmp_config( trans, repo, changeset_revision, tool_config_filename, work_dir )
    remove_dir( work_dir )
    trans.app.config.tool_data_path = original_tool_data_path
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    reset_tool_data_tables( trans.app )
    return repository, tool, message
def new_tool_metadata_required( trans, repository, metadata_dict ):
    """
    Compare the last saved metadata for each tool in the repository with the new metadata in metadata_dict to determine if a new repository_metadata
    table record is required, or if the last saved metadata record can be updated instead.
    """
    if 'tools' in metadata_dict:
        repository_metadata = get_latest_repository_metadata( trans, repository.id )
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
            # There is no saved repository metadata, so we need to create a new repository_metadata table record.
            return True
    # The received metadata_dict includes no metadata for tools, so a new repository_metadata table record is not needed.
    return False
def new_workflow_metadata_required( trans, repository, metadata_dict ):
    """
    Currently everything about an exported workflow except the name is hard-coded, so there's no real way to differentiate versions of
    exported workflows.  If this changes at some future time, this method should be enhanced accordingly.
    """
    if 'workflows' in metadata_dict:
        repository_metadata = get_latest_repository_metadata( trans, repository.id )
        if repository_metadata:
            # The repository has metadata, so update the workflows value - no new record is needed.
            return False
        else:
            # There is no saved repository metadata, so we need to create a new repository_metadata table record.
            return True
    # The received metadata_dict includes no metadata for workflows, so a new repository_metadata table record is not needed.
    return False
def set_repository_metadata( trans, repository, content_alert_str='', **kwd ):
    """
    Set metadata using the repository's current disk files, returning specific error messages (if any) to alert the repository owner that the changeset
    has problems.
    """
    message = ''
    status = 'done'
    encoded_id = trans.security.encode_id( repository.id )
    repository_clone_url = generate_clone_url_for_repository_in_tool_shed( trans, repository )
    repo_dir = repository.repo_path
    repo = hg.repository( get_configured_ui(), repo_dir )
    metadata_dict, invalid_file_tups = generate_metadata_for_changeset_revision( app=trans.app,
                                                                                 repository=repository,
                                                                                 repository_clone_url=repository_clone_url,
                                                                                 relative_install_dir=repo_dir,
                                                                                 repository_files_dir=None,
                                                                                 resetting_all_metadata_on_repository=False,
                                                                                 updating_installed_repository=False,
                                                                                 persist=False )
    if metadata_dict:
        downloadable = is_downloadable( metadata_dict )
        repository_metadata = None
        if new_tool_metadata_required( trans, repository, metadata_dict ) or new_workflow_metadata_required( trans, repository, metadata_dict ):
            # Create a new repository_metadata table row.
            repository_metadata = create_or_update_repository_metadata( trans,
                                                                        encoded_id,
                                                                        repository,
                                                                        repository.tip,
                                                                        metadata_dict )
            # If this is the first record stored for this repository, see if we need to send any email alerts.
            if len( repository.downloadable_revisions ) == 1:
                handle_email_alerts( trans, repository, content_alert_str='', new_repo_alert=True, admin_only=False )
        else:
            repository_metadata = get_latest_repository_metadata( trans, repository.id )
            if repository_metadata:
                downloadable = is_downloadable( metadata_dict )
                # Update the last saved repository_metadata table row.
                repository_metadata.changeset_revision = repository.tip
                repository_metadata.metadata = metadata_dict
                repository_metadata.downloadable = downloadable
                trans.sa_session.add( repository_metadata )
                trans.sa_session.flush()
            else:
                # There are no tools in the repository, and we're setting metadata on the repository tip.
                repository_metadata = create_or_update_repository_metadata( trans,
                                                                            encoded_id,
                                                                            repository,
                                                                            repository.tip,
                                                                            metadata_dict )
        if 'tools' in metadata_dict and repository_metadata and status != 'error':
            # Set tool versions on the new downloadable change set.  The order of the list of changesets is critical, so we use the repo's changelog.
            changeset_revisions = []
            for changeset in repo.changelog:
                changeset_revision = str( repo.changectx( changeset ) )
                if get_repository_metadata_by_changeset_revision( trans, encoded_id, changeset_revision ):
                    changeset_revisions.append( changeset_revision )
            add_tool_versions( trans, encoded_id, repository_metadata, changeset_revisions )
    elif len( repo ) == 1 and not invalid_file_tups:
        message = "Revision '%s' includes no tools, datatypes or exported workflows for which metadata can " % str( repository.tip )
        message += "be defined so this revision cannot be automatically installed into a local Galaxy instance."
        status = "error"
    if invalid_file_tups:
        message = generate_message_for_invalid_tools( invalid_file_tups, repository, metadata_dict )
        status = 'error'
    # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
    reset_tool_data_tables( trans.app )
    return message, status
def set_repository_metadata_due_to_new_tip( trans, repository, content_alert_str=None, **kwd ):
    # Set metadata on the repository tip.
    error_message, status = set_repository_metadata( trans, repository, content_alert_str=content_alert_str, **kwd )
    if error_message:
        # If there is an error, display it.
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='manage_repository',
                                                          id=trans.security.encode_id( repository.id ),
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
