from sqlalchemy.sql.expression import func
import logging

log = logging.getLogger( __name__ )

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