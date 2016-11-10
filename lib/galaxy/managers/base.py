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
# TODO: it may be there's a better way to combine the above three classes
#   such as: a single flat class, serializers being singletons in the manager, etc.
#   instead of the three separate classes. With no 'apparent' perfect scheme
#   I'm opting to just keep them separate.
import datetime
import logging
import re

import routes
import sqlalchemy
from six import string_types

from galaxy import exceptions
from galaxy import model
from galaxy.model import tool_shed_install

log = logging.getLogger( __name__ )


# ==== accessors from base/controller.py
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


def decode_id(app, id):
    try:
        # note: use str - occasionally a fully numeric id will be placed in post body and parsed as int via JSON
        #   resulting in error for valid id
        return app.security.decode_id( str( id ) )
    except ( ValueError, TypeError ):
        msg = "Malformed id ( %s ) specified, unable to decode" % ( str( id ) )
        raise exceptions.MalformedId( msg, id=str( id ) )


def get_object( trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None ):
    """
    Convenience method to get a model object with the specified checks. This is
    a generic method for dealing with objects uniformly from the older
    controller mixin code - however whenever possible the managers for a
    particular model should be used to load objects.
    """
    decoded_id = decode_id(trans.app, id)
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
def munge_lists( listA, listB ):
    """
    Combine two lists into a single list.

    (While allowing them to be None, non-lists, or lists.)
    """
    # TODO: there's nothing specifically filter or model-related here - move to util
    if listA is None:
        return listB
    if listB is None:
        return listA
    if not isinstance( listA, list ):
        listA = [ listA ]
    if not isinstance( listB, list ):
        listB = [ listB ]
    return listA + listB


