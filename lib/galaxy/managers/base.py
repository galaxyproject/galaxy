"""
Keeps the older BaseController security and fetching methods and also
defines a base ModelManager, ModelSerializer, and ModelDeserializer.

ModelManagers are used for operations on models that occur outside the scope of
a single model object, such as:
    - object creation
    - object lookup
    - interactions between 2+ objects of different model classes

(Since these were to replace model Mixins from
web/framework/base/controller.py the rule of thumb used there also generally
has been applied here: if it uses the trans or sa_session, put it in a manager
and not the model.)

ModelSerializers allow flexible conversion of model objects to dictionaries.
They control what keys are sent, how values are simplified, can remap keys,
and allow both predefined and user controlled key sets.

ModelDeserializers control how a model validates and process an incoming
attribute change to a model object.
"""
#TODO: it may be there's a better way to combine the above three classes
#   such as: a single flat class, serializers being singletons in the manager, etc.
#   instead of the three separate classes. With no 'apparent' perfect scheme
#   I'm opting to just keep them separate.

import re

import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy

from galaxy import model
from galaxy import exceptions
from galaxy.model import tool_shed_install
from galaxy.util import sanitize_html


import logging
log = logging.getLogger( __name__ )


# =============================================================================
def security_check( trans, item, check_ownership=False, check_accessible=False ):
    """
    Security checks for an item: checks if (a) user owns item or (b) item
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


def get_class( class_name ):
    """
    Returns the class object that a string denotes. Without this method, we'd have
    to do eval(<class_name>).
    """
    if class_name == 'History':
        item_class = model.History
    elif class_name == 'HistoryDatasetAssociation':
        item_class = model.HistoryDatasetAssociation
    elif class_name == 'Page':
        item_class = model.Page
    elif class_name == 'StoredWorkflow':
        item_class = model.StoredWorkflow
    elif class_name == 'Visualization':
        item_class = model.Visualization
    elif class_name == 'Tool':
        item_class = model.Tool
    elif class_name == 'Job':
        item_class = model.Job
    elif class_name == 'User':
        item_class = model.User
    elif class_name == 'Group':
        item_class = model.Group
    elif class_name == 'Role':
        item_class = model.Role
    elif class_name == 'Quota':
        item_class = model.Quota
    elif class_name == 'Library':
        item_class = model.Library
    elif class_name == 'LibraryFolder':
        item_class = model.LibraryFolder
    elif class_name == 'LibraryDatasetDatasetAssociation':
        item_class = model.LibraryDatasetDatasetAssociation
    elif class_name == 'LibraryDataset':
        item_class = model.LibraryDataset
    elif class_name == 'ToolShedRepository':
        item_class = tool_shed_install.ToolShedRepository
    else:
        item_class = None
    return item_class


def get_object( trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None ):
    """
    Convenience method to get a model object with the specified checks. This is
    a generic method for dealing with objects uniformly from the older
    controller mixin code - however whenever possible the managers for a
    particular model should be used to load objects.
    """
    try:
        decoded_id = trans.security.decode_id( id )
    except:
        raise exceptions.MessageException( "Malformed %s id ( %s ) specified, unable to decode"
                                           % ( class_name, str( id ) ), type='error' )
    try:
        item_class = get_class( class_name )
        assert item_class is not None
        item = trans.sa_session.query( item_class ).get( decoded_id )
        assert item is not None
    except Exception:
        log.exception( "Invalid %s id ( %s ) specified." % ( class_name, id ) )
        raise exceptions.MessageException( "Invalid %s id ( %s ) specified" % ( class_name, id ), type="error" )

    if check_ownership or check_accessible:
        security_check( trans, item, check_ownership, check_accessible )
    if deleted is True and not item.deleted:
        raise exceptions.ItemDeletionException( '%s "%s" is not deleted'
                                                % ( class_name, getattr( item, 'name', id ) ), type="warning" )
    elif deleted is False and item.deleted:
        raise exceptions.ItemDeletionException( '%s "%s" is deleted'
                                                % ( class_name, getattr( item, 'name', id ) ), type="warning" )
    return item


# =============================================================================
class ModelManager( object ):
    """
    Base class for all model/resource managers.

    Provides common queries and CRUD operations as a (hopefully) light layer
    over the ORM.
    """
    model_class = object
    foreign_key_name = None

    def __init__( self, app ):
        self.app = app

    def _default_order_by( self ):
        """
        Returns a tuple of columns for the default order when getting multiple models.
        """
        return ( self.model_class.create_time, )

    #NOTE: at this layer, all ids are expected to be decoded and in int form
    # ------------------------------------------------------------------------- get/read/query
    def query( self, trans, eagerloads=True, filters=None, order_by=None, limit=None, offset=None, **kwargs ):
        """
        Return a basic query from model_class, filters, order_by, and limit and offset.

        Set eagerloads to False to disable them for this query.
        """
        #print 'query:', eagerloads, filters, order_by, limit, offset, kwargs
        query = trans.sa_session.query( self.model_class )

        # joined table loading
        if eagerloads is False:
            query = query.enable_eagerloads( False )

        #TODO: if non-orm filters are the only option, here is where they'd go
        query = self._apply_filters( query, filters )
        query = self._apply_order_by_limit_offset( query, order_by, limit, offset )
        return query

    def _apply_filters( self, query, filters ):
        """
        Add any filters to the given query.
        """
        if filters is None:
            return query

        if not isinstance( filters, list ):
            filters = [ filters ]
        #note: implicit AND
        for filter in filters:
            query = query.filter( filter )
        return query

    def _munge_filters( self, filtersA, filtersB ):
        """
        Combine two lists into a single list.

        (While allowing them to be None, non-lists, or lists.)
        """
        #TODO: there's nothing specifically filter or model-related here - move to util
        if filtersA is None:
            return filtersB
        if filtersB is None:
            return filtersA
        if not isinstance( filtersA, list ):
            filtersA = [ filtersA ]
        if not isinstance( filtersB, list ):
            filtersB = [ filtersB ]
        return filtersA + filtersB

    def _apply_order_by_limit_offset( self, query, order_by, limit, offset ):
        """
        Return the query after adding the order_by, limit, and offset clauses.
        """
        query = self._apply_order_by( query, order_by )
        return self._apply_limit_offset( query, limit, offset )

    def _apply_order_by( self, query, order_by ):
        """
        Return the query after adding the order_by clauses.

        Use the manager's default_order_by if order_by is None.
        """
        if order_by is None:
            return query.order_by( *self._default_order_by() )

        if isinstance( order_by, ( list, tuple ) ):
            return query.order_by( *order_by )
        return query.order_by( order_by )

    def _apply_limit_offset( self, query, limit, offset ):
        """
        Return the query after applying the given limit and offset (if not None).
        """
        if limit is not None:
            query = query.limit( limit )
        if offset is not None:
            query = query.offset( offset )
        return query

    # ......................................................................... common queries
    def one( self, trans, **kwargs ):
        """
        Sends kwargs to build the query and returns one and only one model.
        """
        query = self.query( trans, **kwargs )
        return self._one_with_recast_errors( query )

    def _one_with_recast_errors( self, query ):
        """
        Call sqlalchemy's one and recast errors to serializable errors if any.

        :raises exceptions.ObjectNotFound: if no model is found
        :raises exceptions.InconsistentDatabase: if more than one model is found
        """
        # overridden to raise serializable errors
        try:
            return query.one()
        except sqlalchemy.orm.exc.NoResultFound, not_found:
            raise exceptions.ObjectNotFound( self.model_class.__name__ + ' not found' )
        except sqlalchemy.orm.exc.MultipleResultsFound, multi_found:
            raise exceptions.InconsistentDatabase( 'found more than one ' + self.model_class.__name__ )

    def _one_or_none( self, query ):
        """
        Return the object if found, None if it's not.

        :raises exceptions.InconsistentDatabase: if more than one model is found
        """
        try:
            return self._one_with_recast_errors( query )
        except exceptions.ObjectNotFound, not_found:
            return None

    #TODO: get?

    def by_id( self, trans, id, **kwargs ):
        """
        Gets a model by primary id.
        """
        id_filter = self.model_class.id == id
        return self.one( trans, filters=id_filter, **kwargs )

    def list( self, trans, query=None, **kwargs ):
        """
        Sends kwargs to build the query return all models found.
        """
        query = query or self.query( trans, **kwargs )
        return query.all()

    def _query_by_ids( self, trans, ids, filters=None, **kwargs ):
        """
        Builds a query to find a list of models with the given list of `ids`.
        """
        ids_filter = self.model_class.id.in_( ids )
        return self.query( trans, filters=self._munge_filters( ids_filter, filters ), **kwargs )

    def by_ids( self, trans, ids, **kwargs ):
        """
        Returns an in-order list of models with the matching ids in `ids`.
        """
        found = self._query_by_ids( trans, ids, **kwargs ).all()
        #TODO: this does not order by the original 'ids' array

        # ...could use get (supposedly since found are in the session, the db won't be hit twice)
        #return map( trans.sa_session.query( self.model_class ).get, ids )

        # ...could implement own version here - slow?
        return self._order_items_by_id( ids, found )
        #return found

    def _order_items_by_id( self, ids, items ):
        """
        Given a list of (unique) ids and a list of items having an 'id' attribute,
        return items that have the given ids in that order.

        If an id in ids is not found or if an item in items doesn't have a given
        id, they will not be in the returned list.
        """
        ID_ATTR_NAME = 'id'
        #TODO:?? aside from sqlalx.get mentioned above, I haven't seen an in-SQL way
        #   to make this happen. This may not be the most efficient way either.
        #NOTE: that this isn't sorting by id - this is matching the order in items to the order in ids
        # move items list into dict by id
        item_dict = {}
        for item in items:
            item_id = getattr( item, ID_ATTR_NAME, None )
            if item_id:
                item_dict[ item_id ] = item
        # pull from map in order of ids
        in_order = []
        for id in ids:
            if id in item_dict:
                in_order.append( item_dict[ id ] )
        return in_order

    # ------------------------------------------------------------------------- create
    def create( self, trans, flush=True, *args, **kwargs ):
        """
        Generically create a new model.
        """
        # override in subclasses
        item = self.model_class( *args, **kwargs )
        trans.sa_session.add( item )
        if flush:
            trans.sa_session.flush()
        return item

    def copy( self, trans, item, **kwargs ):
        """
        Clone or copy an item.
        """
        raise exceptions.NotImplemented( 'Abstract method' )

    # ------------------------------------------------------------------------- update
    def update( self, trans, item, new_values, flush=True, **kwargs ):
        """
        Given a dictionary of new values, update `item` and return it.

        ..note: NO validation or deserialization occurs here.
        """
        trans.sa_session.add( item )
        for key, value in new_values.items():
            if hasattr( item, key ):
                setattr( item, key, value )
        if flush:
            trans.sa_session.flush()
        return item

    #TODO: yagni?
    def associate( self, trans, associate_with, item, foreign_key_name=None ):
        """
        Generically associate `item` with `associate_with` based on `foreign_key_name`.
        """
        foreign_key_name = foreign_key_name or self.foreign_key_name
        setattr( associate_with, foreign_key_name, item )
        return item

    def query_associated( self, trans, associated_model_class, item, foreign_key_name=None ):
        """
        Generically query other items that have been associated with this `item`.
        """
        foreign_key_name = foreign_key_name or self.foreign_key_name
        foreign_key = getattr( associated_model_class, foreign_key_name )
        return trans.sa_session.query( associated_model_class ).filter( foreign_key == item )

    # ------------------------------------------------------------------------- delete
    # a rename of sql DELETE to differentiate from the Galaxy notion of mark_as_deleted
    #def destroy( self, trans, item, **kwargs ):
    #    return item


# ============================================================================= SERIALIZERS/to_dict,from_dict
class ModelSerializingError( exceptions.InternalServerError ):
    """Thrown when request model values can't be serialized"""
    pass


