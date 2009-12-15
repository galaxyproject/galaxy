"""
Tags Controller: handles tagging/untagging of entities and provides autocomplete support.
"""

from galaxy.model import History, HistoryTagAssociation, Dataset, DatasetTagAssociation, \
    HistoryDatasetAssociation, HistoryDatasetAssociationTagAssociation, Page, PageTagAssociation
from galaxy.web.base.controller import *
from galaxy.tags.tag_handler import *
from sqlalchemy.sql.expression import func, and_
from sqlalchemy.sql import select

class TagsController ( BaseController ):

    def __init__(self, app):
        BaseController.__init__(self, app)

        # Set up tag handler to recognize the following items: History, HistoryDatasetAssociation, Page, ...
        self.tag_handler = TagHandler()

    @web.expose
    @web.require_login( "Add tag to an item." )
    def add_tag_async( self, trans, id=None, item_class=None, new_tag=None, context=None ):
        """ Add tag to an item. """
        
        # Check that user owns item.
        item = self._get_item(trans, item_class, trans.security.decode_id( id ) )
        self._do_security_check( trans, item )
        
        # Apply tag.
        self.tag_handler.apply_item_tags( trans.sa_session, item, new_tag.encode('utf-8') )
        trans.sa_session.flush()
        
        # Log.
        params = dict( item_id=item.id, item_class=item_class, tag=new_tag)
        trans.log_action( unicode( "tag"), context, params )
        
    @web.expose
    @web.require_login( "Remove tag from an item." )
    def remove_tag_async( self, trans, id=None, item_class=None, tag_name=None, context=None ):
        """ Remove tag from an item. """
        
        # Check that user owns item.
        item = self._get_item(trans, item_class, trans.security.decode_id(id))
        self._do_security_check(trans, item)
        
        # Remove tag.
        self.tag_handler.remove_item_tag( trans, item, tag_name.encode('utf-8') )
        trans.sa_session.flush()
        
        # Log.
        params = dict( item_id=item.id, item_class=item_class, tag=tag_name)
        trans.log_action( unicode( "untag"), context, params )
        
    # Retag an item. All previous tags are deleted and new tags are applied.
    @web.expose
    @web.require_login( "Apply a new set of tags to an item; previous tags are deleted." )
    def retag_async( self, trans, id=None, item_class=None, new_tags=None ):
        """ Apply a new set of tags to an item; previous tags are deleted. """  
        item = self._get_item(trans, item_class, trans.security.decode_id(id))
        
        self._do_security_check(trans, item)
        
        tag_handler.delete_item_tags( trans, item )
        self.tag_handler.apply_item_tags( trans.sa_session, item, new_tags.encode('utf-8') )
        trans.sa_session.flush()
                
    @web.expose
    @web.require_login( "get autocomplete data for an item's tags" )
    def tag_autocomplete_data( self, trans, q=None, limit=None, timestamp=None, id=None, item_class=None ):
        """ Get autocomplete data for an item's tags. """

        #
        # Get item, do security check, and get autocomplete data.
        #
        item = None
        if id is not None:
            item = self._get_item(trans, item_class, trans.security.decode_id(id))
            self._do_security_check(trans, item)
            
        # Get item class. TODO: we should have a mapper that goes from class_name to class object.
        if item_class == 'History':
            item_class = History
        elif item_class == 'HistoryDatasetAssociation':
            item_class = HistoryDatasetAssociation
        elif item_class == 'Page':
            item_class = Page
        
        q = q.encode('utf-8')
        if q.find(":") == -1:
            return self._get_tag_autocomplete_names(trans, q, limit, timestamp, item, item_class)
        else:
            return self._get_tag_autocomplete_values(trans, q, limit, timestamp, item, item_class)
    
    def _get_tag_autocomplete_names( self, trans, q, limit, timestamp, item=None, item_class=None ):
        """Returns autocomplete data for tag names ordered from most frequently used to
            least frequently used."""
        #    
        # Get user's item tags and usage counts.
        #
        
        # Get item's class object and item-tag association class.
        if item is None and item_class is None:
            raise RuntimeError("Both item and item_class cannot be None")
        elif item is not None:
            item_class = item.__class__
        
        item_tag_assoc_class = self.tag_handler.get_tag_assoc_class(item_class)
        
        # Build select statement.
        cols_to_select = [ item_tag_assoc_class.table.c.tag_id, func.count('*') ] 
        from_obj = item_tag_assoc_class.table.join(item_class.table).join(Tag.table)
        where_clause = and_(self._get_column_for_filtering_item_by_user_id(item_class)==trans.get_user().id,
                            Tag.table.c.name.like(q + "%"))
        order_by = [ func.count("*").desc() ]
        group_by = item_tag_assoc_class.table.c.tag_id
        
        # Do query and get result set.
        query = select(columns=cols_to_select, from_obj=from_obj,
                       whereclause=where_clause, group_by=group_by, order_by=order_by, limit=limit)
        result_set = trans.sa_session.execute(query)
        
        # Create and return autocomplete data.
        ac_data = "#Header|Your Tags\n"
        for row in result_set:
            tag = self.tag_handler.get_tag_by_id(trans.sa_session, row[0])
                
            # Exclude tags that are already applied to the item.    
            if ( item is not None ) and ( self.tag_handler.item_has_tag(item, tag) ):
                continue
            # Add tag to autocomplete data. Use the most frequent name that user
            # has employed for the tag.
            tag_names = self._get_usernames_for_tag(trans.sa_session, trans.get_user(),
                                                    tag, item_class, item_tag_assoc_class)
            ac_data += tag_names[0] + "|" + tag_names[0] + "\n"
        
        return ac_data
        
    def _get_tag_autocomplete_values(self, trans, q, limit, timestamp, item=None, item_class=None):
        """Returns autocomplete data for tag values ordered from most frequently used to
            least frequently used."""
            
        tag_name_and_value = q.split(":")
        tag_name = tag_name_and_value[0]
        tag_value = tag_name_and_value[1]
        tag = self.tag_handler.get_tag_by_name(trans.sa_session, tag_name)
        # Don't autocomplete if tag doesn't exist.
        if tag is None:
            return ""
                
        # Get item's class object and item-tag association class.
        if item is None and item_class is None:
            raise RuntimeError("Both item and item_class cannot be None")
        elif item is not None:
            item_class = item.__class__

        item_tag_assoc_class = self.tag_handler.get_tag_assoc_class(item_class)
        
        # Build select statement.
        cols_to_select = [ item_tag_assoc_class.table.c.value, func.count('*') ] 
        from_obj = item_tag_assoc_class.table.join(item_class.table).join(Tag.table)
        where_clause = and_(self._get_column_for_filtering_item_by_user_id(item_class)==trans.get_user().id,
                            Tag.table.c.id==tag.id,
                            item_tag_assoc_class.table.c.value.like(tag_value + "%"))
        order_by = [ func.count("*").desc(),  item_tag_assoc_class.table.c.value ]
        group_by = item_tag_assoc_class.table.c.value
        
        # Do query and get result set.
        query = select(columns=cols_to_select, from_obj=from_obj,
                       whereclause=where_clause, group_by=group_by, order_by=order_by, limit=limit)
        result_set = trans.sa_session.execute(query)
        
        # Create and return autocomplete data.
        ac_data = "#Header|Your Values for '%s'\n" % (tag_name)
        tag_uname = self._get_usernames_for_tag(trans.sa_session, trans.get_user(), tag, item_class, item_tag_assoc_class)[0]
        for row in result_set:
            ac_data += tag_uname + ":" + row[0] + "|" + row[0] + "\n"
        return ac_data
    
    def _get_usernames_for_tag(self, db_session, user, tag, item_class, item_tag_assoc_class):
        """ Returns an ordered list of the user names for a tag; list is ordered from
            most popular to least popular name."""
        
        # Build select stmt.
        cols_to_select = [ item_tag_assoc_class.table.c.user_tname, func.count('*') ]
        where_clause = and_(self._get_column_for_filtering_item_by_user_id(item_class)==user.id ,
                            item_tag_assoc_class.table.c.tag_id==tag.id)
        group_by = item_tag_assoc_class.table.c.user_tname
        order_by = [ func.count("*").desc() ]
        
        # Do query and get result set.
        query = select(columns=cols_to_select, whereclause=where_clause,
                       group_by=group_by, order_by=order_by)
        result_set = db_session.execute(query)
        
        user_tag_names = list()
        for row in result_set:
            user_tag_names.append(row[0])
            
        return user_tag_names
    
    def _get_column_for_filtering_item_by_user_id(self, item_class): 
        """ Returns the column to use when filtering by user id. """
        if item_class is HistoryDatasetAssociation:
            # Use the user_id associated with the HDA's history.
            return History.table.c.user_id
        else:
            # Generically, just use the user_id column of the tagged item's table.
            return item_class.table.c.user_id
    
    def _get_item(self, trans, item_class_name, id):
        """ Get an item based on type and id. """
        item_class = self.tag_handler.item_tag_assoc_info[item_class_name].item_class
        item = trans.sa_session.query(item_class).filter("id=" + str(id))[0]
        return item;
        
    def _do_security_check(self, trans, item):
        """ Do security check on an item. """
        if isinstance(item, History):
            history = item;
            # Check that the history exists, and is either owned by the current
            # user (if logged in) or the current history
            assert history is not None
            if history.user is None:
                assert history == trans.get_history()
            else:
                assert history.user == trans.user
        elif isinstance(item, HistoryDatasetAssociation):
            # TODO.
            pass
        elif isinstance(item, Page):
            # TODO.
            pass
