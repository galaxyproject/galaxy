from sqlalchemy.sql.expression import func
from sqlalchemy.orm.collections import InstrumentedList
# Cannot import galaxy.model b/c it creates a circular import graph.
import galaxy
import logging
log = logging.getLogger( __name__ )

class RuntimeException( Exception ):
    pass     

class UsesItemRatings:
    """ 
        Mixin for getting and setting item ratings.
        
        Class makes two assumptions:
        (1) item-rating association table is named <item_class>RatingAssocation
        (2) item-rating association table has a column with a foreign key referencing 
        item table that contains the item's id.
    """      
    def get_ave_item_rating_data( self, db_session, item, webapp_model=None ):
        """ Returns the average rating for an item."""
        if webapp_model is None:
            webapp_model = galaxy.model
        item_rating_assoc_class = self._get_item_rating_assoc_class( item, webapp_model=webapp_model )
        if not item_rating_assoc_class:
            raise RuntimeException( "Item does not have ratings: %s" % item.__class__.__name__ )
        item_id_filter = self._get_item_id_filter_str( item, item_rating_assoc_class )
        ave_rating = db_session.query( func.avg( item_rating_assoc_class.rating ) ).filter( item_id_filter ).scalar()
        # Convert ave_rating to float; note: if there are no item ratings, ave rating is None.
        if ave_rating:
            ave_rating = float( ave_rating )
        else:
            ave_rating = 0
        num_ratings = int( db_session.query( func.count( item_rating_assoc_class.rating ) ).filter( item_id_filter ).scalar() )
        return ( ave_rating, num_ratings )
    
    def rate_item( self, db_session, user, item, rating, webapp_model=None ):
        """ Rate an item. Return type is <item_class>RatingAssociation. """
        if webapp_model is None:
            webapp_model = galaxy.model
        item_rating = self.get_user_item_rating( db_session, user, item, webapp_model=webapp_model )
        if not item_rating:
            # User has not yet rated item; create rating.
            item_rating_assoc_class = self._get_item_rating_assoc_class( item, webapp_model=webapp_model )
            item_rating = item_rating_assoc_class()
            item_rating.user = user
            item_rating.set_item( item )
            item_rating.rating = rating
            db_session.add( item_rating )
            db_session.flush()
        elif item_rating.rating != rating:
            # User has rated item; update rating.
            item_rating.rating = rating
            db_session.flush()
        return item_rating
        
    def get_user_item_rating( self, db_session, user, item, webapp_model=None ):
        """ Returns user's rating for an item. Return type is <item_class>RatingAssociation. """
        if webapp_model is None:
            webapp_model = galaxy.model
        item_rating_assoc_class = self._get_item_rating_assoc_class( item, webapp_model=webapp_model )
        if not item_rating_assoc_class:
            raise RuntimeException( "Item does not have ratings: %s" % item.__class__.__name__ )
        
        # Query rating table by user and item id. 
        item_id_filter = self._get_item_id_filter_str( item, item_rating_assoc_class )
        return db_session.query( item_rating_assoc_class ).filter_by( user=user ).filter( item_id_filter ).first()
        
    def _get_item_rating_assoc_class( self, item, webapp_model=None ):
        """ Returns an item's item-rating association class. """
        if webapp_model is None:
            webapp_model = galaxy.model
        item_rating_assoc_class = '%sRatingAssociation' % item.__class__.__name__
        return getattr( webapp_model, item_rating_assoc_class, None )

    def _get_item_id_filter_str( self, item, item_rating_assoc_class, webapp_model=None ):
        # Get foreign key in item-rating association table that references item table.
        if webapp_model is None:
            webapp_model = galaxy.model
        item_fk = None
        for fk in item_rating_assoc_class.table.foreign_keys:
            if fk.references( item.table ):
                item_fk = fk
                break
                
        if not item_fk:
            raise RuntimeException( "Cannot find item id column in item-rating association table: %s, %s" % item_rating_assoc_class.__name__, item_rating_assoc_class.table.name )
            
        # TODO: can we provide a better filter than a raw string?
        return "%s=%i" % ( item_fk.parent.name, item.id )