class ModelDeserializingError( exceptions.ObjectAttributeInvalidException ):
    """Thrown when an incoming value isn't usable by the model
    (bad type, out of range, etc.)
    """
    pass


# -----------------------------------------------------------------------------
class ModelSerializer( object ):
    """
    Turns models into JSONable dicts.

    Maintains a map of requestable keys and the Callable() serializer functions
    that should be called for those keys.
    E.g. { 'x' : lambda trans, item, key: item.x, ... }

    To serialize call:
        my_serializer = MySerializer( app )
        ...
        keys_to_serialize = [ 'id', 'name', 'attr1', 'attr2', ... ]
        item_dict = MySerializer.serialize( trans, my_item, keys_to_serialize )
        # if a key to serialize is not listed in the Serializer.serializable_keys or serializers, it will not be added
    """

    def __init__( self, app ):
        """
        Set up serializer map, any additional serializable keys, and views here.
        """
        self.app = app

        # a map of dictionary keys to the functions (often lambdas) that create the values for those keys
        self.serializers = {}
        # a list of valid serializable keys that can use the default (string) serializer
        #   this allows us to: 'mention' the key without adding the default serializer
        #NOTE: if a key is requested that is in neither serializable_keys or serializers, it is not returned
        self.serializable_keys = []
        # add subclass serializers defined there
        self.add_serializers()

        # views are collections of serializable attributes (a named array of keys)
        #   inspired by model.dict_{view}_visible_keys
        self.views = {}
        self.default_view = None

    # ......................................................................... serializing
    def add_serializers( self ):
        """
        Register a map of attribute keys -> serializing functions that will serialize
        the attribute.
        """
        # to be overridden in subclasses
        pass

    def serialize( self, trans, item, keys ):
        """
        Serialize the model `item` to a dictionary.

        Given model `item` and the list `keys`, create and return a dictionary
        built from each key in `keys` that also exists in `serializers` and
        values of calling the keyed/named serializers on item.
        """
        # main interface fn for converting a model to a dict
        returned = {}
        for key in keys:
            # check both serializers and serializable keys
            if key in self.serializers:
                returned[ key ] = self.serializers[ key ]( trans, item, key )
            elif key in self.serializable_keys:
                returned[ key ] = self.default_serializer( trans, item, key )
            # ignore bad/unreg keys
        return returned

    def default_serializer( self, trans, item, key ):
        """
        Serialize the `item`'s attribute named `key`.
        """
        #TODO:?? point of change but not really necessary?
        return getattr( item, key )

    # ......................................................................... serializers for common galaxy objects
    def serialize_date( self, trans, item, key ):
        """
        Serialize a date attribute of `item`.
        """
        date = getattr( item, key )
        return date.isoformat() if date is not None else None

    def serialize_id( self, trans, item, key ):
        """
        Serialize an id attribute of `item`.
        """
        id = getattr( item, key )
        return self.app.security.encode_id( id ) if id is not None else None

    # ......................................................................... serializing to a view
    # where a view is a predefied list of keys to serialize
    def serialize_to_view( self, trans, item, view=None, keys=None, default_view=None ):
        """
        Use a predefined list of keys (the string `view`) and any additional keys
        listed in `keys`.

        The combinations can be:
            `view` only: return those keys listed in the named view
            `keys` only: return those keys listed
            no `view` or `keys`: use the `default_view` if any
            `view` and `keys`: combine both into one list of keys
        """
        all_keys = []
        keys = keys or []
        # chose explicit over concise here
        if view:
            if keys:
                all_keys = self._view_to_keys( view ) + keys
            else:
                all_keys = self._view_to_keys( view )
        else:
            if keys:
                all_keys = keys
            elif default_view:
                all_keys = self._view_to_keys( default_view )

        return self.serialize( trans, item, all_keys )

    def _view_to_keys( self, view=None ):
        """
        Converts a known view into a list of keys.

        :raises ModelSerializingError: if the view is not listed in `self.views`.
        """
        if view is None:
            view = self.default_view
        if view not in self.views:
            raise ModelSerializingError( 'unknown view', view=view, available_views=self.views )
        return self.views[ view ][:]


