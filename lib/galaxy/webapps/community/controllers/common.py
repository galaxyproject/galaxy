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

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

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
def get_repository_metadata( trans, id, changeset_revision ):
    """Get metadata for a specified repository change set from the database"""
    return trans.sa_session.query( trans.model.RepositoryMetadata ) \
                           .filter( and_( trans.model.RepositoryMetadata.table.c.repository_id == trans.security.decode_id( id ),
                                          trans.model.RepositoryMetadata.table.c.changeset_revision == changeset_revision ) ) \
                           .first()
def set_repository_metadata( trans, id, ctx_str, **kwd ):
    """Set repository metadata"""
    message = ''
    status = 'done'
    repository = get_repository( trans, id )
    repo_dir = repository.repo_path
    repo = hg.repository( ui.ui(), repo_dir )
    change_set = get_change_set( trans, repo, ctx_str )
    invalid_tool_configs = []
    flush_needed = False
    if change_set is not None:
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
                                repository_metadata = get_repository_metadata( trans, id, repository.tip )
                                tool_requirements = []
                                for tr in tool.requirements:
                                    requirement_dict = dict( name=tr.name,
                                                             type=tr.type,
                                                             version=tr.version )
                                    tool_requirements.append( requirement_dict )
                                tool_dict = dict( id = tool.id,
                                                  name = tool.name,
                                                  version = tool.version,
                                                  description = tool.description,
                                                  tool_config = os.path.join( root, name ),
                                                  requirements = tool_requirements )
                                if repository_metadata:
                                    metadata = repository_metadata.metadata
                                    if metadata and 'tools' in metadata:
                                        metadata_tools = metadata[ 'tools' ]
                                        found = False
                                        for tool_metadata_dict in metadata_tools:
                                            if 'id' in tool_metadata_dict and tool_metadata_dict[ 'id' ] == tool.id and \
                                                'version' in tool_metadata_dict and tool_metadata_dict[ 'version' ] == tool.version:
                                                found = True
                                                tool_metadata_dict[ 'name' ] = tool.name
                                                tool_metadata_dict[ 'description' ] = tool.description
                                                tool_metadata_dict[ 'tool_config' ] = os.path.join( root, name )
                                                tool_metadata_dict[ 'requirements' ] = tool_requirements
                                                flush_needed = True
                                        if not found:
                                            metadata_tools.append( tool_dict )
                                    else:
                                        if metadata is None:
                                            repository_metadata.metadata = {}
                                        repository_metadata.metadata[ 'tools' ] = [ tool_dict ]
                                        trans.sa_session.add( repository_metadata )
                                        if not flush_needed:
                                            flush_needed = True
                                else:
                                    if 'tools' in metadata_dict:
                                        metadata_dict[ 'tools' ].append( tool_dict )
                                    else:
                                        metadata_dict[ 'tools' ] = [ tool_dict ]
                        except Exception, e:
                            invalid_tool_configs.append( ( name, str( e ) ) )
        repository_metadata = trans.model.RepositoryMetadata( repository.id, repository.tip, metadata_dict )
        trans.sa_session.add( repository_metadata )
        if not flush_needed:
            flush_needed = True
    else:
        message = "Repository does not include changeset revision '%s'." % str( ctx_str )
        status = 'error'
    if invalid_tool_configs:
        message = "Metadata cannot be defined for change set revision '%s'.  Correct the following problems and reset metadata.<br/>" % str( ctx_str )
        for itc_tup in invalid_tool_configs:
            message += "<b>%s</b> - %s<br/>" % ( itc_tup[0], itc_tup[1] )
        status = 'error'
    elif flush_needed:
        # We only flush if there are no tool config errors, so change sets will only have metadata
        # if everything in them is valid.
        trans.sa_session.flush()
    return message, status
def get_repository_by_name( trans, name ):
    """Get a repository from the database via name"""
    return trans.sa_session.query( app.model.Repository ).filter_by( name=name ).one()
def get_change_set( trans, repo, ctx_str, **kwd ):
    """Retrieve a specified change set from a repository"""
    for changeset in repo.changelog:
        ctx = repo.changectx( changeset )
        if str( ctx ) == ctx_str:
            return ctx
    return None
def get_user( trans, id ):
    """Get a user from the database"""
    return trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( id ) )
def handle_email_alerts( trans, repository ):
    repo_dir = repository.repo_path
    repo = hg.repository( ui.ui(), repo_dir )
    smtp_server = trans.app.config.smtp_server
    if smtp_server and repository.email_alerts:
        # Send email alert to users that want them.
        if trans.app.config.email_alerts_from is not None:
            email_alerts_from = trans.app.config.email_alerts_from
        elif trans.request.host.split( ':' )[0] == 'localhost':
            email_alerts_from = 'galaxy-no-reply@' + socket.getfqdn()
        else:
            email_alerts_from = 'galaxy-no-reply@' + trans.request.host.split( ':' )[0]
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
        frm = email_alerts_from
        subject = "Galaxy tool shed repository update alert"
        email_alerts = from_json_string( repository.email_alerts )
        for email in email_alerts:
            to = email.strip()
            # Send it
            try:
                util.send_mail( frm, to, subject, body, trans.app.config )
            except Exception, e:
                log.exception( "An error occurred sending a tool shed repository update alert by email." )
def update_for_browsing( repository, current_working_dir ):
    # Make a copy of a repository's files for browsing.
    repo_dir = repository.repo_path
    repo = hg.repository( ui.ui(), repo_dir )
    # The following will delete the disk copy of only the files in the repository.
    #os.system( 'hg update -r null > /dev/null 2>&1' )
    repo.ui.pushbuffer()
    commands.status( repo.ui, repo, all=True )
    status_and_file_names = repo.ui.popbuffer().strip().split( "\n" )
    # status_and_file_names looks something like:
    # ['? MY_README_AGAIN', '? galaxy_tmap_tool/tmap-0.0.9.tar.gz', '? dna_filtering.py', 'C filtering.py', 'C filtering.xml']
    # The codes used to show the status of files are:
    # M = modified
    # A = added
    # R = removed
    # C = clean
    # ! = deleted, but still tracked
    # ? = not tracked
    # I = ignored
    # We'll remove all files that are not tracked or ignored.
    files_to_remove_from_disk = []
    for status_and_file_name in status_and_file_names:
        if status_and_file_name.startswith( '?' ) or status_and_file_name.startswith( 'I' ):
            files_to_remove_from_disk.append( os.path.abspath( os.path.join( repo_dir, status_and_file_name.split()[1] ) ) )
    for full_path in files_to_remove_from_disk:
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
