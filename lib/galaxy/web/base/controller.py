"""
Contains functionality needed in every web interface
"""
import os, time, logging, re, string, sys, glob
from datetime import datetime, timedelta
from galaxy import config, tools, web, util
from galaxy.web import error, form, url_for
from galaxy.model.orm import *
from galaxy.workflow.modules import *
from galaxy.web.framework import simplejson

from Cheetah.Template import Template

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

# RE that tests for valid slug.
VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )
    
class BaseController( object ):
    """
    Base class for Galaxy web application controllers.
    """
    def __init__( self, app ):
        """Initialize an interface for application 'app'"""
        self.app = app
    def get_toolbox(self):
        """Returns the application toolbox"""
        return self.app.toolbox
    def get_class( self, trans, class_name ):
        """ Returns the class object that a string denotes. Without this method, we'd have to do eval(<class_name>). """
        if class_name == 'History':
            item_class = trans.model.History
        elif class_name == 'HistoryDatasetAssociation':
            item_class = trans.model.HistoryDatasetAssociation
        elif class_name == 'Page':
            item_class = trans.model.Page
        elif class_name == 'StoredWorkflow':
            item_class = trans.model.StoredWorkflow
        elif class_name == 'Visualization':
            item_class = trans.model.Visualization
        elif class_name == 'Tool':
            item_class = trans.model.Tool
        elif class_name == 'Job':
            item_class == trans.model.Job
        else:
            item_class = None
        return item_class
        
Root = BaseController

class UsesAnnotations:
    """ Mixin for getting and setting item annotations. """
    def get_item_annotation_str( self, trans, user, item ):
        """ Returns a user's annotation string for an item. """
        annotation_obj = self.get_item_annotation_obj( trans, user, item )
        if annotation_obj:
            return annotation_obj.annotation
        return None
    def get_item_annotation_obj( self, trans, user, item ):
        """ Returns a user's annotation object for an item. """
        # Get annotation association.
        try:
            annotation_assoc_class = eval( "trans.model.%sAnnotationAssociation" % item.__class__.__name__ )
        except:
            # Item doesn't have an annotation association class and cannot be annotated.
            return False
        # Get annotation association object.
        annotation_assoc = trans.sa_session.query( annotation_assoc_class ).filter_by( user=user )
        if item.__class__ == trans.model.History:
            annotation_assoc = annotation_assoc.filter_by( history=item )
        elif item.__class__ == trans.model.HistoryDatasetAssociation:
            annotation_assoc = annotation_assoc.filter_by( hda=item )
        elif item.__class__ == trans.model.StoredWorkflow:
            annotation_assoc = annotation_assoc.filter_by( stored_workflow=item )
        elif item.__class__ == trans.model.WorkflowStep:
            annotation_assoc = annotation_assoc.filter_by( workflow_step=item )
        elif item.__class__ == trans.model.Page:
            annotation_assoc = annotation_assoc.filter_by( page=item )
        elif item.__class__ == trans.model.Visualization:
            annotation_assoc = annotation_assoc.filter_by( visualization=item )
        return annotation_assoc.first()
    def add_item_annotation( self, trans, item, annotation ):
        """ Add or update an item's annotation; a user can only have a single annotation for an item. """
        # Get/create annotation association object.
        annotation_assoc = self.get_item_annotation_obj( trans, trans.user, item )
        if not annotation_assoc:
            # Create association.
            # TODO: we could replace this eval() with a long if/else stmt, but this is more general without sacrificing
            try:
                annotation_assoc_class = eval( "trans.model.%sAnnotationAssociation" % item.__class__.__name__ )
            except:
                # Item doesn't have an annotation association class and cannot be annotated.
                return False
            annotation_assoc = annotation_assoc_class()
            item.annotations.append( annotation_assoc )
            annotation_assoc.user = trans.get_user()
        # Set annotation.
        annotation_assoc.annotation = annotation
        return True

class SharableItemSecurity:
    """ Mixin for handling security for sharable items. """
    def security_check( self, user, item, check_ownership=False, check_accessible=False ):
        """ Security checks for an item: checks if (a) user owns item or (b) item is accessible to user. """
        if check_ownership:
            # Verify ownership.
            if not user:
                error( "Must be logged in to manage Galaxy items" )
            if item.user != user:
                error( "%s is not owned by current user" % item.__class__.__name__ )
        if check_accessible:
            # Verify accessible.
            if ( item.user != user ) and ( not item.importable ) and ( user not in item.users_shared_with_dot_users ):
                error( "%s is not accessible to current user" % item.__class__.__name__ )
        return item
        
class UsesHistoryDatasetAssociation:
    """ Mixin for controllers that use HistoryDatasetAssociation objects. """
    def get_dataset( self, trans, dataset_id, check_ownership=True, check_accessible=False ):
        """ Get an HDA object by id. """
        # DEPRECATION: We still support unencoded ids for backward compatibility
        try:
            data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
            if data is None:
                raise ValueError( 'Invalid reference dataset id: %s.' % dataset_id )
        except:
            try:
                data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( int( dataset_id ) )
            except:
                data = None
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid dataset id: %s." % str( dataset_id ) )
        if check_ownership:
            # Verify ownership.
            user = trans.get_user()
            if not user:
                error( "Must be logged in to manage Galaxy items" )
            if data.history.user != user:
                error( "%s is not owned by current user" % data.__class__.__name__ )
        if check_accessible:
            current_user_roles = trans.get_current_user_roles()
            if trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
                if data.state == trans.model.Dataset.states.UPLOAD:
                    return trans.show_error_message( "Please wait until this dataset finishes uploading before attempting to view it." )
            else:
                error( "You are not allowed to access this dataset" )
        return data
    def get_data( self, dataset, preview=True ):
        """ Gets a dataset's data. """
        # Get data from file, truncating if necessary.
        truncated = False
        dataset_data = None
        if os.path.exists( dataset.file_name ):
            max_peek_size = 1000000 # 1 MB
            if preview and os.stat( dataset.file_name ).st_size > max_peek_size:
                dataset_data = open( dataset.file_name ).read(max_peek_size)
                truncated = True
            else:
                dataset_data = open( dataset.file_name ).read(max_peek_size)
                truncated = False
        return truncated, dataset_data
        