# -----------------------------------------------------------------------------
class ModelDeserializer( object ):
    """
    An object that converts an incoming serialized dict into values that can be
    directly assigned to an item's attributes and assigns them.
    """
    #: the class used to create this deserializer's generically accessible model_manager
    model_manager_class = None

    def __init__( self, app ):
        """
        Set up deserializers and validator.
        """
        self.app = app

        self.deserializers = {}
        self.deserializable_keys = []
        self.add_deserializers()
        # a sub object that can validate incoming values
        self.validate = ModelValidator( self.app )

        # create a generically accessible manager for the model this deserializer works with/for
        self.manager = None
        if self.model_manager_class:
           self.manager = self.model_manager_class( self.app )

    def add_deserializers( self ):
        """
        Register a map of attribute keys -> functions that will deserialize data
        into attributes to be assigned to the item.
        """
        # to be overridden in subclasses
        pass

    def deserialize( self, trans, item, data, flush=True ):
        """
        Convert an incoming serialized dict into values that can be
        directly assigned to an item's attributes and assign them
        """
        sa_session = self.app.model.context
        new_dict = {}
        for key, val in data.items():
            if key in self.deserializers:
                new_dict[ key ] = self.deserializers[ key ]( trans, item, key, val )
            #!important: don't error on unreg. keys -- many clients will add weird ass keys onto the model

        #TODO:?? add and flush here or in manager?
        if flush and len( new_dict ):
            sa_session.add( item )
            sa_session.flush()

        return new_dict

    # ... common deserializers for primitives
    def default_deserializer( self, trans, item, key, val ):
        """
        If the incoming `val` is different than the `item` value change it
        and, in either case, return the value.
        """
        #TODO: sets the item attribute to value (this may not work in all instances)

        # only do the following if val == getattr( item, key )
        if hasattr( item, key ) and getattr( item, key ) != val:
            setattr( item, key, val )
        return val

    def deserialize_basestring( self, trans, item, key, val ):
        val = self.validate.basestring( key, val )
        return self.default_deserializer( trans, item, key, val )

    def deserialize_bool( self, trans, item, key, val ):
        val = self.validate.bool( key, val )
        return self.default_deserializer( trans, item, key, val )

    def deserialize_int( self, trans, item, key, val, min=None, max=None ):
        val = self.validate.int_range( key, val, min, max )
        return self.default_deserializer( trans, item, key, val )

    # ... common deserializers for Galaxy
    def deserialize_genome_build( self, trans, item, key, val ):
        """
        Make sure `val` is a valid dbkey and assign it.
        """
        val = self.validate.genome_build( trans, key, val )
        return self.default_deserializer( trans, item, key, val )