# -----------------------------------------------------------------------------
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

    def session( self ):
        return self.app.model.context

    def _session_setattr( self, item, attr, val, fn=None, flush=True ):
        if fn:
            fn( item, attr, val )
        else:
            setattr( item, attr, val )

        self.session().add( item )
        if flush:
            self.session().flush()
        return item

    # .... query foundation wrapper
    def query( self, eagerloads=True, **kwargs ):
        """
        Return a basic query from model_class, filters, order_by, and limit and offset.

        Set eagerloads to False to disable them for this query.
        """
        query = self.session().query( self.model_class )
        # joined table loading
        if eagerloads is False:
            query = query.enable_eagerloads( False )
        return self._filter_and_order_query( query, **kwargs )

    def _filter_and_order_query( self, query, filters=None, order_by=None, limit=None, offset=None, **kwargs ):
        # TODO: not a lot of functional cohesion here
        query = self._apply_orm_filters( query, filters )
        query = self._apply_order_by( query, order_by )
        query = self._apply_orm_limit_offset( query, limit, offset )
        return query

    # .... filters
    def _apply_orm_filters( self, query, filters ):
        """
        Add any filters to the given query.
        """
        if filters is None:
            return query

        if not isinstance( filters, list ):
            filters = [ filters ]
        # note: implicit AND
        for filter in filters:
            query = query.filter( filter )
        return query

    def _munge_filters( self, filtersA, filtersB ):
        """
        Combine two lists into a single list.

        (While allowing them to be None, non-lists, or lists.)
        """
        return munge_lists( filtersA, filtersB )

    # .... order, limit, and offset
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

    def _default_order_by( self ):
        """
        Returns a tuple of columns for the default order when getting multiple models.
        """
        return ( self.model_class.create_time, )

    def _apply_orm_limit_offset( self, query, limit, offset ):
        """
        Return the query after applying the given limit and offset (if not None).
        """
        if limit is not None:
            query = query.limit( limit )
        if offset is not None:
            query = query.offset( offset )
        return query

    # .... query resolution
    def one( self, **kwargs ):
        """
        Sends kwargs to build the query and returns one and only one model.
        """
        query = self.query( **kwargs )
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
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.ObjectNotFound( self.model_class.__name__ + ' not found' )
        except sqlalchemy.orm.exc.MultipleResultsFound:
            raise exceptions.InconsistentDatabase( 'found more than one ' + self.model_class.__name__ )

    def _one_or_none( self, query ):
        """
        Return the object if found, None if it's not.

        :raises exceptions.InconsistentDatabase: if more than one model is found
        """
        try:
            return self._one_with_recast_errors( query )
        except exceptions.ObjectNotFound:
            return None

    # NOTE: at this layer, all ids are expected to be decoded and in int form
    def by_id( self, id, **kwargs ):
        """
        Gets a model by primary id.
        """
        id_filter = self.model_class.id == id
        return self.one( filters=id_filter, **kwargs )

    # .... multirow queries
    def list( self, filters=None, order_by=None, limit=None, offset=None, **kwargs ):
        """
        Returns all objects matching the given filters
        """
        # list becomes a way of applying both filters generated in the orm (such as .user ==)
        # and functional filters that aren't currently possible using the orm (such as instance calcluated values
        # or annotations/tags). List splits those two filters and applies limits/offsets
        # only after functional filters (if any) using python.
        orm_filters, fn_filters = self._split_filters( filters )
        if not fn_filters:
            # if no fn_filtering required, we can use the 'all orm' version with limit offset
            return self._orm_list( filters=orm_filters, order_by=order_by,
                limit=limit, offset=offset, **kwargs )

        # fn filters will change the number of items returnable by limit/offset - remove them here from the orm query
        query = self.query( filters=orm_filters, order_by=order_by, limit=None, offset=None, **kwargs )
        items = query.all()

        # apply limit, offset after SQL filtering
        items = self._apply_fn_filters_gen( items, fn_filters )
        return list( self._apply_fn_limit_offset_gen( items, limit, offset ) )

    def _split_filters( self, filters ):
        """
        Splits `filters` into a tuple of two lists:
            a list of filters to be added to the SQL query
        and a list of functional filters to be applied after the SQL query.
        """
        orm_filters, fn_filters = ( [], [] )
        if filters is None:
            return ( orm_filters, fn_filters )
        if not isinstance( filters, list ):
            filters = [ filters ]
        for filter_ in filters:
            if self._is_fn_filter( filter_ ):
                fn_filters.append( filter_ )
            else:
                orm_filters.append( filter_ )
        return ( orm_filters, fn_filters )

    def _is_fn_filter( self, filter_ ):
        """
        Returns True if `filter_` is a functional filter to be applied after the SQL query.
        """
        return callable( filter_ )

    def _orm_list( self, query=None, **kwargs ):
        """
        Sends kwargs to build the query return all models found.
        """
        query = query or self.query( **kwargs )
        return query.all()

    def _apply_fn_filters_gen( self, items, filters ):
        """
        If all the filter functions in `filters` return True for an item in `items`,
        yield that item.
        """
        # cpu-expensive
        for item in items:
            filter_results = [f( item ) for f in filters]
            if all( filter_results ):
                yield item

    def _apply_fn_limit_offset_gen( self, items, limit, offset ):
        """
        Iterate over `items` and begin yielding items after
        `offset` number of items and stop when we've yielded
        `limit` number of items.
        """
        # change negative limit, offset to None
        if limit is not None and limit < 0:
            limit = None
        if offset is not None and offset < 0:
            offset = None

        yielded = 0
        for i, item in enumerate( items ):
            if offset is not None and i < offset:
                continue
            if limit is not None and yielded >= limit:
                break
            yield item
            yielded += 1

    def by_ids( self, ids, filters=None, **kwargs ):
        """
        Returns an in-order list of models with the matching ids in `ids`.
        """
        if not ids:
            return []
        ids_filter = self.model_class.id.in_( ids )
        found = self.list( filters=self._munge_filters( ids_filter, filters ), **kwargs )
        # TODO: this does not order by the original 'ids' array

        # ...could use get (supposedly since found are in the session, the db won't be hit twice)
        # return map( self.session().query( self.model_class ).get, ids )

        # ...could implement own version here - slow?
        return self._order_items_by_id( ids, found )

    def _order_items_by_id( self, ids, items ):
        """
        Given a list of (unique) ids and a list of items having an 'id' attribute,
        return items that have the given ids in that order.

        If an id in ids is not found or if an item in items doesn't have a given
        id, they will not be in the returned list.
        """
        ID_ATTR_NAME = 'id'
        # TODO:?? aside from sqlalx.get mentioned above, I haven't seen an in-SQL way
        #   to make this happen. This may not be the most efficient way either.
        # NOTE: that this isn't sorting by id - this is matching the order in items to the order in ids
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

    def create( self, flush=True, *args, **kwargs ):
        """
        Generically create a new model.
        """
        # override in subclasses
        item = self.model_class( *args, **kwargs )
        self.session().add( item )
        if flush:
            self.session().flush()
        return item

    def copy( self, item, **kwargs ):
        """
        Clone or copy an item.
        """
        raise exceptions.NotImplemented( 'Abstract method' )

    def update( self, item, new_values, flush=True, **kwargs ):
        """
        Given a dictionary of new values, update `item` and return it.

        ..note: NO validation or deserialization occurs here.
        """
        self.session().add( item )
        for key, value in new_values.items():
            if hasattr( item, key ):
                setattr( item, key, value )
        if flush:
            self.session().flush()
        return item

    def associate( self, associate_with, item, foreign_key_name=None ):
        """
        Generically associate `item` with `associate_with` based on `foreign_key_name`.
        """
        foreign_key_name = foreign_key_name or self.foreign_key_name
        setattr( associate_with, foreign_key_name, item )
        return item

    def _foreign_key( self, associated_model_class, foreign_key_name=None ):
        foreign_key_name = foreign_key_name or self.foreign_key_name
        return getattr( associated_model_class, foreign_key_name )

    def query_associated( self, associated_model_class, item, foreign_key_name=None ):
        """
        Generically query other items that have been associated with this `item`.
        """
        foreign_key = self._foreign_key( associated_model_class, foreign_key_name=foreign_key_name )
        return self.session().query( associated_model_class ).filter( foreign_key == item )

    # a rename of sql DELETE to differentiate from the Galaxy notion of mark_as_deleted
    # def destroy( self, item, **kwargs ):
    #    return item


