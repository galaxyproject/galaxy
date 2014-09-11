from galaxy import exceptions


class ModelManager( object ):
    pass


class ModelSerializer( object ):
    pass


def security_check( trans, item, check_ownership=False, check_accessible=False ):
    """ Security checks for an item: checks if (a) user owns item or (b) item
    is accessible to user. This is a generic method for dealing with objects
    uniformly from the older controller mixin code - however whenever possible
    the managers for a particular model should be used to perform security
    checks.
    """

    # all items are accessible to an admin
    if trans.user_is_admin():
        return item

    # Verify ownership: there is a current user and that user is the same as the item's
    if check_ownership:
        if not trans.user:
            raise exceptions.ItemOwnershipException( "Must be logged in to manage Galaxy items", type='error' )
        if item.user != trans.user:
            raise exceptions.ItemOwnershipException( "%s is not owned by the current user" % item.__class__.__name__, type='error' )

    # Verify accessible:
    #   if it's part of a lib - can they access via security
    #   if it's something else (sharable) have they been added to the item's users_shared_with_dot_users
    if check_accessible:
        if type( item ) in ( trans.app.model.LibraryFolder, trans.app.model.LibraryDatasetDatasetAssociation, trans.app.model.LibraryDataset ):
            if not trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), item, trans.user ):
                raise exceptions.ItemAccessibilityException( "%s is not accessible to the current user" % item.__class__.__name__, type='error' )
        else:
            if ( item.user != trans.user ) and ( not item.importable ) and ( trans.user not in item.users_shared_with_dot_users ):
                raise exceptions.ItemAccessibilityException( "%s is not accessible to the current user" % item.__class__.__name__, type='error' )
    return item