# -----------------------------------------------------------------------------
#TODO:?? a larger question is: which should be first? Deserialize then validate - or - validate then deserialize?
class ModelValidator( object ):
    """
    An object that inspects a dictionary (generally meant to be a set of
    new/updated values for the model) and raises an error if a value is
    not acceptable.
    """

    def __init__( self, app, *args, **kwargs ):
        self.app = app

    def type( self, key, val, types ):
        """
        Check `val` against the type (or tuple of types) in `types`.

        :raises exceptions.RequestParameterInvalidException: if not an instance.
        """
        if not isinstance( val, types ):
            msg = 'must be a type: %s' % ( str( types ) )
            raise exceptions.RequestParameterInvalidException( msg, key=key, val=val )
        return val

    # validators for primitives and compounds of primitives
    def basestring( self, key, val ):
        return self.type( key, val, basestring )

    def bool( self, key, val ):
        return self.type( key, val, bool )

    def int( self, key, val ):
        return self.type( key, val, int )

    def nullable_basestring( self, key, val ):
        """
        Must be a basestring or None.
        """
        return self.type( key, val, ( basestring, type( None ) ) )

    def int_range( self, key, val, min=None, max=None ):
        """
        Must be a int between min and max.
        """
        val = self.type( key, val, int )
        if min is not None and val < min:
            raise exceptions.RequestParameterInvalidException( "less than minimum", key=key, val=val, min=min )
        if max is not None and val > max:
            raise exceptions.RequestParameterInvalidException( "greater than maximum", key=key, val=val, max=max )
        return val

    def basestring_list( self, key, val ):
        """
        Must be a list of basestrings.
        """
        #TODO: Here's where compound types start becoming a nightmare. Any more or more complex
        #   and should find a different way.
        val = self.type( key, val, list )
        return [ self.basestring( key, elem ) for elem in val ]

    # validators for Galaxy
    def genome_build( self, trans, key, val ):
        """
        Must be a valid genome_build/dbkey/reference/whatever-the-hell-were-calling-them-now.
        """
        #TODO: is this correct?
        if val is None:
            return '?'
        for genome_build_shortname, longname in self.app.genome_builds.get_genome_build_names( trans=trans ):
            if val == genome_build_shortname:
                return val
        raise exceptions.RequestParameterInvalidException( "invalid reference", key=key, val=val )

    #def slug( self, trans, item, key, val ):
    #    """validate slug"""
    #    pass


