

class TagsManager( object ):
    """ Manages CRUD operations related to tagging objects.
    """

    def __init__( self, app ):
        self.app = app
        self.tag_handler = app.tag_handler

    def set_tags_from_list( self, trans, item, new_tags_list, user=None ):
        #precondition: item is already security checked against user
        #precondition: incoming tags is a list of sanitized/formatted strings
        user = user or trans.user

        self.tag_handler.delete_item_tags( trans, user, item )
        new_tags_str = ','.join( new_tags_list )
        self.tag_handler.apply_item_tags( trans, user, item, unicode( new_tags_str.encode( 'utf-8' ), 'utf-8' ) )
        trans.sa_session.flush()
        return item.tags