# ---- code for classes that use one *main* model manager
# TODO: this may become unecessary if we can access managers some other way (class var, app, etc.)
class HasAModelManager( object ):
    """
    Mixin used where serializers, deserializers, filter parsers, etc.
    need some functionality around the model they're mainly concerned with
    and would perform that functionality with a manager.
    """

    #: the class used to create this serializer's generically accessible model_manager
    model_manager_class = None
    # examples where this doesn't really work are ConfigurationSerializer (no manager)
    # and contents (2 managers)

    def __init__( self, app, manager=None, **kwargs ):
        self._manager = manager

    @property
    def manager( self ):
        """Return an appropriate manager if it exists, instantiate if not."""
        # PRECONDITION: assumes self.app is assigned elsewhere
        if not self._manager:
            # TODO: pass this serializer to it
            self._manager = self.model_manager_class( self.app )
            # this will error for unset model_manager_class'es
        return self._manager


# ==== SERIALIZERS/to_dict,from_dict
class ModelSerializingError( exceptions.InternalServerError ):
    """Thrown when request model values can't be serialized"""
    pass


class ModelDeserializingError( exceptions.ObjectAttributeInvalidException ):
    """Thrown when an incoming value isn't usable by the model
    (bad type, out of range, etc.)
    """
    pass


class SkipAttribute( Exception ):
    """
    Raise this inside a serializer to prevent the returned dictionary from having
    a the associated key or value for this attribute.
    """
    pass