# =============================================================================
# Mixins (here for now)
# =============================================================================
class AccessibleModelInterface( object ):
    """
    A security interface to check if a User can read/view an item's.

    This can also be thought of as 'read but not modify' privileges.
    """

    # don't want to override by_id since consumers will also want to fetch w/o any security checks
    def is_accessible( self, trans, item, user ):
        """
        Return True if the item accessible to user.
        """
        # override in subclasses
        raise exceptions.NotImplemented( "Abstract Interface Method" )

    def get_accessible( self, trans, id, user, **kwargs ):
        """
        Return the item with the given id if it's accessible to user,
        otherwise raise an error.

        :raises exceptions.ItemAccessibilityException:
        """
        item = ModelManager.by_id( self, trans, id )
        return self.error_unless_accessible( trans, item, user )

    def error_unless_accessible( self, trans, item, user ):
        """
        Raise an error if the item is NOT accessible to user, otherwise return the item.

        :raises exceptions.ItemAccessibilityException:
        """
        if self.is_accessible( trans, item, user ):
            return item
        raise exceptions.ItemAccessibilityException( "%s is not accessible by user" % ( self.model_class.__name__ ) )

    #TODO:?? are these even useful?
    def list_accessible( self, trans, user, **kwargs ):
        """
        Return a list of items accessible to the user, raising an error if ANY
        are inaccessible.

        :raises exceptions.ItemAccessibilityException:
        """
        raise exceptions.NotImplemented( "Abstract Interface Method" )
        #NOTE: this will be a large, inefficient list if filters are not passed in kwargs
        #items = ModelManager.list( self, trans, **kwargs )
        #return [ self.error_unless_accessible( trans, item, user ) for item in items ]

    def filter_accessible( self, trans, user, **kwargs ):
        """
        Return a list of items accessible to the user.
        """
        raise exceptions.NotImplemented( "Abstract Interface Method" )
        #NOTE: this will be a large, inefficient list if filters are not  passed in kwargs
        #items = ModelManager.list( self, trans, **kwargs )
        #return filter( lambda item: self.is_accessible( trans, item, user ), items )


