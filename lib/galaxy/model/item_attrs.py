from sqlalchemy.sql.expression import func

class UsesItemRatings:
    """ 
        Mixin for getting and setting item ratings.
        
        Class makes two assumptions:
        (1) item-rating association table is named <item_class>RatingAssocation
        and is in trans.model;
        (2) item-rating association table has a column with a foreign key referencing 
        item table that contains the item's id.
    """
                    
    def get_ave_item_rating_data( self, trans, item):
        """ Returns the average rating for an item."""
        item_rating_assoc_class = self._get_item_rating_assoc_class( trans, item )
        if not item_rating_assoc_class:
            raise RuntimeException( "Item does not have ratings: %s" % item.__class__.__name__ )
        item_id_filter = self._get_item_id_filter_str( trans, item, item_rating_assoc_class )
        ave_rating = trans.sa_session.query( func.avg( item_rating_assoc_class.rating ) ).filter( item_id_filter ).scalar()
        # Convert ave_rating to float; note: if there are no item ratings, ave rating is None.
        if ave_rating:
            ave_rating = float( ave_rating )
        else:
            ave_rating = 0
        num_ratings = int( trans.sa_session.query( func.count( item_rating_assoc_class.rating ) ).filter( item_id_filter ).scalar() )
        return ( ave_rating, num_ratings )
    
    def rate_item( self, trans, user, item, rating ):
        """ Rate an item. Return type is <item_class>RatingAssociation. """
        item_rating = self.get_user_item_rating( trans, user, item )
        if not item_rating:
            # User has not yet rated item; create rating.
            item_rating_assoc_class = self._get_item_rating_assoc_class( trans, item )
            item_rating = item_rating_assoc_class()
            item_rating.user = trans.get_user()
            item_rating.set_item( item )
            item_rating.rating = rating
            trans.sa_session.add( item_rating )
            trans.sa_session.flush()
        elif item_rating.rating != rating:
            # User has rated item; update rating.
            item_rating.rating = rating
            trans.sa_session.flush()
        return item_rating
        
    def get_user_item_rating( self, trans, user, item ):
        """ Returns user's rating for an item. Return type is <item_class>RatingAssociation. """
        item_rating_assoc_class = self._get_item_rating_assoc_class( trans, item )
        if not item_rating_assoc_class:
            raise RuntimeException( "Item does not have ratings: %s" % item.__class__.__name__ )
        
        # Query rating table by user and item id. 
        item_id_filter = self._get_item_id_filter_str( trans, item, item_rating_assoc_class )
        return trans.sa_session.query( item_rating_assoc_class ).filter_by( user=user ).filter( item_id_filter ).first()
        
    def _get_item_rating_assoc_class( self, trans, item ):
        """ Returns an item's item-rating association class. """
        item_rating_assoc_class = '%sRatingAssociation' % item.__class__.__name__
        return trans.model.get( item_rating_assoc_class, None )
        
    def _get_item_id_filter_str( self, trans, item, item_rating_assoc_class ):
        # Get foreign key in item-rating association table that references item table.
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
    def get_item_annotation_str( self, trans, user, item ):
        """ Returns a user's annotation string for an item. """
        annotation_obj = self.get_item_annotation_obj( trans, user, item )
        if annotation_obj:
            return annotation_obj.annotation
        return None
    def get_item_annotation_obj( self, trans, user, item ):
        """ Returns a user's annotation object for an item. """
        # Get annotation association class.
        annotation_assoc_class = self._get_annotation_assoc_class( trans, item )
        if not annotation_assoc_class:
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
        
    def _get_annotation_assoc_class( self, trans, item ):
        """ Returns an item's item-annotation association class. """
        class_name = '%sAnnotationAssociation' % item.__class__.__name__
        return trans.model.get( class_name, None )