class UsesVisualization( SharableItemSecurity ):
    """ Mixin for controllers that use Visualization objects. """

    len_files = None
    
    def _get_dbkeys( self, trans ):
        """ Returns all valid dbkeys that a user can use in a visualization. """
        
        # Read len files.
        if not self.len_files:
            len_files = glob.glob(os.path.join( trans.app.config.tool_data_path, 'shared','ucsc','chrom', "*.len" ))
            self.len_files = [ os.path.split(f)[1].split(".len")[0] for f in len_files ] # get xxx.len

        user_keys = {}
        user = trans.get_user()
        if 'dbkeys' in user.preferences:
            user_keys = from_json_string( user.preferences['dbkeys'] )
        
        dbkeys = [ (v, k) for k, v in trans.db_builds if k in self.len_files or k in user_keys ]
        return dbkeys
    
    def get_visualization( self, trans, id, check_ownership=True, check_accessible=False ):
        """ Get a Visualization from the database by id, verifying ownership. """
        # Load workflow from database
        id = trans.security.decode_id( id )
        visualization = trans.sa_session.query( trans.model.Visualization ).get( id )
        if not visualization:
            error( "Visualization not found" )
        else:
            return self.security_check( trans.get_user(), visualization, check_ownership, check_accessible )
            
    def get_visualization_config( self, trans, visualization ):
        """ Returns a visualization's configuration. Only works for trackster visualizations right now. """

        config = None
        if visualization.type == 'trackster':
            # Trackster config; taken from tracks/browser
            latest_revision = visualization.latest_revision
            tracks = []

            # Set dbkey.
            try:
                dbkey = latest_revision.config['dbkey']
            except KeyError:
                dbkey = None
        
            # Set tracks.
            if 'tracks' in latest_revision.config:
                hda_query = trans.sa_session.query( trans.model.HistoryDatasetAssociation )
                for t in visualization.latest_revision.config['tracks']:
                    dataset_id = t['dataset_id']
                    try:
                        prefs = t['prefs']
                    except KeyError:
                        prefs = {}
                    dataset = hda_query.get( dataset_id )
                    track_type, _ = dataset.datatype.get_track_type()
                    tracks.append( {
                        "track_type": track_type,
                        "name": dataset.name,
                        "dataset_id": dataset.id,
                        "prefs": simplejson.dumps(prefs),
                    } )
                    if dbkey is None: dbkey = dataset.dbkey # Hack for backward compat
            
            
            ## TODO: chrom needs to be able to be set; right now it's empty.
            config = { "title": visualization.title, "vis_id": trans.security.encode_id( visualization.id ), 
                        "tracks": tracks, "chrom": "", "dbkey": dbkey }
            
        return config
        
class UsesStoredWorkflow( SharableItemSecurity ):
    """ Mixin for controllers that use StoredWorkflow objects. """
    def get_stored_workflow( self, trans, id, check_ownership=True, check_accessible=False ):
        """ Get a StoredWorkflow from the database by id, verifying ownership. """
        # Load workflow from database
        id = trans.security.decode_id( id )
        stored = trans.sa_session.query( trans.model.StoredWorkflow ).get( id )
        if not stored:
            error( "Workflow not found" )
        else:
            return self.security_check( trans.get_user(), stored, check_ownership, check_accessible )
    def get_stored_workflow_steps( self, trans, stored_workflow ):
        """ Restores states for a stored workflow's steps. """
        for step in stored_workflow.latest_workflow.steps:
            if step.type == 'tool' or step.type is None:
                # Restore the tool state for the step
                module = module_factory.from_workflow_step( trans, step )
                # Any connected input needs to have value DummyDataset (these
                # are not persisted so we need to do it every time)
                module.add_dummy_datasets( connections=step.input_connections )                  
                # Store state with the step
                step.module = module
                step.state = module.state
                # Error dict
                if step.tool_errors:
                    errors[step.id] = step.tool_errors
            else:
                ## Non-tool specific stuff?
                step.module = module_factory.from_workflow_step( trans, step )
                step.state = step.module.get_runtime_state()
            # Connections by input name
            step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )

