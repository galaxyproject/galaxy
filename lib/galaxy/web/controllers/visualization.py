from galaxy import model
from galaxy.model.item_attrs import *
from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, grids, iff
from galaxy.util.sanitize_html import sanitize_html


class VisualizationListGrid( grids.Grid ):
    # Grid definition
    title = "Saved Visualizations"
    model_class = model.Visualization
    default_sort_key = "-update_time"
    default_filter = dict( title="All", deleted="False", tags="All", sharing="All" )
    columns = [
        grids.TextColumn( "Title", key="title", attach_popup=True,
                         link=( lambda item: dict( controller="tracks", action="browser", id=item.id ) ) ),
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
        grids.GridOperation( "View/Edit", allow_multiple=False, url_args=dict( controller='tracks', action='browser' ) ),
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


class VisualizationController( BaseUIController, Sharable, UsesAnnotations, 
                                UsesHistoryDatasetAssociation, UsesVisualization, 
                                UsesItemRatings ):
    _user_list_grid = VisualizationListGrid()
    _published_list_grid = VisualizationAllPublishedGrid()
    
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
    def create( self, trans, visualization_title="", visualization_slug="", visualization_annotation="", visualization_dbkey="" ):
        """
        Create a new visualization
        """
        user = trans.get_user()
        visualization_title_err = visualization_slug_err = visualization_annotation_err = ""
        if trans.request.method == "POST":
            if not visualization_title:
                visualization_title_err = "visualization name is required"
            elif not visualization_slug:
                visualization_slug_err = "visualization id is required"
            elif not VALID_SLUG_RE.match( visualization_slug ):
                visualization_slug_err = "visualization identifier must consist of only lowercase letters, numbers, and the '-' character"
            elif trans.sa_session.query( model.Visualization ).filter_by( user=user, slug=visualization_slug, deleted=False ).first():
                visualization_slug_err = "visualization id must be unique"
            else:
                # Create the new stored visualization
                visualization = model.Visualization()
                visualization.title = visualization_title
                visualization.slug = visualization_slug
                visualization.dbkey = visualization_dbkey
                visualization.type = 'trackster' # HACK: set visualization type to trackster since it's the only viz
                visualization_annotation = sanitize_html( visualization_annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans.sa_session, trans.get_user(), visualization, visualization_annotation )
                visualization.user = user
                
                # And the first (empty) visualization revision
                visualization_revision = model.VisualizationRevision()
                visualization_revision.title = visualization_title
                visualization_revision.config = {}
                visualization_revision.dbkey = visualization_dbkey
                visualization_revision.visualization = visualization
                visualization.latest_revision = visualization_revision

                # Persist
                session = trans.sa_session
                session.add(visualization)
                session.add(visualization_revision)
                session.flush()

                return trans.response.send_redirect( web.url_for( action='list' ) )
                                
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Create new visualization", submit_text="Submit" )
                .add_text( "visualization_title", "Visualization title", value=visualization_title, error=visualization_title_err )
                .add_text( "visualization_slug", "Visualization identifier", value=visualization_slug, error=visualization_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this visualization. A default is generated
                                from the visualization title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" )
                .add_select( "visualization_dbkey", "Visualization DbKey/Build", value=visualization_dbkey, options=self._get_dbkeys( trans ), error=None)
                .add_text( "visualization_annotation", "Visualization annotation", value=visualization_annotation, error=visualization_annotation_err,
                            help="A description of the visualization; annotation is shown alongside published visualizations."),
                template="visualization/create.mako" )
        
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

    def get_item( self, trans, id ):
        return self.get_visualization( trans, id )
    
