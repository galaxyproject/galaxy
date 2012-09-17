from galaxy import model
from galaxy.model.item_attrs import *
from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, grids, iff
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web.controllers.library import LibraryListGrid
from galaxy.visualization.genomes import decode_dbkey
from galaxy.visualization.genome.visual_analytics import get_dataset_job
from galaxy.visualization.data_providers.basic import ColumnDataProvider

#
# -- Grids --
#

class NameColumn( grids.TextColumn ):
    def get_value( self, trans, grid, history ):
        return history.get_display_name()
    def get_link( self, trans, grid, history ):
        # Provide link to list all datasets in history that have a given dbkey.
        # Right now, only dbkey needs to be passed through, but pass through 
        # all for now since it's cleaner.
        d = dict( action=grid.datasets_action, show_item_checkboxes=True )
        d[ grid.datasets_param ] = trans.security.encode_id( history.id )
        for filter, value in grid.cur_filter_dict.iteritems():
            d[ "f-" + filter ] = value
        return d
        
class DbKeyPlaceholderColumn( grids.GridColumn ):
    """ Placeholder to keep track of dbkey. """
    def filter( self, trans, user, query, dbkey ):
        return query

class HistorySelectionGrid( grids.Grid ):
    """
    Grid enables user to select a history, which is then used to display 
    datasets from the history.
    """
    title = "Add Track: Select History"
    model_class = model.History
    template='/tracks/history_select_grid.mako'
    default_sort_key = "-update_time"
    datasets_action = 'list_history_datasets'
    datasets_param = "f-history"
    columns = [
        NameColumn( "History Name", key="name", filterable="standard" ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago, visible=False ),
        DbKeyPlaceholderColumn( "Dbkey", key="dbkey", model_class=model.HistoryDatasetAssociation, visible=False )
    ]
    num_rows_per_page = 10
    use_async = True
    use_paging = True
    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, purged=False, deleted=False, importing=False )
        
class LibrarySelectionGrid( LibraryListGrid ):
    """
    Grid enables user to select a Library, which is then used to display 
    datasets from the history.
    """
    title = "Add Track: Select Library"
    template='/tracks/history_select_grid.mako'
    model_class = model.Library
    datasets_action = 'list_library_datasets'
    datasets_param = "f-library"
    columns = [
        NameColumn( "Library Name", key="name", filterable="standard" )
    ]
    num_rows_per_page = 10
    use_async = True
    use_paging = True
        
class DbKeyColumn( grids.GridColumn ):
    """ Column for filtering by and displaying dataset dbkey. """
    def filter( self, trans, user, query, dbkey ):
        """ Filter by dbkey; datasets without a dbkey are returned as well. """
        # use raw SQL b/c metadata is a BLOB
        dbkey_user, dbkey = decode_dbkey( dbkey )
        dbkey = dbkey.replace("'", "\\'")
        return query.filter( or_( \
                                or_( "metadata like '%%\"dbkey\": [\"%s\"]%%'" % dbkey, "metadata like '%%\"dbkey\": \"%s\"%%'" % dbkey ), \
                                or_( "metadata like '%%\"dbkey\": [\"?\"]%%'", "metadata like '%%\"dbkey\": \"?\"%%'" ) \
                                )
                            )
                    
class HistoryColumn( grids.GridColumn ):
    """ Column for filtering by history id. """
    def filter( self, trans, user, query, history_id ):
        return query.filter( model.History.id==trans.security.decode_id(history_id) )