class UsesHistory( SharableItemSecurity ):
    """ Mixin for controllers that use History objects. """
    def get_history( self, trans, id, check_ownership=True, check_accessible=False ):
        """Get a History from the database by id, verifying ownership."""
        # Load history from database
        id = trans.security.decode_id( id )
        history = trans.sa_session.query( trans.model.History ).get( id )
        if not history:
            err+msg( "History not found" )
        else:
            return self.security_check( trans.get_user(), history, check_ownership, check_accessible )
    def get_history_datasets( self, trans, history, show_deleted=False ):
        """ Returns history's datasets. """
        query = trans.sa_session.query( trans.model.HistoryDatasetAssociation ) \
            .filter( trans.model.HistoryDatasetAssociation.history == history ) \
            .options( eagerload( "children" ) ) \
            .join( "dataset" ).filter( trans.model.Dataset.purged == False ) \
            .options( eagerload_all( "dataset.actions" ) ) \
            .order_by( trans.model.HistoryDatasetAssociation.hid )
        if not show_deleted:
            query = query.filter( trans.model.HistoryDatasetAssociation.deleted == False )
        return query.all()
            
class Sharable:
    """ Mixin for a controller that manages an item that can be shared. """
    # Implemented methods.
    @web.expose
    @web.require_login( "share Galaxy items" )
    def set_public_username( self, trans, id, username, **kwargs ):
        """ Set user's public username and delegate to sharing() """
        trans.get_user().username = username
        trans.sa_session.flush
        return self.sharing( trans, id, **kwargs )
    # Abstract methods.
    @web.expose
    @web.require_login( "modify Galaxy items" )
    def set_slug_async( self, trans, id, new_slug ):
        """ Set item slug asynchronously. """
        pass  
    @web.expose
    @web.require_login( "share Galaxy items" )
    def sharing( self, trans, id, **kwargs ):
        """ Handle item sharing. """
        pass
    @web.expose
    @web.require_login( "share Galaxy items" )
    def share( self, trans, id=None, email="", **kwd ):
        """ Handle sharing an item with a particular user. """
        pass
    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """ Display item by username and slug. """
        pass
    @web.expose
    @web.json
    @web.require_login( "get item name and link" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns item's name and link. """
        pass
    @web.expose
    @web.require_login("get item content asynchronously")
    def get_item_content_async( self, trans, id ):
        """ Returns item content in HTML format. """
        pass
    # Helper methods.
    def _make_item_accessible( self, sa_session, item ):
        """ Makes item accessible--viewable and importable--and sets item's slug. Does not flush/commit changes, however. Item must have name, user, importable, and slug attributes. """
        item.importable = True
        self.create_item_slug( sa_session, item )
    def create_item_slug( self, sa_session, item ):
        """ Create item slug. Slug is unique among user's importable items for item's class. Returns true if item's slug was set; false otherwise. """
        if item.slug is None or item.slug == "":
            # Item can have either a name or a title.
            if hasattr( item, 'name' ):
                item_name = item.name
            elif hasattr( item, 'title' ):
                item_name = item.title
            # Replace whitespace with '-'
            slug_base = re.sub( "\s+", "-", item_name.lower() )
            # Remove all non-alphanumeric characters.
            slug_base = re.sub( "[^a-zA-Z0-9\-]", "", slug_base )
            # Remove trailing '-'.
            if slug_base.endswith('-'):
                slug_base = slug_base[:-1]
            # Make sure that slug is not taken; if it is, add a number to it.
            slug = slug_base
            count = 1
            while sa_session.query( item.__class__ ).filter_by( user=item.user, slug=slug, importable=True ).count() != 0:
                # Slug taken; choose a new slug based on count. This approach can handle numerous histories with the same name gracefully.
                slug = '%s-%i' % ( slug_base, count )
                count += 1
            item.slug = slug
            return True
        return False
        
"""
Deprecated: `BaseController` used to be available under the name `Root`
"""
class ControllerUnavailable( Exception ):
    pass

class Admin( object ):
    # Override these
    user_list_grid = None
    role_list_grid = None
    group_list_grid = None
    
    @web.expose
    @web.require_admin
    def index( self, trans, **kwd ):
        webapp = kwd.get( 'webapp', 'galaxy' )
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if webapp == 'galaxy':
            return trans.fill_template( '/webapps/galaxy/admin/index.mako',
                                        webapp=webapp,
                                        message=message,
                                        status=status )
        else:
            return trans.fill_template( '/webapps/community/admin/index.mako',
                                        webapp=webapp,
                                        message=message,
                                        status=status )
    @web.expose
    @web.require_admin
    def center( self, trans, **kwd ):
        webapp = kwd.get( 'webapp', 'galaxy' )
        if webapp == 'galaxy':
            return trans.fill_template( '/webapps/galaxy/admin/center.mako' )
        else:
            return trans.fill_template( '/webapps/community/admin/center.mako' )
    @web.expose
    @web.require_admin
    def reload_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/admin/reload_tool.mako',
                                    toolbox=self.app.toolbox,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def tool_reload( self, trans, tool_version=None, **kwd ):
        params = util.Params( kwd )
        tool_id = params.tool_id
        self.app.toolbox.reload( tool_id )
        message = 'Reloaded tool: ' + tool_id
        return trans.fill_template( '/admin/reload_tool.mako',
                                    toolbox=self.app.toolbox,
                                    message=message,
                                    status='done' )
    
    # Galaxy Role Stuff
    @web.expose
    @web.require_admin
    def roles( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "roles":
                return self.role( trans, **kwargs )
            if operation == "create":
                return self.create_role( trans, **kwargs )
            if operation == "delete":
                return self.mark_role_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_role( trans, **kwargs )
            if operation == "purge":
                return self.purge_role( trans, **kwargs )
            if operation == "manage users and groups":
                return self.manage_users_and_groups_for_role( trans, **kwargs )
            if operation == "rename":
                return self.rename_role( trans, **kwargs )
        # Render the list view
        return self.role_list_grid( trans, **kwargs )
    @web.expose
    @web.require_admin
    def create_role( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if params.get( 'create_role_button', False ):
            name = util.restore_text( params.name )
            description = util.restore_text( params.description )
            in_users = util.listify( params.get( 'in_users', [] ) )
            in_groups = util.listify( params.get( 'in_groups', [] ) )
            create_group_for_role = params.get( 'create_group_for_role', 'no' )
            if not name or not description:
                message = "Enter a valid name and a description"
            elif trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.name==name ).first():
                message = "A role with that name already exists"
            else:
                # Create the role
                role = trans.app.model.Role( name=name, description=description, type=trans.app.model.Role.types.ADMIN )
                trans.sa_session.add( role )
                # Create the UserRoleAssociations
                for user in [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in in_users ]:
                    ura = trans.app.model.UserRoleAssociation( user, role )
                    trans.sa_session.add( ura )
                # Create the GroupRoleAssociations
                for group in [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in in_groups ]:
                    gra = trans.app.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                if create_group_for_role == 'yes':
                    # Create the group
                    group = trans.app.model.Group( name=name )
                    trans.sa_session.add( group )
                    message = "Group '%s' has been created, and role '%s' has been created with %d associated users and %d associated groups" % \
                    ( group.name, role.name, len( in_users ), len( in_groups ) )
                else:
                    message = "Role '%s' has been created with %d associated users and %d associated groups" % ( role.name, len( in_users ), len( in_groups ) )
                trans.sa_session.flush()
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='create_role',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        out_users = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted==False ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            out_users.append( ( user.id, user.email ) )
        out_groups = []
        for group in trans.sa_session.query( trans.app.model.Group ) \
                                     .filter( trans.app.model.Group.table.c.deleted==False ) \
                                     .order_by( trans.app.model.Group.table.c.name ):
            out_groups.append( ( group.id, group.name ) )
        return trans.fill_template( '/admin/dataset_security/role/role_create.mako',
                                    in_users=[],
                                    out_users=out_users,
                                    in_groups=[],
                                    out_groups=out_groups,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def rename_role( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No role ids received for renaming"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        role = get_role( trans, id )
        if params.get( 'rename_role_button', False ):
            old_name = role.name
            new_name = util.restore_text( params.name )
            new_description = util.restore_text( params.description )
            if not new_name:
                message = 'Enter a valid name'
                status='error'
            elif trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.name==new_name ).first():
                message = 'A role with that name already exists'
                status = 'error'
            else:
                role.name = new_name
                role.description = new_description
                trans.sa_session.add( role )
                trans.sa_session.flush()
                message = "Role '%s' has been renamed to '%s'" % ( old_name, new_name )
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='roles',
                                                                  webapp=webapp,
                                                                  message=util.sanitize_text( message ),
                                                                  status='done' ) )
        return trans.fill_template( '/admin/dataset_security/role/role_rename.mako',
                                    role=role,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def manage_users_and_groups_for_role( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No role ids received for managing users and groups"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        role = get_role( trans, id )
        if params.get( 'role_members_edit_button', False ):
            in_users = [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in util.listify( params.in_users ) ]
            for ura in role.users:
                user = trans.sa_session.query( trans.app.model.User ).get( ura.user_id )
                if user not in in_users:
                    # Delete DefaultUserPermissions for previously associated users that have been removed from the role
                    for dup in user.default_permissions:
                        if role == dup.role:
                            trans.sa_session.delete( dup )
                    # Delete DefaultHistoryPermissions for previously associated users that have been removed from the role
                    for history in user.histories:
                        for dhp in history.default_permissions:
                            if role == dhp.role:
                                trans.sa_session.delete( dhp )
                    trans.sa_session.flush()
            in_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( params.in_groups ) ]
            trans.app.security_agent.set_entity_role_associations( roles=[ role ], users=in_users, groups=in_groups )
            trans.sa_session.refresh( role )
            message = "Role '%s' has been updated with %d associated users and %d associated groups" % ( role.name, len( in_users ), len( in_groups ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )            
        in_users = []
        out_users = []
        in_groups = []
        out_groups = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted==False ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user in [ x.user for x in role.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        for group in trans.sa_session.query( trans.app.model.Group ) \
                                     .filter( trans.app.model.Group.table.c.deleted==False ) \
                                     .order_by( trans.app.model.Group.table.c.name ):
            if group in [ x.group for x in role.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        library_dataset_actions = {}
        if webapp == 'galaxy':
            # Build a list of tuples that are LibraryDatasetDatasetAssociationss followed by a list of actions
            # whose DatasetPermissions is associated with the Role
            # [ ( LibraryDatasetDatasetAssociation [ action, action ] ) ]
            for dp in role.dataset_actions:
                for ldda in trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ) \
                                            .filter( trans.app.model.LibraryDatasetDatasetAssociation.dataset_id==dp.dataset_id ):
                    root_found = False
                    folder_path = ''
                    folder = ldda.library_dataset.folder
                    while not root_found:
                        folder_path = '%s / %s' % ( folder.name, folder_path )
                        if not folder.parent:
                            root_found = True
                        else:
                            folder = folder.parent
                    folder_path = '%s %s' % ( folder_path, ldda.name )
                    library = trans.sa_session.query( trans.app.model.Library ) \
                                              .filter( trans.app.model.Library.table.c.root_folder_id == folder.id ) \
                                              .first()
                    if library not in library_dataset_actions:
                        library_dataset_actions[ library ] = {}
                    try:
                        library_dataset_actions[ library ][ folder_path ].append( dp.action )
                    except:
                        library_dataset_actions[ library ][ folder_path ] = [ dp.action ]
        return trans.fill_template( '/admin/dataset_security/role/role.mako',
                                    role=role,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    library_dataset_actions=library_dataset_actions,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def mark_role_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for deleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d roles: " % len( ids )
        for role_id in ids:
            role = get_role( trans, role_id )
            role.deleted = True
            trans.sa_session.add( role )
            trans.sa_session.flush()
            message += " %s " % role.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def undelete_role( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_roles = ""
        for role_id in ids:
            role = get_role( trans, role_id )
            if not role.deleted:
                message = "Role '%s' has not been deleted, so it cannot be undeleted." % role.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            role.deleted = False
            trans.sa_session.add( role )
            trans.sa_session.flush()
            count += 1
            undeleted_roles += " %s" % role.name
        message = "Undeleted %d roles: %s" % ( count, undeleted_roles )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def purge_role( self, trans, **kwd ):
        # This method should only be called for a Role that has previously been deleted.
        # Purging a deleted Role deletes all of the following from the database:
        # - UserRoleAssociations where role_id == Role.id
        # - DefaultUserPermissions where role_id == Role.id
        # - DefaultHistoryPermissions where role_id == Role.id
        # - GroupRoleAssociations where role_id == Role.id
        # - DatasetPermissionss where role_id == Role.id
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d roles: " % len( ids )
        for role_id in ids:
            role = get_role( trans, role_id )
            if not role.deleted:
                message = "Role '%s' has not been deleted, so it cannot be purged." % role.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            # Delete UserRoleAssociations
            for ura in role.users:
                user = trans.sa_session.query( trans.app.model.User ).get( ura.user_id )
                # Delete DefaultUserPermissions for associated users
                for dup in user.default_permissions:
                    if role == dup.role:
                        trans.sa_session.delete( dup )
                # Delete DefaultHistoryPermissions for associated users
                for history in user.histories:
                    for dhp in history.default_permissions:
                        if role == dhp.role:
                            trans.sa_session.delete( dhp )
                trans.sa_session.delete( ura )
            # Delete GroupRoleAssociations
            for gra in role.groups:
                trans.sa_session.delete( gra )
            # Delete DatasetPermissionss
            for dp in role.dataset_actions:
                trans.sa_session.delete( dp )
            trans.sa_session.flush()
            message += " %s " % role.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    # Galaxy Group Stuff
    @web.expose
    @web.require_admin
    def groups( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "groups":
                return self.group( trans, **kwargs )
            if operation == "create":
                return self.create_group( trans, **kwargs )
            if operation == "delete":
                return self.mark_group_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_group( trans, **kwargs )
            if operation == "purge":
                return self.purge_group( trans, **kwargs )
            if operation == "manage users and roles":
                return self.manage_users_and_roles_for_group( trans, **kwargs )
            if operation == "rename":
                return self.rename_group( trans, **kwargs )
        # Render the list view
        return self.group_list_grid( trans, **kwargs )
    @web.expose
    @web.require_admin
    def rename_group( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No group ids received for renaming"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        group = get_group( trans, id )
        if params.get( 'rename_group_button', False ):
            old_name = group.name
            new_name = util.restore_text( params.name )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            elif trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.name==new_name ).first():
                message = 'A group with that name already exists'
                status = 'error'
            else:
                group.name = new_name
                trans.sa_session.add( group )
                trans.sa_session.flush()
                message = "Group '%s' has been renamed to '%s'" % ( old_name, new_name )
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='groups',
                                                                  webapp=webapp,
                                                                  message=util.sanitize_text( message ),
                                                                  status='done' ) )
        return trans.fill_template( '/admin/dataset_security/group/group_rename.mako',
                                    group=group,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def manage_users_and_roles_for_group( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        group = get_group( trans, params.id )
        if params.get( 'group_roles_users_edit_button', False ):
            in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( params.in_roles ) ]
            in_users = [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in util.listify( params.in_users ) ]
            trans.app.security_agent.set_entity_group_associations( groups=[ group ], roles=in_roles, users=in_users )
            trans.sa_session.refresh( group )
            message += "Group '%s' has been updated with %d associated roles and %d associated users" % ( group.name, len( in_roles ), len( in_users ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        in_roles = []
        out_roles = []
        in_users = []
        out_users = []
        for role in trans.sa_session.query(trans.app.model.Role ) \
                                    .filter( trans.app.model.Role.table.c.deleted==False ) \
                                    .order_by( trans.app.model.Role.table.c.name ):
            if role in [ x.role for x in group.roles ]:
                in_roles.append( ( role.id, role.name ) )
            else:
                out_roles.append( ( role.id, role.name ) )
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted==False ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user in [ x.user for x in group.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        message += 'Group %s is currently associated with %d roles and %d users' % ( group.name, len( in_roles ), len( in_users ) )
        return trans.fill_template( '/admin/dataset_security/group/group.mako',
                                    group=group,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    in_users=in_users,
                                    out_users=out_users,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def create_group( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if params.get( 'create_group_button', False ):
            name = util.restore_text( params.name )
            in_users = util.listify( params.get( 'in_users', [] ) )
            in_roles = util.listify( params.get( 'in_roles', [] ) )
            if not name:
                message = "Enter a valid name"
            elif trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.name==name ).first():
                message = "A group with that name already exists"
            else:
                # Create the group
                group = trans.app.model.Group( name=name )
                trans.sa_session.add( group )
                trans.sa_session.flush()
                # Create the UserRoleAssociations
                for user in [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in in_users ]:
                    uga = trans.app.model.UserGroupAssociation( user, group )
                    trans.sa_session.add( uga )
                    trans.sa_session.flush()
                # Create the GroupRoleAssociations
                for role in [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in in_roles ]:
                    gra = trans.app.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                    trans.sa_session.flush()
                message = "Group '%s' has been created with %d associated users and %d associated roles" % ( name, len( in_users ), len( in_roles ) )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='create_group',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        out_users = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted==False ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            out_users.append( ( user.id, user.email ) )
        out_roles = []
        for role in trans.sa_session.query( trans.app.model.Role ) \
                                    .filter( trans.app.model.Role.table.c.deleted==False ) \
                                    .order_by( trans.app.model.Role.table.c.name ):
            out_roles.append( ( role.id, role.name ) )
        return trans.fill_template( '/admin/dataset_security/group/group_create.mako',
                                    in_users=[],
                                    out_users=out_users,
                                    in_roles=[],
                                    out_roles=out_roles,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def mark_group_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = params.get( 'id', None )
        if not id:
            message = "No group ids received for marking deleted"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d groups: " % len( ids )
        for group_id in ids:
            group = get_group( trans, group_id )
            group.deleted = True
            trans.sa_session.add( group )
            trans.sa_session.flush()
            message += " %s " % group.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def undelete_group( self, trans, **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No group ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_groups = ""
        for group_id in ids:
            group = get_group( trans, group_id )
            if not group.deleted:
                message = "Group '%s' has not been deleted, so it cannot be undeleted." % group.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            group.deleted = False
            trans.sa_session.add( group )
            trans.sa_session.flush()
            count += 1
            undeleted_groups += " %s" % group.name
        message = "Undeleted %d groups: %s" % ( count, undeleted_groups )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def purge_group( self, trans, **kwd ):
        # This method should only be called for a Group that has previously been deleted.
        # Purging a deleted Group simply deletes all UserGroupAssociations and GroupRoleAssociations.
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No group ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d groups: " % len( ids )
        for group_id in ids:
            group = get_group( trans, group_id )
            if not group.deleted:
                # We should never reach here, but just in case there is a bug somewhere...
                message = "Group '%s' has not been deleted, so it cannot be purged." % group.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            # Delete UserGroupAssociations
            for uga in group.users:
                trans.sa_session.delete( uga )
            # Delete GroupRoleAssociations
            for gra in group.roles:
                trans.sa_session.delete( gra )
            trans.sa_session.flush()
            message += " %s " % group.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    # Galaxy User Stuff
    @web.expose
    @web.require_admin
    def create_new_user( self, trans, **kwargs ):
        webapp = kwargs.get( 'webapp', 'galaxy' )
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='create',
                                                          webapp=webapp,
                                                          admin_view=True ) )
    @web.expose
    @web.require_admin
    def reset_user_password( self, trans, **kwd ):
        webapp = kwd.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for resetting passwords"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        if 'reset_user_password_button' in kwd:
            message = ''
            status = ''
            for user_id in ids:
                user = get_user( trans, user_id )
                password = kwd.get( 'password', None )
                confirm = kwd.get( 'confirm' , None )
                if len( password ) < 6:
                    message = "Please use a password of at least 6 characters"
                    status = 'error'
                    break
                elif password != confirm:
                    message = "Passwords do not match"
                    status = 'error'
                    break
                else:
                    user.set_password_cleartext( password )
                    trans.sa_session.add( user )
                    trans.sa_session.flush()
            if not message and not status:
                message = "Passwords reset for %d users" % len( ids )
                status = 'done'
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        users = [ get_user( trans, user_id ) for user_id in ids ]
        if len( ids ) > 1:
            id=','.join( id )
        return trans.fill_template( '/admin/user/reset_password.mako',
                                    id=id,
                                    users=users,
                                    password='',
                                    confirm='',
                                    webapp=webapp )
    @web.expose
    @web.require_admin
    def mark_user_deleted( self, trans, **kwd ):
        webapp = kwd.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for deleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d users: " % len( ids )
        for user_id in ids:
            user = get_user( trans, user_id )
            user.deleted = True
            trans.sa_session.add( user )
            trans.sa_session.flush()
            message += " %s " % user.email
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='users',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def undelete_user( self, trans, **kwd ):
        webapp = kwd.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       webapp=webapp,
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_users = ""
        for user_id in ids:
            user = get_user( trans, user_id )
            if not user.deleted:
                message = "User '%s' has not been deleted, so it cannot be undeleted." % user.email
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            user.deleted = False
            trans.sa_session.add( user )
            trans.sa_session.flush()
            count += 1
            undeleted_users += " %s" % user.email
        message = "Undeleted %d users: %s" % ( count, undeleted_users )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='users',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def purge_user( self, trans, **kwd ):
        # This method should only be called for a User that has previously been deleted.
        # We keep the User in the database ( marked as purged ), and stuff associated
        # with the user's private role in case we want the ability to unpurge the user 
        # some time in the future.
        # Purging a deleted User deletes all of the following:
        # - History where user_id = User.id
        #    - HistoryDatasetAssociation where history_id = History.id
        #    - Dataset where HistoryDatasetAssociation.dataset_id = Dataset.id
        # - UserGroupAssociation where user_id == User.id
        # - UserRoleAssociation where user_id == User.id EXCEPT FOR THE PRIVATE ROLE
        # Purging Histories and Datasets must be handled via the cleanup_datasets.py script
        webapp = kwd.get( 'webapp', 'galaxy' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d users: " % len( ids )
        for user_id in ids:
            user = get_user( trans, user_id )
            if not user.deleted:
                # We should never reach here, but just in case there is a bug somewhere...
                message = "User '%s' has not been deleted, so it cannot be purged." % user.email
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            private_role = trans.app.security_agent.get_private_user_role( user )
            # Delete History
            for h in user.active_histories:
                trans.sa_session.refresh( h )
                for hda in h.active_datasets:
                    # Delete HistoryDatasetAssociation
                    d = trans.sa_session.query( trans.app.model.Dataset ).get( hda.dataset_id )
                    # Delete Dataset
                    if not d.deleted:
                        d.deleted = True
                        trans.sa_session.add( d )
                    hda.deleted = True
                    trans.sa_session.add( hda )
                h.deleted = True
                trans.sa_session.add( h )
            # Delete UserGroupAssociations
            for uga in user.groups:
                trans.sa_session.delete( uga )
            # Delete UserRoleAssociations EXCEPT FOR THE PRIVATE ROLE
            for ura in user.roles:
                if ura.role_id != private_role.id:
                    trans.sa_session.delete( ura )
            # Purge the user
            user.purged = True
            trans.sa_session.add( user )
            trans.sa_session.flush()
            message += "%s " % user.email
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='users',
                                                   webapp=webapp,
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def users( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "roles":
                return self.user( trans, **kwargs )
            if operation == "reset password":
                return self.reset_user_password( trans, **kwargs )
            if operation == "delete":
                return self.mark_user_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_user( trans, **kwargs )
            if operation == "purge":
                return self.purge_user( trans, **kwargs )
            if operation == "create":
                return self.create_new_user( trans, **kwargs )
            if operation == "information":
                return self.user_info( trans, **kwargs )
            if operation == "manage roles and groups":
                return self.manage_roles_and_groups_for_user( trans, **kwargs )
            if operation == "tools_by_user":
                # This option is called via the ToolsColumn link in a grid subclass,
                # so we need to add user_id to kwargs since id in the subclass is tool.id,
                # and update the current sort filter, using the grid subclass's default
                # sort filter instead of this class's.
                kwargs[ 'user_id' ] = kwargs[ 'id' ]
                kwargs[ 'sort' ] = 'name'
                return self.browse_tools( trans, **kwargs )
        # Render the list view
        return self.user_list_grid( trans, **kwargs )
    @web.expose
    @web.require_admin
    def user_info( self, trans, **kwd ):
        '''
        This method displays the user information page which consists of login 
        information, public username, reset password & other user information 
        obtained during registration
        '''
        webapp = kwd.get( 'webapp', 'galaxy' )
        user_id = kwd.get( 'id', None )
        if not user_id:
            message += "Invalid user id (%s) received" % str( user_id )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        user = get_user( trans, user_id )
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='show_info',
                                                          user_id=user.id,
                                                          admin_view=True,
                                                          **kwd ) )
    @web.expose
    @web.require_admin
    def name_autocomplete_data( self, trans, q=None, limit=None, timestamp=None ):
        """Return autocomplete data for user emails"""
        ac_data = ""
        for user in trans.sa_session.query( User ).filter_by( deleted=False ).filter( func.lower( User.email ).like( q.lower() + "%" ) ):
            ac_data = ac_data + user.email + "\n"
        return ac_data
    @web.expose
    @web.require_admin
    def manage_roles_and_groups_for_user( self, trans, **kwd ):
        webapp = kwd.get( 'webapp', 'galaxy' )
        user_id = kwd.get( 'id', None )
        message = ''
        status = ''
        if not user_id:
            message += "Invalid user id (%s) received" % str( user_id )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       webapp=webapp,
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        user = get_user( trans, user_id )
        private_role = trans.app.security_agent.get_private_user_role( user )
        if kwd.get( 'user_roles_groups_edit_button', False ):
            # Make sure the user is not dis-associating himself from his private role
            out_roles = kwd.get( 'out_roles', [] )
            if out_roles:
                out_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( out_roles ) ]
            if private_role in out_roles:
                message += "You cannot eliminate a user's private role association.  "
                status = 'error'
            in_roles = kwd.get( 'in_roles', [] )
            if in_roles:
                in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( in_roles ) ]
            out_groups = kwd.get( 'out_groups', [] )
            if out_groups:
                out_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( out_groups ) ]
            in_groups = kwd.get( 'in_groups', [] )
            if in_groups:
                in_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( in_groups ) ]
            if in_roles:
                trans.app.security_agent.set_entity_user_associations( users=[ user ], roles=in_roles, groups=in_groups )
                trans.sa_session.refresh( user )
                message += "User '%s' has been updated with %d associated roles and %d associated groups (private roles are not displayed)" % \
                    ( user.email, len( in_roles ), len( in_groups ) )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           webapp=webapp,
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
        in_roles = []
        out_roles = []
        in_groups = []
        out_groups = []
        for role in trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.deleted==False ) \
                                                                  .order_by( trans.app.model.Role.table.c.name ):
            if role in [ x.role for x in user.roles ]:
                in_roles.append( ( role.id, role.name ) )
            elif role.type != trans.app.model.Role.types.PRIVATE:
                # There is a 1 to 1 mapping between a user and a PRIVATE role, so private roles should
                # not be listed in the roles form fields, except for the currently selected user's private
                # role, which should always be in in_roles.  The check above is added as an additional
                # precaution, since for a period of time we were including private roles in the form fields.
                out_roles.append( ( role.id, role.name ) )
        for group in trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.deleted==False ) \
                                                                    .order_by( trans.app.model.Group.table.c.name ):
            if group in [ x.group for x in user.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        message += "User '%s' is currently associated with %d roles and is a member of %d groups" % \
            ( user.email, len( in_roles ), len( in_groups ) )
        if not status:
            status = 'done'
        return trans.fill_template( '/admin/user/user.mako',
                                    user=user,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def memdump( self, trans, ids = 'None', sorts = 'None', pages = 'None', new_id = None, new_sort = None, **kwd ):
        if self.app.memdump is None:
            return trans.show_error_message( "Memdump is not enabled (set <code>use_memdump = True</code> in universe_wsgi.ini)" )
        heap = self.app.memdump.get()
        p = util.Params( kwd )
        msg = None
        if p.dump:
            heap = self.app.memdump.get( update = True )
            msg = "Heap dump complete"
        elif p.setref:
            self.app.memdump.setref()
            msg = "Reference point set (dump to see delta from this point)"
        ids = ids.split( ',' )
        sorts = sorts.split( ',' )
        if new_id is not None:
            ids.append( new_id )
            sorts.append( 'None' )
        elif new_sort is not None:
            sorts[-1] = new_sort
        breadcrumb = "<a href='%s' class='breadcrumb'>heap</a>" % web.url_for()
        # new lists so we can assemble breadcrumb links
        new_ids = []
        new_sorts = []
        for id, sort in zip( ids, sorts ):
            new_ids.append( id )
            if id != 'None':
                breadcrumb += "<a href='%s' class='breadcrumb'>[%s]</a>" % ( web.url_for( ids=','.join( new_ids ), sorts=','.join( new_sorts ) ), id )
                heap = heap[int(id)]
            new_sorts.append( sort )
            if sort != 'None':
                breadcrumb += "<a href='%s' class='breadcrumb'>.by('%s')</a>" % ( web.url_for( ids=','.join( new_ids ), sorts=','.join( new_sorts ) ), sort )
                heap = heap.by( sort )
        ids = ','.join( new_ids )
        sorts = ','.join( new_sorts )
        if p.theone:
            breadcrumb += ".theone"
            heap = heap.theone
        return trans.fill_template( '/admin/memdump.mako', heap = heap, ids = ids, sorts = sorts, breadcrumb = breadcrumb, msg = msg )

    @web.expose
    @web.require_admin
    def jobs( self, trans, stop = [], stop_msg = None, cutoff = 180, **kwd ):
        deleted = []
        msg = None
        status = None
        job_ids = util.listify( stop )
        if job_ids and stop_msg in [ None, '' ]:
            msg = 'Please enter an error message to display to the user describing why the job was terminated'
            status = 'error'
        elif job_ids:
            if stop_msg[-1] not in string.punctuation:
                stop_msg += '.'
            for job_id in job_ids:
                trans.app.job_manager.job_stop_queue.put( job_id, error_msg="This job was stopped by an administrator: %s  For more information or help" % stop_msg )
                deleted.append( str( job_id ) )
        if deleted:
            msg = 'Queued job'
            if len( deleted ) > 1:
                msg += 's'
            msg += ' for deletion: '
            msg += ', '.join( deleted )
            status = 'done'
        cutoff_time = datetime.utcnow() - timedelta( seconds=int( cutoff ) )
        jobs = trans.sa_session.query( trans.app.model.Job ) \
                               .filter( and_( trans.app.model.Job.table.c.update_time < cutoff_time,
                                              or_( trans.app.model.Job.state == trans.app.model.Job.states.NEW,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.QUEUED,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.RUNNING,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.UPLOAD ) ) ) \
                               .order_by( trans.app.model.Job.table.c.update_time.desc() )
        last_updated = {}
        for job in jobs:
            delta = datetime.utcnow() - job.update_time
            if delta > timedelta( minutes=60 ):
                last_updated[job.id] = '%s hours' % int( delta.seconds / 60 / 60 )
            else:
                last_updated[job.id] = '%s minutes' % int( delta.seconds / 60 )
        return trans.fill_template( '/admin/jobs.mako',
                                    jobs = jobs,
                                    last_updated = last_updated,
                                    cutoff = cutoff,
                                    msg = msg,
                                    status = status )

## ---- Utility methods -------------------------------------------------------
        
def get_user( trans, id ):
    """Get a User from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    user = trans.sa_session.query( trans.model.User ).get( id )
    if not user:
        return trans.show_error_message( "User not found for id (%s)" % str( id ) )
    return user
def get_role( trans, id ):
    """Get a Role from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    role = trans.sa_session.query( trans.model.Role ).get( id )
    if not role:
        return trans.show_error_message( "Role not found for id (%s)" % str( id ) )
    return role
def get_group( trans, id ):
    """Get a Group from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    group = trans.sa_session.query( trans.model.Group ).get( id )
    if not group:
        return trans.show_error_message( "Group not found for id (%s)" % str( id ) )
    return group