# =============================================================================
class OwnableModelInterface( object ):
    """
    A security interface to check if a User is an item's owner.

    Some resources are associated with the User that created or imported them
    and these Users can be considered the models' owner.

    This can also be thought of as write/edit privileges.
    """

    def is_owner( self, trans, item, user ):
        """
        Return True if user owns the item.
        """
        # override in subclasses
        raise exceptions.NotImplemented( "Abstract Interface Method" )

    def get_owned( self, trans, id, user, **kwargs ):
        """
        Return the item with the given id if owned by the user,
        otherwise raise an error.

        :raises exceptions.ItemOwnershipException:
        """
        item = ModelManager.by_id( self, trans, id )
        return self.error_unless_owner( trans, item, user )

    def error_unless_owner( self, trans, item, user ):
        """
        Raise an error if the item is NOT owned by user, otherwise return the item.

        :raises exceptions.ItemAccessibilityException:
        """
        if self.is_owner( trans, item, user ):
            return item
        raise exceptions.ItemOwnershipException( "%s is not owned by user" % ( self.model_class.__name__ ) )

    def list_owned( self, trans, user, **kwargs ):
        """
        Return a list of items owned by the user, raising an error if ANY
        are not.

        :raises exceptions.ItemAccessibilityException:
        """
        # just alias to by_user (easier/same thing)
        return self.by_user( trans, user, **kwargs )

    def filter_owned( self, trans, user, **kwargs ):
        """
        Return a list of items owned by the user.
        """
        # just alias to list_owned
        return self.list_owned( trans, user, **kwargs )