class HistoryDatasetsSelectionGrid( grids.Grid ):
    # Grid definition.
    available_tracks = None
    title = "Add Datasets"
    template = "tracks/history_datasets_select_grid.mako"
    model_class = model.HistoryDatasetAssociation
    default_filter = { "deleted" : "False" , "shared" : "All" }
    default_sort_key = "-hid"
    use_async = True
    use_paging = False
    columns = [
        grids.GridColumn( "Id", key="hid" ),
        grids.TextColumn( "Name", key="name", model_class=model.HistoryDatasetAssociation ),
        grids.TextColumn( "Filetype", key="extension", model_class=model.HistoryDatasetAssociation ),
        HistoryColumn( "History", key="history", visible=False ),
        DbKeyColumn( "Dbkey", key="dbkey", model_class=model.HistoryDatasetAssociation, visible=True, sortable=False )
    ]
    columns.append( 
        grids.MulticolFilterColumn( "Search name and filetype", cols_to_filter=[ columns[1], columns[2] ], 
        key="free-text-search", visible=False, filterable="standard" )
    )
    
    def get_current_item( self, trans, **kwargs ):
        """ 
        Current item for grid is the history being queried. This is a bit 
        of hack since current_item typically means the current item in the grid.
        """
        return model.History.get( trans.security.decode_id( kwargs[ 'f-history' ] ) )
    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class ).join( model.History.table ).join( model.Dataset.table )
    def apply_query_filter( self, trans, query, **kwargs ):
        if self.available_tracks is None:
             self.available_tracks = trans.app.datatypes_registry.get_available_tracks()
        return query.filter( model.HistoryDatasetAssociation.extension.in_(self.available_tracks) ) \
                    .filter( model.Dataset.state == model.Dataset.states.OK ) \
                    .filter( model.HistoryDatasetAssociation.deleted == False ) \
                    .filter( model.HistoryDatasetAssociation.visible == True )
                                     
class TracksterSelectionGrid( grids.Grid ):
    # Grid definition.
    title = "Insert into visualization"
    template = "/tracks/add_to_viz.mako"
    async_template = "/page/select_items_grid_async.mako"
    model_class = model.Visualization
    default_sort_key = "-update_time"
    use_async = True
    use_paging = False
    columns = [
        grids.TextColumn( "Title", key="title", model_class=model.Visualization, filterable="standard" ),
        grids.TextColumn( "Dbkey", key="dbkey", model_class=model.Visualization ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago )
    ]

    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class ).filter( self.model_class.deleted == False )
    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.user_id == trans.user.id )

class VisualizationListGrid( grids.Grid ):
    def get_url_args( item ):
        """
        Returns dictionary used to create item link.
        """
        controller = "visualization"
        action = item.type
        if item.type == "phyloviz":
            controller = "phyloviz"
            action = "visualization"
        return dict( controller=controller, action=action, id=item.id )

    # Grid definition
    title = "Saved Visualizations"
    model_class = model.Visualization
    default_sort_key = "-update_time"
    default_filter = dict( title="All", deleted="False", tags="All", sharing="All" )
    columns = [
        grids.TextColumn( "Title", key="title", attach_popup=True, link=get_url_args ),
        grids.TextColumn( "Type", key="type" ),
        grids.TextColumn( "Dbkey", key="dbkey" ),
        grids.IndividualTagsColumn( "Tags", key="tags", model_tag_association_class=model.VisualizationTagAssociation, filterable="advanced", grid_name="VisualizationListGrid" ),
        grids.SharingStatusColumn( "Sharing", key="sharing", filterable="advanced", sortable=False ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]    
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[2] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    global_actions = [
        grids.GridAction( "Create new visualization", dict( action='create' ) )
    ]
    operations = [
        grids.GridOperation( "View/Edit", allow_multiple=False, url_args=get_url_args ),
        grids.GridOperation( "Edit Attributes", allow_multiple=False, url_args=dict( action='edit') ),
        grids.GridOperation( "Copy", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=False, url_args=dict( action='clone') ),
        grids.GridOperation( "Share or Publish", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ), async_compatible=True, confirm="Are you sure you want to delete this visualization?" ),
    ]
    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, deleted=False )
        
class VisualizationAllPublishedGrid( grids.Grid ):
    # Grid definition
    use_panels = True
    use_async = True
    title = "Published Visualizations"
    model_class = model.Visualization
    default_sort_key = "update_time"
    default_filter = dict( title="All", username="All" )
    columns = [
        grids.PublicURLColumn( "Title", key="title", filterable="advanced" ),
        grids.OwnerAnnotationColumn( "Annotation", key="annotation", model_annotation_association_class=model.VisualizationAnnotationAssociation, filterable="advanced" ),
        grids.OwnerColumn( "Owner", key="username", model_class=model.User, filterable="advanced" ),
        grids.CommunityRatingColumn( "Community Rating", key="rating" ), 
        grids.CommunityTagsColumn( "Community Tags", key="tags", model_tag_association_class=model.VisualizationTagAssociation, filterable="advanced", grid_name="VisualizationAllPublishedGrid" ),
        grids.ReverseSortColumn( "Last Updated", key="update_time", format=time_ago )
    ]
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search title, annotation, owner, and tags", 
        cols_to_filter=[ columns[0], columns[1], columns[2], columns[4] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    def build_initial_query( self, trans, **kwargs ):
        # Join so that searching history.user makes sense.
        return trans.sa_session.query( self.model_class ).join( model.User.table )
    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.deleted==False ).filter( self.model_class.published==True )