class ModelSerializer( HasAModelManager ):
    """
    Turns models into JSONable dicts.

    Maintains a map of requestable keys and the Callable() serializer functions
    that should be called for those keys.
    E.g. { 'x' : lambda item, key: item.x, ... }

    Note: if a key to serialize is not listed in the Serializer.serializable_keyset
    or serializers, it will not be returned.

    To serialize call:
        my_serializer = MySerializer( app )
        ...
        keys_to_serialize = [ 'id', 'name', 'attr1', 'attr2', ... ]
        item_dict = MySerializer.serialize( my_item, keys_to_serialize )
    """
    #: 'service' to use for getting urls - use class var to allow overriding when testing
    url_for = staticmethod( routes.url_for )

    def __init__( self, app, **kwargs ):
        """
        Set up serializer map, any additional serializable keys, and views here.
        """
        super( ModelSerializer, self ).__init__( app, **kwargs )
        self.app = app

        # a list of valid serializable keys that can use the default (string) serializer
        #   this allows us to: 'mention' the key without adding the default serializer
        # TODO: we may want to eventually error if a key is requested
        #   that is in neither serializable_keyset or serializers
        self.serializable_keyset = set([])
        # a map of dictionary keys to the functions (often lambdas) that create the values for those keys
        self.serializers = {}
        # add subclass serializers defined there
        self.add_serializers()
        # update the keyset by the serializers (removing the responsibility from subclasses)
        self.serializable_keyset.update( self.serializers.keys() )

        # views are collections of serializable attributes (a named array of keys)
        #   inspired by model.dict_{view}_visible_keys
        self.views = {}
        self.default_view = None

    def add_serializers( self ):
        """
        Register a map of attribute keys -> serializing functions that will serialize
        the attribute.
        """
        self.serializers.update({
            'id'            : self.serialize_id,
            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,
        })

    def add_view( self, view_name, key_list, include_keys_from=None ):
        """
        Add the list of serializable attributes `key_list` to the serializer's
        view dictionary under the key `view_name`.

        If `include_keys_from` is a proper view name, extend `key_list` by
        the list in that view.
        """
        key_list = list( set( key_list + self.views.get( include_keys_from, [] ) ) )
        self.views[ view_name ] = key_list
        self.serializable_keyset.update( key_list )
        return key_list

    def serialize( self, item, keys, **context ):
        """
        Serialize the model `item` to a dictionary.

        Given model `item` and the list `keys`, create and return a dictionary
        built from each key in `keys` that also exists in `serializers` and
        values of calling the keyed/named serializers on item.
        """
        # TODO: constrain context to current_user/whos_asking when that's all we need (trans)
        returned = {}
        for key in keys:
            # check both serializers and serializable keys
            if key in self.serializers:
                try:
                    returned[ key ] = self.serializers[ key ]( item, key, **context )
                except SkipAttribute:
                    # dont add this key if the deserializer threw this
                    pass
            elif key in self.serializable_keyset:
                returned[ key ] = self.default_serializer( item, key, **context )
            # ignore bad/unreg keys
        return returned

    def skip( self, msg='skipped' ):
        """
        To be called from inside a serializer to skip it.

        Handy for config checks, information hiding, etc.
        """
        raise SkipAttribute( msg )

    def _remap_from( self, original_key ):
        if original_key in self.serializers:
            return self.serializers[ original_key ]
        if original_key in self.serializable_keyset:
            return lambda i, k, **c: self.default_serializer( i, original_key, **c )
        raise KeyError( 'serializer not found for remap: ' + original_key )

    def default_serializer( self, item, key, **context ):
        """
        Serialize the `item`'s attribute named `key`.
        """
        # TODO:?? point of change but not really necessary?
        return getattr( item, key )

    # serializers for common galaxy objects
    def serialize_date( self, item, key, **context ):
        """
        Serialize a date attribute of `item`.
        """
        date = getattr( item, key )
        return date.isoformat() if date is not None else None

    def serialize_id( self, item, key, **context ):
        """
        Serialize an id attribute of `item`.
        """
        id = getattr( item, key )
        # Note: it may not be best to encode the id at this layer
        return self.app.security.encode_id( id ) if id is not None else None

    def serialize_type_id( self, item, key, **context ):
        """
        Serialize an type-id for `item`.
        """
        TYPE_ID_SEP = '-'
        type_id = getattr( item, key )
        if type_id is None:
            return None
        split = type_id.split( TYPE_ID_SEP, 1 )
        # Note: it may not be best to encode the id at this layer
        return TYPE_ID_SEP.join([ split[0], self.app.security.encode_id( split[1] )])

    # serializing to a view where a view is a predefied list of keys to serialize
    def serialize_to_view( self, item, view=None, keys=None, default_view=None, **context ):
        """
        Use a predefined list of keys (the string `view`) and any additional keys
        listed in `keys`.

        The combinations can be:
            `view` only: return those keys listed in the named view
            `keys` only: return those keys listed
            no `view` or `keys`: use the `default_view` if any
            `view` and `keys`: combine both into one list of keys
        """

        # TODO: default view + view makes no sense outside the API.index context - move default view there
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

        return self.serialize( item, all_keys, **context )

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