# -----------------------------------------------------------------------------
class DeletableModelInterface( object ):
    """
    A mixin/interface for a model that is deletable (i.e. has a 'deleted' attr).

    Many resources in Galaxy can be marked as deleted - meaning (in most cases)
    that they are no longer needed, should not be displayed, or may be actually
    removed by an admin/script.
    """

    def delete( self, trans, item, flush=True, **kwargs ):
        """
        Mark as deleted and return.
        """
        trans.sa_session.add( item )
        item.deleted = True
        if flush:
            trans.sa_session.flush()
        return item

    def undelete( self, trans, item, flush=True, **kwargs ):
        """
        Mark as not deleted and return.
        """
        trans.sa_session.add( item )
        item.deleted = False
        if flush:
            trans.sa_session.flush()
        return item


class DeletableModelSerializer( object ):

    def add_serializers( self ):
        pass


#TODO: these are of questionable value if we don't want to enable users to delete/purge via update
class DeletableModelDeserializer( object ):

    def add_deserializers( self ):
        self.deserializers[ 'deleted' ] = self.deserialize_deleted

    def deserialize_deleted( self, trans, item, key, val ):
        """
        Delete or undelete `item` based on `val` then return `item.deleted`.
        """
        new_deleted = self.validate.bool( key, val )
        if new_deleted == item.deleted:
            return item.deleted
        #TODO:?? flush=False?
        if new_deleted:
            self.manager.delete( trans, item, flush=False )
        else:
            self.manager.undelete( trans, item, flush=False )
        return item.deleted


# -----------------------------------------------------------------------------
class PurgableModelInterface( DeletableModelInterface ):
    """
    A manager interface/mixin for a resource that allows deleting and purging where
    purging is often removal of some additional, non-db resource (e.g. a dataset's
    file).
    """

    def purge( self, trans, item, flush=True, **kwargs ):
        """
        Mark as purged and return.

        Override this in subclasses to do the additional resource removal.
        """
        trans.sa_session.add( item )
        item.purged = True
        if flush:
            trans.sa_session.flush()
        return item


class PurgableModelSerializer( DeletableModelSerializer ):

    def add_serializers( self ):
        DeletableModelSerializer.add_serializers( self )


class PurgableModelDeserializer( DeletableModelDeserializer ):

    def add_deserializers( self ):
        DeletableModelDeserializer.add_deserializers( self )
        self.deserializers[ 'purged' ] = self.deserialize_purged

    def deserialize_purged( self, trans, item, key, val ):
        """
        If `val` is True, purge `item` and return `item.purged`.
        """
        new_purged = self.validate.bool( key, val )
        if new_purged == item.purged:
            return item.purged
        if new_purged:
            self.manager.purge( trans, item, flush=False )
        return self.purged