class VisualizationController( BaseUIController, SharableMixin, UsesAnnotations, 
                                UsesVisualizationMixin, 
                                UsesItemRatings ):
    _user_list_grid = VisualizationListGrid()
    _published_list_grid = VisualizationAllPublishedGrid()
    _libraries_grid = LibrarySelectionGrid()
    _histories_grid = HistorySelectionGrid()
    _history_datasets_grid = HistoryDatasetsSelectionGrid()
    _tracks_grid = TracksterSelectionGrid()

    #
    # -- Functions for listing visualizations. --
    #

    @web.expose
    @web.require_login( "see all available libraries" )
    def list_libraries( self, trans, **kwargs ):
        """List all libraries that can be used for selecting datasets."""

        # Render the list view
        return self._libraries_grid( trans, **kwargs )

    @web.expose
    @web.require_login( "see a library's datasets that can added to this visualization" )
    def list_library_datasets( self, trans, **kwargs ):
        """List a library's datasets that can be added to a visualization."""
        
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( kwargs.get('f-library') ) )
        return trans.fill_template( '/tracks/library_datasets_select_grid.mako',
                                    cntrller="library",
                                    use_panels=False,
                                    library=library,
                                    created_ldda_ids='',
                                    hidden_folder_ids='',
                                    show_deleted=False,
                                    comptypes=[],
                                    current_user_roles=trans.get_current_user_roles(),
                                    message='',
                                    status="done" )
        
    @web.expose
    @web.require_login( "see all available histories" )
    def list_histories( self, trans, **kwargs ):
        """List all histories that can be used for selecting datasets."""
        
        # Render the list view
        return self._histories_grid( trans, **kwargs )
        
    @web.expose
    @web.require_login( "see current history's datasets that can added to this visualization" )
    def list_current_history_datasets( self, trans, **kwargs ):
        """ List a history's datasets that can be added to a visualization. """
        
        kwargs[ 'f-history' ] = trans.security.encode_id( trans.get_history().id )
        kwargs[ 'show_item_checkboxes' ] = 'True'
        return self.list_history_datasets( trans, **kwargs )
        
    @web.expose
    @web.require_login( "see a history's datasets that can added to this visualization" )
    def list_history_datasets( self, trans, **kwargs ):
        """List a history's datasets that can be added to a visualization."""

        # Render the list view
        return self._history_datasets_grid( trans, **kwargs )
    
    @web.expose
    @web.require_login( "see all available datasets" )
    def list_datasets( self, trans, **kwargs ):
        """List all datasets that can be added as tracks"""
        
        # Render the list view
        return self._data_grid( trans, **kwargs )
    
    @web.expose
    def list_tracks( self, trans, **kwargs ):
        return self._tracks_grid( trans, **kwargs )
    
    @web.expose
    def list_published( self, trans, *args, **kwargs ):
        grid = self._published_list_grid( trans, **kwargs )
        if 'async' in kwargs:
            return grid
        else:
            # Render grid wrapped in panels
            return trans.fill_template( "visualization/list_published.mako", grid=grid )

    @web.expose
    @web.require_login( "use Galaxy visualizations", use_panels=True )
    def list( self, trans, *args, **kwargs ):
        # Handle operation
        if 'operation' in kwargs and 'id' in kwargs:
            session = trans.sa_session
            operation = kwargs['operation'].lower()
            ids = util.listify( kwargs['id'] )
            for id in ids:
                item = session.query( model.Visualization ).get( trans.security.decode_id( id ) )
                if operation == "delete":
                    item.deleted = True
                if operation == "share or publish":
                    return self.sharing( trans, **kwargs )
            session.flush()
            
        # Build list of visualizations shared with user.
        shared_by_others = trans.sa_session \
            .query( model.VisualizationUserShareAssociation ) \
            .filter_by( user=trans.get_user() ) \
            .join( model.Visualization.table ) \
            .filter( model.Visualization.deleted == False ) \
            .order_by( desc( model.Visualization.update_time ) ) \
            .all()
        
        return trans.fill_template( "visualization/list.mako", grid=self._user_list_grid( trans, *args, **kwargs ), shared_by_others=shared_by_others )
    

    #
    # -- Functions for operating on visualizations. --
    #

    @web.expose
    @web.require_login( "use Galaxy visualizations", use_panels=True )
    def index( self, trans, *args, **kwargs ):
        """ Lists user's saved visualizations. """
        return self.list( trans, *args, **kwargs )
    
    @web.expose
    @web.require_login()
    def clone(self, trans, id, *args, **kwargs):
        visualization = self.get_visualization( trans, id, check_ownership=False )            
        user = trans.get_user()
        owner = ( visualization.user == user )
        new_title = "Copy of '%s'" % visualization.title
        if not owner:
            new_title += " shared by %s" % visualization.user.email
            
        cloned_visualization = visualization.copy( user=trans.user, title=new_title )
        
        # Persist
        session = trans.sa_session
        session.add( cloned_visualization )
        session.flush()
        
        # Display the management page
        trans.set_message( 'Copy created with name "%s"' % cloned_visualization.title )
        return self.list( trans )
            
    @web.expose
    @web.require_login( "modify Galaxy visualizations" )
    def set_slug_async( self, trans, id, new_slug ):
        """ Set item slug asynchronously. """
        visualization = self.get_visualization( trans, id )
        if visualization:
            visualization.slug = new_slug
            trans.sa_session.flush()
            return visualization.slug
            
    @web.expose
    @web.require_login( "use Galaxy visualizations" )
    def set_accessible_async( self, trans, id=None, accessible=False ):
        """ Set visualization's importable attribute and slug. """
        visualization = self.get_visualization( trans, id )

        # Only set if importable value would change; this prevents a change in the update_time unless attribute really changed.
        importable = accessible in ['True', 'true', 't', 'T'];
        if visualization and visualization.importable != importable:
            if importable:
                self._make_item_accessible( trans.sa_session, visualization )
            else:
                visualization.importable = importable
            trans.sa_session.flush()

        return
        
    @web.expose
    @web.require_login( "rate items" )
    @web.json
    def rate_async( self, trans, id, rating ):
        """ Rate a visualization asynchronously and return updated community data. """

        visualization = self.get_visualization( trans, id, check_ownership=False, check_accessible=True )
        if not visualization:
            return trans.show_error_message( "The specified visualization does not exist." )

        # Rate visualization.
        visualization_rating = self.rate_item( trans.sa_session, trans.get_user(), visualization, rating )

        return self.get_ave_item_rating_data( trans.sa_session, visualization )
        
    @web.expose
    @web.require_login( "share Galaxy visualizations" )
    def imp( self, trans, id ):
        """ Import a visualization into user's workspace. """
        # Set referer message.
        referer = trans.request.referer
        if referer is not "":
            referer_message = "<a href='%s'>return to the previous page</a>" % referer
        else:
            referer_message = "<a href='%s'>go to Galaxy's start page</a>" % url_for( '/' )
                    
        # Do import.
        session = trans.sa_session
        visualization = self.get_visualization( trans, id, check_ownership=False )
        if visualization.importable == False:
            return trans.show_error_message( "The owner of this visualization has disabled imports via this link.<br>You can %s" % referer_message, use_panels=True )
        elif visualization.deleted:
            return trans.show_error_message( "You can't import this visualization because it has been deleted.<br>You can %s" % referer_message, use_panels=True )
        else:
            # Create imported visualization via copy. 
            #   TODO: need to handle custom db keys.
            
            imported_visualization = visualization.copy( user=trans.user, title="imported: " + visualization.title )
            
            # Persist
            session = trans.sa_session
            session.add( imported_visualization )
            session.flush()
            
            # Redirect to load galaxy frames.
            return trans.show_ok_message(
                message="""Visualization "%s" has been imported. <br>You can <a href="%s">start using this visualization</a> or %s.""" 
                % ( visualization.title, web.url_for( controller='visualization' ), referer_message ), use_panels=True )
        

    @web.expose
    @web.require_login( "share Galaxy visualizations" )
    def sharing( self, trans, id, **kwargs ):
        """ Handle visualization sharing. """

        # Get session and visualization.
        session = trans.sa_session
        visualization = self.get_visualization( trans, id, check_ownership=True )

        # Do operation on visualization.
        if 'make_accessible_via_link' in kwargs:
            self._make_item_accessible( trans.sa_session, visualization )
        elif 'make_accessible_and_publish' in kwargs:
            self._make_item_accessible( trans.sa_session, visualization )
            visualization.published = True
        elif 'publish' in kwargs:
            visualization.published = True
        elif 'disable_link_access' in kwargs:
            visualization.importable = False
        elif 'unpublish' in kwargs:
            visualization.published = False
        elif 'disable_link_access_and_unpublish' in kwargs:
            visualization.importable = visualization.published = False
        elif 'unshare_user' in kwargs:
            user = session.query( model.User ).get( trans.security.decode_id( kwargs['unshare_user' ] ) )
            if not user:
                error( "User not found for provided id" )
            association = session.query( model.VisualizationUserShareAssociation ) \
                                 .filter_by( user=user, visualization=visualization ).one()
            session.delete( association )

        session.flush()

        return trans.fill_template( "/sharing_base.mako", item=visualization, use_panels=True )

    @web.expose
    @web.require_login( "share Galaxy visualizations" )
    def share( self, trans, id=None, email="", use_panels=False ):
        """ Handle sharing a visualization with a particular user. """
        msg = mtype = None
        visualization = self.get_visualization( trans, id, check_ownership=True )
        if email:
            other = trans.sa_session.query( model.User ) \
                                    .filter( and_( model.User.table.c.email==email,
                                                   model.User.table.c.deleted==False ) ) \
                                    .first()
            if not other:
                mtype = "error"
                msg = ( "User '%s' does not exist" % email )
            elif other == trans.get_user():
                mtype = "error"
                msg = ( "You cannot share a visualization with yourself" )
            elif trans.sa_session.query( model.VisualizationUserShareAssociation ) \
                    .filter_by( user=other, visualization=visualization ).count() > 0:
                mtype = "error"
                msg = ( "Visualization already shared with '%s'" % email )
            else:
                share = model.VisualizationUserShareAssociation()
                share.visualization = visualization
                share.user = other
                session = trans.sa_session
                session.add( share )
                self.create_item_slug( session, visualization )
                session.flush()
                trans.set_message( "Visualization '%s' shared with user '%s'" % ( visualization.title, other.email ) )
                return trans.response.send_redirect( url_for( action='sharing', id=id ) )
        return trans.fill_template( "/ind_share_base.mako",
                                    message = msg,
                                    messagetype = mtype,
                                    item=visualization,
                                    email=email,
                                    use_panels=use_panels )
        

    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """ Display visualization based on a username and slug. """

        # Get visualization.
        session = trans.sa_session
        user = session.query( model.User ).filter_by( username=username ).first()
        visualization = trans.sa_session.query( model.Visualization ).filter_by( user=user, slug=slug, deleted=False ).first()
        if visualization is None:
            raise web.httpexceptions.HTTPNotFound()
        
        # Security check raises error if user cannot access visualization.
        self.security_check( trans, visualization, False, True)
        
        # Get rating data.
        user_item_rating = 0
        if trans.get_user():
            user_item_rating = self.get_user_item_rating( trans.sa_session, trans.get_user(), visualization )
            if user_item_rating:
                user_item_rating = user_item_rating.rating
            else:
                user_item_rating = 0
        ave_item_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, visualization )
        
        # Display.
        visualization_config = self.get_visualization_config( trans, visualization )
        return trans.stream_template_mako( "visualization/display.mako", item = visualization, item_data = visualization_config, 
                                            user_item_rating = user_item_rating, ave_item_rating=ave_item_rating, num_ratings=num_ratings,
                                            content_only=True )
        
    @web.expose
    @web.json
    @web.require_login( "get item name and link" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns visualization's name and link. """
        visualization = self.get_visualization( trans, id, check_ownership=False, check_accessible=True )

        if self.create_item_slug( trans.sa_session, visualization ):
            trans.sa_session.flush()
        return_dict = { "name" : visualization.title, "link" : url_for( action="display_by_username_and_slug", username=visualization.user.username, slug=visualization.slug ) }
        return return_dict

    @web.expose
    def get_item_content_async( self, trans, id ):
        """ Returns item content in HTML format. """
        
        # Get visualization, making sure it's accessible.
        visualization = self.get_visualization( trans, id, check_ownership=False, check_accessible=True )
        if visualization is None:
            raise web.httpexceptions.HTTPNotFound()
        
        # Return content.
        visualization_config = self.get_visualization_config( trans, visualization )    
        return trans.fill_template_mako( "visualization/item_content.mako", encoded_id=trans.security.encode_id(visualization.id), 
                                            item=visualization, item_data=visualization_config, content_only=True )
        
    @web.expose
    @web.require_login( "create visualizations" )
    def create( self, trans, visualization_title="", visualization_slug="", visualization_annotation="", visualization_dbkey="",
                visualization_type="" ):
        """
        Creates a new visualization or returns a form for creating visualization.
        """
        visualization_title_err = visualization_slug_err = visualization_annotation_err = ""
        if trans.request.method == "POST":
            rval = self.create_visualization( trans, title=visualization_title, 
                                              slug=visualization_slug, 
                                              annotation=visualization_annotation,
                                              dbkey=visualization_dbkey,
                                              type=visualization_type )
            if isinstance( rval, dict ):
                # Found error creating viz.
                visualization_title_err = rval[ 'title_err' ]
                visualization_slug_err = rval[ 'slug_err' ]
            else:
                # Successfully created viz.
                return trans.response.send_redirect( web.url_for( action='list' ) )
        
        viz_type_options = [ ( t, t ) for t in self.viz_types ]
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Create new visualization", submit_text="Submit" )
                .add_text( "visualization_title", "Visualization title", value=visualization_title, error=visualization_title_err )
                .add_select( "visualization_type", "Type", options=viz_type_options, error=None )
                .add_text( "visualization_slug", "Visualization identifier", value=visualization_slug, error=visualization_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this visualization. A default is generated
                                from the visualization title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" )
                .add_select( "visualization_dbkey", "Visualization DbKey/Build", value=visualization_dbkey, options=trans.app.genomes.get_dbkeys_with_chrom_info( trans ), error=None)
                .add_text( "visualization_annotation", "Visualization annotation", value=visualization_annotation, error=visualization_annotation_err,
                            help="A description of the visualization; annotation is shown alongside published visualizations."),
                template="visualization/create.mako" )
                
    @web.json
    def save( self, trans, vis_json=None, type=None, id=None, title=None, dbkey=None, annotation=None ):
        """
        Save a visualization; if visualization does not have an ID, a new 
        visualization is created. Returns JSON of visualization.
        """

        # Get visualization attributes from kwargs or from config.
        vis_config = from_json_string( vis_json )
        vis_type = type or vis_config[ 'type' ]
        vis_id = id or vis_config.get( 'id', None )
        vis_title = title or vis_config.get( 'title', None )
        vis_dbkey = dbkey or vis_config.get( 'dbkey', None )
        vis_annotation = annotation or vis_config.get( 'annotation', None )
        return self.save_visualization( trans, vis_config, vis_type, vis_id, vis_title, vis_dbkey, vis_annotation )
        
    @web.expose
    @web.require_login( "edit visualizations" )
    def edit( self, trans, id, visualization_title="", visualization_slug="", visualization_annotation="" ):
        """
        Edit a visualization's attributes.
        """
        visualization = self.get_visualization( trans, id, check_ownership=True )
        session = trans.sa_session
        
        visualization_title_err = visualization_slug_err = visualization_annotation_err = ""
        if trans.request.method == "POST":
            if not visualization_title:
                visualization_title_err = "Visualization name is required"
            elif not visualization_slug:
                visualization_slug_err = "Visualization id is required"
            elif not VALID_SLUG_RE.match( visualization_slug ):
                visualization_slug_err = "Visualization identifier must consist of only lowercase letters, numbers, and the '-' character"
            elif visualization_slug != visualization.slug and trans.sa_session.query( model.Visualization ).filter_by( user=visualization.user, slug=visualization_slug, deleted=False ).first():
                visualization_slug_err = "Visualization id must be unique"
            else:
                visualization.title = visualization_title
                visualization.slug = visualization_slug
                if visualization_annotation != "":
                    visualization_annotation = sanitize_html( visualization_annotation, 'utf-8', 'text/html' )
                    self.add_item_annotation( trans.sa_session, trans.get_user(), visualization, visualization_annotation )
                session.flush()
                # Redirect to visualization list.
                return trans.response.send_redirect( web.url_for( action='list' ) )
        else:
            visualization_title = visualization.title
            # Create slug if it's not already set.
            if visualization.slug is None:
                self.create_item_slug( trans.sa_session, visualization )
            visualization_slug = visualization.slug
            visualization_annotation = self.get_item_annotation_str( trans.sa_session, trans.user, visualization )
            if not visualization_annotation:
                visualization_annotation = ""
        return trans.show_form( 
            web.FormBuilder( web.url_for( id=id ), "Edit visualization attributes", submit_text="Submit" )
                .add_text( "visualization_title", "Visualization title", value=visualization_title, error=visualization_title_err )
                .add_text( "visualization_slug", "Visualization identifier", value=visualization_slug, error=visualization_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this visualization. A default is generated
                                from the visualization title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" )
                .add_text( "visualization_annotation", "Visualization annotation", value=visualization_annotation, error=visualization_annotation_err,
                            help="A description of the visualization; annotation is shown alongside published visualizations."),
            template="visualization/create.mako" )

    #
    # Visualizations.
    #

    @web.expose
    @web.require_login()
    def new_browser( self, trans, **kwargs ):
        """
        Provide info necessary for creating a new trackster browser.
        """
        return trans.fill_template( "tracks/new_browser.mako", 
                                    dbkeys=trans.app.genomes.get_dbkeys_with_chrom_info( trans ), 
                                    default_dbkey=kwargs.get("default_dbkey", None) )
        
    @web.expose
    @web.require_login()
    def trackster(self, trans, id=None, **kwargs):
        """
        Display browser for the visualization denoted by id and add the datasets listed in `dataset_ids`.
        """

        # Display new browser if no id provided.
        if not id:
            return trans.fill_template( "tracks/browser.mako", config={}, 
                                        add_dataset=kwargs.get("dataset_id", None), 
                                        default_dbkey=kwargs.get("default_dbkey", None) )

        # Display saved visualization.
        vis = self.get_visualization( trans, id, check_ownership=False, check_accessible=True )
        viz_config = self.get_visualization_config( trans, vis )
        
        # Get new dataset if specified.
        new_dataset = kwargs.get("dataset_id", None)
        if new_dataset is not None:
            if trans.security.decode_id(new_dataset) in [ d["dataset_id"] for d in viz_config.get("tracks") ]:
                new_dataset = None # Already in browser, so don't add
        return trans.fill_template( 'tracks/browser.mako', config=viz_config, add_dataset=new_dataset )

    @web.json
    def save_trackster( self, trans, vis_json ):
        """
        Save a visualization; if visualization does not have an ID, a new 
        visualization is created. Returns JSON of visualization.
        """
        
        # TODO: Need from_dict to convert json to Visualization object.
        vis_config = from_json_string( vis_json )
        config = {
            'view': vis_config[ 'datasets' ],
            'bookmarks': vis_config[ 'bookmarks' ],
            'viewport': vis_config[ 'viewport' ]
        }
        type = vis_config[ 'type' ]
        id = vis_config.get( 'id', None )
        title = vis_config[ 'title' ]
        dbkey = vis_config[ 'dbkey' ]
        annotation = vis_config.get( 'annotation', None )
        return self.save_visualization( trans, config, type, id, title, dbkey, annotation )

    @web.expose
    def circster( self, trans, id, **kwargs ):
        """
        Display a circster visualization.
        """
        vis = self.get_visualization( trans, id, check_ownership=False, check_accessible=True )
        viz_config = self.get_visualization_config( trans, vis )

        # Get genome info.
        dbkey = viz_config[ 'dbkey' ]
        chroms_info = self.app.genomes.chroms( trans, dbkey=dbkey )
        genome = { 'dbkey': dbkey, 'chroms_info': chroms_info }

        # Add genome-wide summary tree data to each track in viz.
        tracks = viz_config[ 'tracks' ]
        for track in tracks:
            # Get dataset and indexed datatype.
            dataset = self.get_hda_or_ldda( trans, track[ 'hda_ldda'], track[ 'dataset_id' ] )
            data_sources = self._get_datasources( trans, dataset )
            data_provider_registry = trans.app.data_provider_registry
            if 'data_standalone' in data_sources:
                indexed_type = data_sources['data_standalone']['name']
                data_provider = data_provider_registry.get_data_provider( indexed_type )( dataset )
            else:
                indexed_type = data_sources['index']['name']
                # Get converted dataset and append track's genome data.
                converted_dataset = dataset.get_converted_dataset( trans, indexed_type )
                data_provider = data_provider_registry.get_data_provider( indexed_type )( converted_dataset, dataset )
            # HACK: pass in additional params, which are only used for summary tree data, not BBI data.
            track[ 'genome_wide_data' ] = { 'data': data_provider.get_genome_data( chroms_info, level=4, detail_cutoff=0, draw_cutoff=0 ) }
        
        return trans.fill_template( 'visualization/circster.mako', viz_config=viz_config, genome=genome )

    @web.expose
    def sweepster( self, trans, id=None, hda_ldda=None, dataset_id=None, regions=None ):
        """
        Displays a sweepster visualization using the incoming parameters. If id is available,
        get the visualization with the given id; otherwise, create a new visualization using
        a given dataset and regions.
        """
        # Need to create history if necessary in order to create tool form.
        trans.get_history( create=True )

        if id:
            # Loading a shared visualization.
            viz = self.get_visualization( trans, id )
            viz_config = self.get_visualization_config( trans, viz )
            dataset = self.get_dataset( trans, viz_config[ 'dataset_id' ] )
        else:
            # Loading new visualization.
            dataset = self.get_hda_or_ldda( trans, hda_ldda, dataset_id )
            job = get_dataset_job( dataset )
            viz_config = {
                'dataset_id': dataset_id,
                'tool_id': job.tool_id,
                'regions': from_json_string( regions )
            }
                
        # Add tool, dataset attributes to config based on id.
        tool = trans.app.toolbox.get_tool( viz_config[ 'tool_id' ] )
        viz_config[ 'tool' ] = tool.to_dict( trans, for_display=True )
        viz_config[ 'dataset' ] = dataset.get_api_value()

        return trans.fill_template_mako( "visualization/sweepster.mako", config=viz_config )
    
    def get_item( self, trans, id ):
        return self.get_visualization( trans, id )

    @web.expose    
    def scatterplot( self, trans, dataset_id, cols ):
        # Get HDA.
        hda = self.get_dataset( trans, dataset_id, check_ownership=False, check_accessible=True )
        
        # get some metadata for the page
        hda_dict = hda.get_api_value()
        #title = "Scatter plot of {name}:".format( **hda_dict )
        #subtitle = "{misc_info}".format( **hda_dict )
        
        #TODO: add column data
        # Read data.
        data_provider = ColumnDataProvider( original_dataset=hda )
        data = data_provider.get_data( cols )
        
        # Return plot.
        return trans.fill_template_mako( "visualization/scatterplot.mako",
                                         title=hda.name, subtitle=hda.info,
                                         hda=hda,
                                         data=data )
        

    @web.json
    def bookmarks_from_dataset( self, trans, hda_id=None, ldda_id=None ):
        if hda_id:
            hda_ldda = "hda"
            dataset_id = hda_id
        elif ldda_id:
            hda_ldda = "ldda"
            dataset_id = ldda_id
        dataset = self.get_hda_or_ldda( trans, hda_ldda, dataset_id )
        
        rows = []
        if isinstance( dataset.datatype, Bed ):
            data = RawBedDataProvider( original_dataset=dataset ).get_iterator()
            for i, line in enumerate( data ):
                if ( i > 500 ): break
                fields = line.split()
                location = name = "%s:%s-%s" % ( fields[0], fields[1], fields[2] )
                if len( fields ) > 3:
                    name = fields[4]
                rows.append( [location, name] )
        return { 'data': rows }
    