class ModelDeserializer( HasAModelManager ):
    """
    An object that converts an incoming serialized dict into values that can be
    directly assigned to an item's attributes and assigns them.
    """
    # TODO:?? a larger question is: which should be first? Deserialize then validate - or - validate then deserialize?

    def __init__( self, app, validator=None, **kwargs ):
        """
        Set up deserializers and validator.
        """
        super( ModelDeserializer, self ).__init__( app, **kwargs )
        self.app = app

        self.deserializers = {}
        self.deserializable_keyset = set([])
        self.add_deserializers()
        # a sub object that can validate incoming values
        self.validate = validator or ModelValidator( self.app )

    def add_deserializers( self ):
        """
        Register a map of attribute keys -> functions that will deserialize data
        into attributes to be assigned to the item.
        """
        # to be overridden in subclasses
        pass

    def deserialize( self, item, data, flush=True, **context ):
        """
        Convert an incoming serialized dict into values that can be
        directly assigned to an item's attributes and assign them
        """
        # TODO: constrain context to current_user/whos_asking when that's all we need (trans)
        sa_session = self.app.model.context
        new_dict = {}
        for key, val in data.items():
            if key in self.deserializers:
                new_dict[ key ] = self.deserializers[ key ]( item, key, val, **context )
            # !important: don't error on unreg. keys -- many clients will add weird ass keys onto the model

        # TODO:?? add and flush here or in manager?
        if flush and len( new_dict ):
            sa_session.add( item )
            sa_session.flush()

        return new_dict

    # ... common deserializers for primitives
    def default_deserializer( self, item, key, val, **context ):
        """
        If the incoming `val` is different than the `item` value change it
        and, in either case, return the value.
        """
        # TODO: sets the item attribute to value (this may not work in all instances)

        # only do the following if val == getattr( item, key )
        if hasattr( item, key ) and getattr( item, key ) != val:
            setattr( item, key, val )
        return val

    def deserialize_basestring( self, item, key, val, convert_none_to_empty=False, **context ):
        val = '' if ( convert_none_to_empty and val is None ) else self.validate.basestring( key, val )
        return self.default_deserializer( item, key, val, **context )

    def deserialize_bool( self, item, key, val, **context ):
        val = self.validate.bool( key, val )
        return self.default_deserializer( item, key, val, **context )

    def deserialize_int( self, item, key, val, min=None, max=None, **context ):
        val = self.validate.int_range( key, val, min, max )
        return self.default_deserializer( item, key, val, **context )

    # def deserialize_date( self, item, key, val ):
    #    #TODO: parse isoformat date into date object

    # ... common deserializers for Galaxy
    def deserialize_genome_build( self, item, key, val, **context ):
        """
        Make sure `val` is a valid dbkey and assign it.
        """
        val = self.validate.genome_build( key, val )
        return self.default_deserializer( item, key, val, **context )


class ModelValidator( HasAModelManager ):
    """
    An object that inspects a dictionary (generally meant to be a set of
    new/updated values for the model) and raises an error if a value is
    not acceptable.
    """

    def __init__( self, app, *args, **kwargs ):
        super( ModelValidator, self ).__init__( app, **kwargs )
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
        return self.type( key, val, string_types )

    def bool( self, key, val ):
        return self.type( key, val, bool )

    def int( self, key, val ):
        return self.type( key, val, int )

    def nullable_basestring( self, key, val ):
        """
        Must be a basestring or None.
        """
        return self.type( key, val, ( string_types, type( None ) ) )

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
        # TODO: Here's where compound types start becoming a nightmare. Any more or more complex
        #   and should find a different way.
        val = self.type( key, val, list )
        return [ self.basestring( key, elem ) for elem in val ]

    # validators for Galaxy
    def genome_build( self, key, val ):
        """
        Must be a valid base_string.

        Note: no checking against installation's ref list is done as many
        data sources consider this an open field.
        """
        # TODO: is this correct?
        if val is None:
            return '?'
        # currently, data source sites like UCSC are able to set the genome build to non-local build names
        # afterwards, attempting to validate the whole model will choke here
        # for genome_build_shortname, longname in self.app.genome_builds.get_genome_build_names( trans=trans ):
        #     if val == genome_build_shortname:
        #         return val
        # raise exceptions.RequestParameterInvalidException( "invalid reference", key=key, val=val )
        # IOW: fallback to string validation
        return self.basestring( key, val )

    # def slug( self, item, key, val ):
    #    """validate slug"""
    #    pass