class UsesAnnotations:
    """ Mixin for getting and setting item annotations. """
    def get_item_annotation_str( self, db_session, user, item ):
        """ Returns a user's annotation string for an item. """
        annotation_obj = self.get_item_annotation_obj( db_session, user, item )
        if annotation_obj:
            return annotation_obj.annotation
        return None
        
    def get_item_annotation_obj( self, db_session, user, item ):
        """ Returns a user's annotation object for an item. """
        # Get annotation association class.
        annotation_assoc_class = self._get_annotation_assoc_class( item )
        if not annotation_assoc_class:
            return None
        
        # Get annotation association object.
        annotation_assoc = db_session.query( annotation_assoc_class ).filter_by( user=user )
        
        # TODO: use filtering like that in _get_item_id_filter_str()
        if item.__class__ == galaxy.model.History:
            annotation_assoc = annotation_assoc.filter_by( history=item )
        elif item.__class__ == galaxy.model.HistoryDatasetAssociation:
            annotation_assoc = annotation_assoc.filter_by( hda=item )
        elif item.__class__ == galaxy.model.StoredWorkflow:
            annotation_assoc = annotation_assoc.filter_by( stored_workflow=item )
        elif item.__class__ == galaxy.model.WorkflowStep:
            annotation_assoc = annotation_assoc.filter_by( workflow_step=item )
        elif item.__class__ == galaxy.model.Page:
            annotation_assoc = annotation_assoc.filter_by( page=item )
        elif item.__class__ == galaxy.model.Visualization:
            annotation_assoc = annotation_assoc.filter_by( visualization=item )
        return annotation_assoc.first()
        
    def add_item_annotation( self, db_session, user, item, annotation ):
        """ Add or update an item's annotation; a user can only have a single annotation for an item. """
        # Get/create annotation association object.
        annotation_assoc = self.get_item_annotation_obj( db_session, user, item )
        if not annotation_assoc:
            annotation_assoc_class = self._get_annotation_assoc_class( item )
            if not annotation_assoc_class:
                return None
            annotation_assoc = annotation_assoc_class()
            item.annotations.append( annotation_assoc )
            annotation_assoc.user = user
        # Set annotation.
        annotation_assoc.annotation = annotation
        return annotation_assoc
        
    def copy_item_annotation( self, db_session, source_user, source_item, target_user, target_item ):
        """ Copy an annotation from a user/item source to a user/item target. """
        if source_user and target_user:
            annotation_str = self.get_item_annotation_str( db_session, source_user, source_item )
            if annotation_str:
                annotation = self.add_item_annotation( db_session, target_user, target_item, annotation_str )
                return annotation
        return None
        
    def _get_annotation_assoc_class( self, item ):
        """ Returns an item's item-annotation association class. """
        class_name = '%sAnnotationAssociation' % item.__class__.__name__
        return getattr( galaxy.model, class_name, None )

class APIItem:
    """ Mixin for api representation. """
    #api_collection_visible_keys = ( 'id' )
    #api_element_visible_keys = ( 'id' )
    def get_api_value( self, view='collection', value_mapper = None ):
        def get_value( key, item ):
            try:
                return item.get_api_value( view=view, value_mapper=value_mapper )
            except:
                if key in value_mapper:
                    return value_mapper.get( key )( item )
                return item
        if value_mapper is None:
            value_mapper = {}
        rval = {}
        try:
            visible_keys = self.__getattribute__( 'api_' + view + '_visible_keys' )
        except AttributeError:
            raise Exception( 'Unknown API view: %s' % view )
        for key in visible_keys:
            try:
                item = self.__getattribute__( key )
                if type( item ) == InstrumentedList:
                    rval[key] = []
                    for i in item:
                        rval[key].append( get_value( key, i ) )
                else:
                    rval[key] = get_value( key, item )
            except AttributeError:
                rval[key] = None
        return rval
