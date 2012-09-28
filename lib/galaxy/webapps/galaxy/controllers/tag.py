"""
Tags Controller: handles tagging/untagging of entities and provides autocomplete support.
"""
import logging
from galaxy.web.base.controller import *
from sqlalchemy.sql.expression import func, and_
from sqlalchemy.sql import select

log = logging.getLogger( __name__ )

class TagsController ( BaseUIController ):
    def __init__( self, app ):
        BaseUIController.__init__( self, app )
        self.tag_handler = app.tag_handler
    @web.expose
    @web.require_login( "edit item tags" )
    def get_tagging_elt_async( self, trans, item_id, item_class, elt_context="" ):
        """ Returns HTML for editing an item's tags. """
        item = self._get_item( trans, item_class, trans.security.decode_id( item_id ) )
        if not item:
            return trans.show_error_message( "No item of class %s with id %s " % ( item_class, item_id ) )
        return trans.fill_template( "/tagging_common.mako",
                                    tag_type="individual",
                                    user=trans.user,
                                    tagged_item=item,
                                    elt_context=elt_context,
                                    in_form=False,
                                    input_size="22",
                                    tag_click_fn="default_tag_click_fn",
                                    use_toggle_link=False )
    @web.expose
    @web.require_login( "add tag to an item" )
    def add_tag_async( self, trans, item_id=None, item_class=None, new_tag=None, context=None ):
        """ Add tag to an item. """   
        # Apply tag.
        item = self._get_item( trans, item_class, trans.security.decode_id( item_id ) )
        user = trans.user
        self.tag_handler.apply_item_tags( trans, user, item, new_tag.encode( 'utf-8' ) )
        trans.sa_session.flush()
        # Log.
        params = dict( item_id=item.id, item_class=item_class, tag=new_tag )
        trans.log_action( user, unicode( "tag" ), context, params )
    @web.expose
    @web.require_login( "remove tag from an item" )
    def remove_tag_async( self, trans, item_id=None, item_class=None, tag_name=None, context=None ):
        """ Remove tag from an item. """
        # Remove tag.
        item = self._get_item( trans, item_class, trans.security.decode_id( item_id ) )
        user = trans.user
        self.tag_handler.remove_item_tag( trans, user, item, tag_name.encode( 'utf-8' ) )
        trans.sa_session.flush()
        # Log.
        params = dict( item_id=item.id, item_class=item_class, tag=tag_name )
        trans.log_action( user, unicode( "untag" ), context, params )
    # Retag an item. All previous tags are deleted and new tags are applied.
    #@web.expose
    @web.require_login( "Apply a new set of tags to an item; previous tags are deleted." )
    def retag_async( self, trans, item_id=None, item_class=None, new_tags=None ):
        """ Apply a new set of tags to an item; previous tags are deleted. """
        # Apply tags.  
        item = self._get_item( trans, item_class, trans.security.decode_id( item_id ) )
        user = trans.user
        self.tag_handler.delete_item_tags( trans, item )
        self.tag_handler.apply_item_tags( trans, user, item, new_tags.encode( 'utf-8' ) )
        trans.sa_session.flush()    
    @web.expose
    @web.require_login( "get autocomplete data for an item's tags" )
    def tag_autocomplete_data( self, trans, q=None, limit=None, timestamp=None, item_id=None, item_class=None ):
        """ Get autocomplete data for an item's tags. """
        # Get item, do security check, and get autocomplete data.
        item = None
        if item_id is not None:
            item = self._get_item( trans, item_class, trans.security.decode_id( item_id ) )
        user = trans.user
        item_class = self.get_class( item_class )
        q = q.encode( 'utf-8' )
        if q.find( ":" ) == -1:
            return self._get_tag_autocomplete_names( trans, q, limit, timestamp, user, item, item_class )
        else:
            return self._get_tag_autocomplete_values( trans, q, limit, timestamp, user, item, item_class )
    def _get_tag_autocomplete_names( self, trans, q, limit, timestamp, user=None, item=None, item_class=None ):
        """
        Returns autocomplete data for tag names ordered from most frequently used to
        least frequently used.
        """
        # Get user's item tags and usage counts.
        # Get item's class object and item-tag association class.
        if item is None and item_class is None:
            raise RuntimeError( "Both item and item_class cannot be None" )
        elif item is not None:
            item_class = item.__class__
        item_tag_assoc_class = self.tag_handler.get_tag_assoc_class( item_class )
        # Build select statement.
        cols_to_select = [ item_tag_assoc_class.table.c.tag_id, func.count( '*' ) ] 
        from_obj = item_tag_assoc_class.table.join( item_class.table ).join( trans.app.model.Tag.table )
        where_clause = and_( trans.app.model.Tag.table.c.name.like( q + "%" ),
                             item_tag_assoc_class.table.c.user_id == user.id )
        order_by = [ func.count( "*" ).desc() ]
        group_by = item_tag_assoc_class.table.c.tag_id
        # Do query and get result set.
        query = select( columns=cols_to_select,
                        from_obj=from_obj,
                        whereclause=where_clause,
                        group_by=group_by,
                        order_by=order_by,
                        limit=limit )
        result_set = trans.sa_session.execute( query )
        # Create and return autocomplete data.
        ac_data = "#Header|Your Tags\n"
        for row in result_set:
            tag = self.tag_handler.get_tag_by_id( trans, row[0] )
            # Exclude tags that are already applied to the item.    
            if ( item is not None ) and ( self.tag_handler.item_has_tag( trans, trans.user, item, tag ) ):
                continue
            # Add tag to autocomplete data. Use the most frequent name that user
            # has employed for the tag.
            tag_names = self._get_usernames_for_tag( trans, trans.user, tag, item_class, item_tag_assoc_class )
            ac_data += tag_names[0] + "|" + tag_names[0] + "\n"
        return ac_data
    def _get_tag_autocomplete_values( self, trans, q, limit, timestamp, user=None, item=None, item_class=None ):
        """
        Returns autocomplete data for tag values ordered from most frequently used to
        least frequently used.
        """
        tag_name_and_value = q.split( ":" )
        tag_name = tag_name_and_value[0]
        tag_value = tag_name_and_value[1]
        tag = self.tag_handler.get_tag_by_name( trans, tag_name )
        # Don't autocomplete if tag doesn't exist.
        if tag is None:
            return ""
        # Get item's class object and item-tag association class.
        if item is None and item_class is None:
            raise RuntimeError( "Both item and item_class cannot be None" )
        elif item is not None:
            item_class = item.__class__
        item_tag_assoc_class = self.tag_handler.get_tag_assoc_class( item_class )
        # Build select statement.
        cols_to_select = [ item_tag_assoc_class.table.c.value, func.count( '*' ) ] 
        from_obj = item_tag_assoc_class.table.join( item_class.table ).join( trans.app.model.Tag.table )
        where_clause = and_( item_tag_assoc_class.table.c.user_id == user.id,
                             trans.app.model.Tag.table.c.id == tag.id,
                             item_tag_assoc_class.table.c.value.like( tag_value + "%" ) )
        order_by = [ func.count("*").desc(), item_tag_assoc_class.table.c.value ]
        group_by = item_tag_assoc_class.table.c.value
        # Do query and get result set.
        query = select( columns=cols_to_select,
                        from_obj=from_obj,
                        whereclause=where_clause,
                        group_by=group_by,
                        order_by=order_by,
                        limit=limit )
        result_set = trans.sa_session.execute( query )
        # Create and return autocomplete data.
        ac_data = "#Header|Your Values for '%s'\n" % ( tag_name )
        tag_uname = self._get_usernames_for_tag( trans, trans.user, tag, item_class, item_tag_assoc_class )[0]
        for row in result_set:
            ac_data += tag_uname + ":" + row[0] + "|" + row[0] + "\n"
        return ac_data
    def _get_usernames_for_tag( self, trans, user, tag, item_class, item_tag_assoc_class ):
        """
        Returns an ordered list of the user names for a tag; list is ordered from
        most popular to least popular name.
        """
        # Build select stmt.
        cols_to_select = [ item_tag_assoc_class.table.c.user_tname, func.count( '*' ) ]
        where_clause = and_( item_tag_assoc_class.table.c.user_id == user.id,
                             item_tag_assoc_class.table.c.tag_id == tag.id )
        group_by = item_tag_assoc_class.table.c.user_tname
        order_by = [ func.count( "*" ).desc() ]
        # Do query and get result set.
        query = select( columns=cols_to_select,
                        whereclause=where_clause,
                        group_by=group_by,
                        order_by=order_by )
        result_set = trans.sa_session.execute( query )
        user_tag_names = list()
        for row in result_set:
            user_tag_names.append( row[0] )
        return user_tag_names
    def _get_item( self, trans, item_class_name, id ):
        """ Get an item based on type and id. """
        item_class = self.tag_handler.item_tag_assoc_info[item_class_name].item_class
        item = trans.sa_session.query( item_class ).filter( "id=" + str( id ) )[0]
        return item