# ==== Building query filters based on model data
class ModelFilterParser( HasAModelManager ):
    """
    Converts string tuples (partially converted query string params) of
    attr, op, val into either:

    - ORM based filters (filters that can be applied by the ORM at the SQL
      level) or
    - functional filters (filters that use derived values or values not
      within the SQL tables)

    These filters can then be applied to queries.

    This abstraction allows 'smarter' application of limit and offset at either the
    SQL level or the generator/list level based on the presence of functional
    filters. In other words, if no functional filters are present, limit and offset
    may be applied at the SQL level. If functional filters are present, limit and
    offset need to applied at the list level.

    These might be safely be replaced in the future by creating SQLAlchemy
    hybrid properties or more thoroughly mapping derived values.
    """
    # ??: this class kindof 'lives' in both the world of the controllers/param-parsing and to models/orm
    # (as the model informs how the filter params are parsed)
    # I have no great idea where this 'belongs', so it's here for now

    #: model class
    model_class = None

    def __init__( self, app, **kwargs ):
        """
        Set up serializer map, any additional serializable keys, and views here.
        """
        super( ModelFilterParser, self ).__init__( app, **kwargs )
        self.app = app

        #: regex for testing/dicing iso8601 date strings, with optional time and ms, but allowing only UTC timezone
        self.date_string_re = re.compile( r'^(\d{4}\-\d{2}\-\d{2})[T| ]{0,1}(\d{2}:\d{2}:\d{2}(?:\.\d{1,6}){0,1}){0,1}Z{0,1}$' )

        # dictionary containing parsing data for ORM/SQLAlchemy-based filters
        # ..note: although kind of a pain in the ass and verbose, opt-in/whitelisting allows more control
        #   over potentially expensive queries
        self.orm_filter_parsers = {}

        #: dictionary containing parsing data for functional filters - applied after a query is made
        self.fn_filter_parsers = {}

        # set up both of the above
        self._add_parsers()

    def _add_parsers( self ):
        """
        Set up, extend, or alter `orm_filter_parsers` and `fn_filter_parsers`.
        """
        # note: these are the default filters for all models
        self.orm_filter_parsers.update({
            # (prob.) applicable to all models
            'id'            : { 'op': ( 'in' ) },
            'encoded_id'    : { 'column' : 'id', 'op': ( 'in' ), 'val': self.parse_id_list },
            # dates can be directly passed through the orm into a filter (no need to parse into datetime object)
            'create_time'   : { 'op': ( 'le', 'ge' ), 'val': self.parse_date },
            'update_time'   : { 'op': ( 'le', 'ge' ), 'val': self.parse_date },
        })

    def parse_filters( self, filter_tuple_list ):
        """
        Parse string 3-tuples (attr, op, val) into orm or functional filters.
        """
        # TODO: allow defining the default filter op in this class (and not 'eq' in base/controller.py)
        parsed = []
        for ( attr, op, val ) in filter_tuple_list:
            filter_ = self.parse_filter( attr, op, val )
            parsed.append( filter_ )
        return parsed

    def parse_filter( self, attr, op, val ):
        """
        Attempt to parse filter as a custom/fn filter, then an orm filter, and
        if neither work - raise an error.

        :raises exceptions.RequestParameterInvalidException: if no functional or orm
            filter can be parsed.
        """
        try:
            # check for a custom filter
            fn_filter = self._parse_fn_filter( attr, op, val )
            if fn_filter is not None:
                return fn_filter

            # if no custom filter found, try to make an ORM filter
            # note: have to use explicit is None here, bool( sqlalx.filter ) == False
            orm_filter = self._parse_orm_filter( attr, op, val )
            if orm_filter is not None:
                return orm_filter

        # by convention, assume most val parsers raise ValueError
        except ValueError as val_err:
            raise exceptions.RequestParameterInvalidException( 'unparsable value for filter',
                column=attr, operation=op, value=val, ValueError=str( val_err ) )

        # if neither of the above work, raise an error with how-to info
        # TODO: send back all valid filter keys in exception for added user help
        raise exceptions.RequestParameterInvalidException( 'bad filter', column=attr, operation=op )

    # ---- fn filters
    def _parse_fn_filter( self, attr, op, val ):
        """
        Attempt to parse a non-ORM filter function.
        """
        # fn_filter_list is a dict: fn_filter_list[ attr ] = { 'opname1' : opfn1, 'opname2' : opfn2, etc. }

        # attr, op is a nested dictionary pointing to the filter fn
        attr_map = self.fn_filter_parsers.get( attr, None )
        if not attr_map:
            return None
        allowed_ops = attr_map.get( 'op' )
        # allowed ops is a map here, op => fn
        filter_fn = allowed_ops.get( op, None )
        if not filter_fn:
            return None
        # parse the val from string using the 'val' parser if present (otherwise, leave as string)
        val_parser = attr_map.get( 'val', None )
        if val_parser:
            val = val_parser( val )

        # curry/partial and fold the val in there now
        return lambda i: filter_fn( i, val )

    # ---- ORM filters
    def _parse_orm_filter( self, attr, op, val ):
        """
        Attempt to parse a ORM-based filter.

        Using SQLAlchemy, this would yield a sql.elements.BinaryExpression.
        """
        # orm_filter_list is a dict: orm_filter_list[ attr ] = <list of allowed ops>
        column_map = self.orm_filter_parsers.get( attr, None )
        if not column_map:
            # no column mapping (not whitelisted)
            return None
        # attr must be a whitelisted column by attr name or by key passed in column_map
        # note: column_map[ 'column' ] takes precedence
        if 'column' in column_map:
            attr = column_map[ 'column' ]
        column = self.model_class.table.columns.get( attr )
        if column is None:
            # could be a property (hybrid_property, etc.) - assume we can make a filter from it
            column = getattr( self.model_class, attr )
        if column is None:
            # no orm column
            return None

        # op must be whitelisted: contained in the list orm_filter_list[ attr ][ 'op' ]
        allowed_ops = column_map.get( 'op' )
        if op not in allowed_ops:
            return None
        op = self._convert_op_string_to_fn( column, op )
        if not op:
            return None

        # parse the val from string using the 'val' parser if present (otherwise, leave as string)
        val_parser = column_map.get( 'val', None )
        if val_parser:
            val = val_parser( val )

        orm_filter = op( val )
        return orm_filter

    #: these are the easier/shorter string equivalents to the python operator fn names that need '__' around them
    UNDERSCORED_OPS = ( 'lt', 'le', 'eq', 'ne', 'ge', 'gt' )

    def _convert_op_string_to_fn( self, column, op_string ):
        """
        Convert the query string filter op shorthand into actual ORM usable
        function names, then return the ORM function.
        """
        # correct op_string to usable function key
        fn_name = op_string
        if op_string in self.UNDERSCORED_OPS:
            fn_name = '__' + op_string + '__'
        elif op_string == 'in':
            fn_name = 'in_'

        # get the column fn using the op_string and error if not a callable attr
        # TODO: special case 'not in' - or disallow?
        op_fn = getattr( column, fn_name, None )
        if not op_fn or not callable( op_fn ):
            return None
        return op_fn

    # ---- preset fn_filters: dictionaries of standard filter ops for standard datatypes
    def string_standard_ops( self, key ):
        return {
            'op' : {
                'eq'        : lambda i, v: v == getattr( i, key ),
                'contains'  : lambda i, v: v in getattr( i, key ),
            }
        }

    # --- more parsers! yay!
    # TODO: These should go somewhere central - we've got ~6 parser modules/sections now
    def parse_bool( self, bool_string ):
        """
        Parse a boolean from a string.
        """
        # Be strict here to remove complexity of options (but allow already parsed).
        if bool_string in ( 'True', True ):
            return True
        if bool_string in ( 'False', False ):
            return False
        raise ValueError( 'invalid boolean: ' + str( bool_string ) )

    def parse_id_list( self, id_list_string, sep=',' ):
        """
        Split `id_list_string` at `sep`.
        """
        # TODO: move id decoding out
        id_list = [ self.app.security.decode_id( id_ ) for id_ in id_list_string.split( sep ) ]
        return id_list

    def parse_int_list( self, int_list_string, sep=',' ):
        """
        Split `int_list_string` at `sep` and parse as ints.
        """
        # TODO: move id decoding out
        int_list = [ int( v ) for v in int_list_string.split( sep ) ]
        return int_list

    def parse_date( self, date_string ):
        """
        Reformats a string containing either seconds from epoch or an iso8601 formated
        date string into a new date string usable within a filter query.

        Seconds from epoch can be a floating point value as well (i.e containing ms).
        """
        # assume it's epoch if no date separator is present
        try:
            epoch = float( date_string )
            datetime_obj = datetime.datetime.fromtimestamp( epoch )
            return datetime_obj.isoformat( sep=' ' )
        except ValueError:
            pass

        match = self.date_string_re.match( date_string )
        if match:
            date_string = ' '.join([ group for group in match.groups() if group ])
            return date_string
        raise ValueError( 'datetime strings must be in the ISO 8601 format and in the UTC' )
