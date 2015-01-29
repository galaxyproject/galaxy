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

import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy

from galaxy import exceptions
from galaxy import model
from galaxy.model import tool_shed_install

import logging
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

    # .... query foundation wrapper
    def query( self, trans, eagerloads=True, filters=None, order_by=None, limit=None, offset=None, **kwargs ):
        """
        Return a basic query from model_class, filters, order_by, and limit and offset.

        Set eagerloads to False to disable them for this query.
        """
        query = trans.sa_session.query( self.model_class )
        # joined table loading
        if eagerloads is False:
            query = query.enable_eagerloads( False )

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
        # TODO: there's nothing specifically filter or model-related here - move to util
        if filtersA is None:
            return filtersB
        if filtersB is None:
            return filtersA
        if not isinstance( filtersA, list ):
            filtersA = [ filtersA ]
        if not isinstance( filtersB, list ):
            filtersB = [ filtersB ]
        return filtersA + filtersB

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

    #NOTE: at this layer, all ids are expected to be decoded and in int form
    def by_id( self, trans, id, **kwargs ):
        """
        Gets a model by primary id.
        """
        id_filter = self.model_class.id == id
        return self.one( trans, filters=id_filter, **kwargs )

    # .... multirow queries
    def _orm_list( self, trans, query=None, **kwargs ):
        """
        Sends kwargs to build the query return all models found.
        """
        query = query or self.query( trans, **kwargs )
        return query.all()

    #def list( self, trans, query=None, filters=None, order_by=None, limit=None, offset=None, **kwargs ):
    def list( self, trans, filters=None, order_by=None, limit=None, offset=None, **kwargs ):
        """
        Returns all objects matching the given filters
        """
        orm_filters, fn_filters = self._split_filters( filters )
        if not fn_filters:
            # if no fn_filtering required, we can use the 'all orm' version with limit offset
            return self._orm_list( trans, filters=orm_filters, order_by=order_by, limit=limit, offset=offset, **kwargs )

        # fn filters will change the number of items returnable by limit/offset - remove them here from the orm query
        query = self.query( trans, filters=orm_filters, order_by=order_by, limit=None, offset=None, **kwargs )
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

    def _apply_fn_filters_gen( self, items, filters ):
        """
        If all the filter functions in `filters` return True for an item in `items`,
        yield that item.
        """
        #cpu-expensive
        for item in items:
            filter_results = map( lambda f: f( item ), filters )
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

    def by_ids( self, trans, ids, filters=None, **kwargs ):
        """
        Returns an in-order list of models with the matching ids in `ids`.
        """
        ids_filter = self.model_class.id.in_( ids )
        found = self.list( trans, filters=self._munge_filters( ids_filter, filters ), **kwargs )
        # TODO: this does not order by the original 'ids' array

        # ...could use get (supposedly since found are in the session, the db won't be hit twice)
        # return map( trans.sa_session.query( self.model_class ).get, ids )

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

    # TODO: yagni?
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

    # a rename of sql DELETE to differentiate from the Galaxy notion of mark_as_deleted
    # def destroy( self, trans, item, **kwargs ):
    #    return item


# ==== SERIALIZERS/to_dict,from_dict
class ModelSerializingError( exceptions.InternalServerError ):
    """Thrown when request model values can't be serialized"""
    pass


class ModelDeserializingError( exceptions.ObjectAttributeInvalidException ):
    """Thrown when an incoming value isn't usable by the model
    (bad type, out of range, etc.)
    """
    pass


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
        # NOTE: if a key is requested that is in neither serializable_keys or serializers, it is not returned
        self.serializable_keys = []
        # add subclass serializers defined there
        self.add_serializers()

        # views are collections of serializable attributes (a named array of keys)
        #   inspired by model.dict_{view}_visible_keys
        self.views = {}
        self.default_view = None

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
        # TODO:?? point of change but not really necessary?
        return getattr( item, key )

    # serializers for common galaxy objects
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

    # serializing to a view where a view is a predefied list of keys to serialize
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


class ModelDeserializer( object ):
    """
    An object that converts an incoming serialized dict into values that can be
    directly assigned to an item's attributes and assigns them.
    """
    #: the class used to create this deserializer's generically accessible model_manager
    model_manager_class = None

    #TODO:?? a larger question is: which should be first? Deserialize then validate - or - validate then deserialize?

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
            # !important: don't error on unreg. keys -- many clients will add weird ass keys onto the model

        # TODO:?? add and flush here or in manager?
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
        # TODO: sets the item attribute to value (this may not work in all instances)

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

    #def deserialize_date( self, trans, item, key, val ):
    #   #TODO: parse isoformat date into date object

    # ... common deserializers for Galaxy
    def deserialize_genome_build( self, trans, item, key, val ):
        """
        Make sure `val` is a valid dbkey and assign it.
        """
        val = self.validate.genome_build( trans, key, val )
        return self.default_deserializer( trans, item, key, val )


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
        # TODO: Here's where compound types start becoming a nightmare. Any more or more complex
        #   and should find a different way.
        val = self.type( key, val, list )
        return [ self.basestring( key, elem ) for elem in val ]

    # validators for Galaxy
    def genome_build( self, trans, key, val ):
        """
        Must be a valid genome_build/dbkey/reference/whatever-the-hell-were-calling-them-now.
        """
        # TODO: is this correct?
        if val is None:
            return '?'
        for genome_build_shortname, longname in self.app.genome_builds.get_genome_build_names( trans=trans ):
            if val == genome_build_shortname:
                return val
        raise exceptions.RequestParameterInvalidException( "invalid reference", key=key, val=val )

    # def slug( self, trans, item, key, val ):
    #    """validate slug"""
    #    pass


# ==== Building query filters based on model data
class FilterParser( object ):
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
    #??: this class kindof 'lives' in both the world of the controllers/param-parsing and to models/orm
    # (as the model informs how the filter params are parsed)
    # I have no great idea where this 'belongs', so it's here for now

    #: model class
    model_class = None

    def __init__( self, app ):
        """
        Set up serializer map, any additional serializable keys, and views here.
        """
        self.app = app

        #: dictionary containing parsing data for ORM/SQLAlchemy-based filters
        #..note: although kind of a pain in the ass and verbose, opt-in/whitelisting allows more control
        #:   over potentially expensive queries
        self.orm_filter_parsers = {}

        #: dictionary containing parsing data for functional filters - applied after a query is made
        self.fn_filter_parsers = {}

        # set up both of the above
        self._add_parsers()

    def _add_parsers( self ):
        """
        Set up, extend, or alter `orm_filter_parsers` and `fn_filter_parsers`.
        """
        pass
        
    def parse_filters( self, filter_tuple_list ):
        """
        Parse string 3-tuples (attr, op, val) into orm or functional filters.
        """
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
            #note: have to use explicit is None here, bool( sqlalx.filter ) == False
            orm_filter = self._parse_orm_filter( attr, op, val )
            if orm_filter is not None:
                return orm_filter

        # by convention, assume most val parsers raise ValueError
        except ValueError, val_err:
            raise exceptions.RequestParameterInvalidException( 'unparsable value for filter',
                column=attr, operation=op, value=val )

        # if neither of the above work, raise an error with how-to info
        #TODO: send back all valid filter keys in exception for added user help
        raise exceptions.RequestParameterInvalidException( 'bad filter', column=attr, operation=op )

    # ---- fn filters
    def _parse_fn_filter( self, attr, op, val ):
        """
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
        """
        # orm_filter_list is a dict: orm_filter_list[ attr ] = <list of allowed ops>
        # attr must be a whitelisted column
        column = self.model_class.table.columns.get( attr )
        column_map = self.orm_filter_parsers.get( attr, None )
        if column is None or not column_map:
            return None
        # op must be whitelisted: contained in the list orm_filter_list[ attr ][ 'op' ]
        allowed_ops = column_map.get( 'op' )
        if op not in allowed_ops:
            return None
        op = self._convert_op_string_to_fn( column, op )
        # parse the val from string using the 'val' parser if present (otherwise, leave as string)
        val_parser = column_map.get( 'val', None )
        if val_parser:
            val = val_parser( val )

        orm_filter = op( val )
        return orm_filter

    #: these are the easier/shorter string equivalents to the python operator fn names that need '__' around them
    UNDERSCORED_OPS = ( 'lt', 'le', 'eq', 'ne', 'ge', 'gt' )
    #UNCHANGED_OPS = ( 'like' )
    def _convert_op_string_to_fn( self, column, op_string ):
        """
        """
        # correct op_string to usable function key
        fn_name = op_string
        if   op_string in self.UNDERSCORED_OPS:
            fn_name = '__' + op_string + '__'
        elif op_string == 'in':
            fn_name = 'in_'

        # get the column fn using the op_string and error if not a callable attr
        #TODO: special case 'not in' - or disallow?
        op_fn = getattr( column, fn_name, None )
        if not op_fn or not callable( op_fn ):
            return None
        return op_fn

    # --- more parsers! yay!
#TODO: These should go somewhere central - we've got ~6 parser modules/sections now
    #TODO: to annotatable
    def _owner_annotation( self, item ):
        """
        Get the annotation by the item's owner.
        """
        if not item.user:
            return None
        for annotation in item.annotations:
            if annotation.user == item.user:
                return annotation.annotation
        return None

    def filter_annotation_contains( self, item, val ):
        """
        Test whether `val` is in the owner's annotation.
        """
        owner_annotation = self._owner_annotation( item )
        if owner_annotation is None:
            return False
        return val in owner_annotation

    #TODO: to taggable
    def _tag_str_gen( self, item ):
        """
        Return a list of strings built from the item's tags.
        """
        #TODO: which user is this? all?
        for tag in item.tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += ":" + tag.user_value
            yield tag_str

    def filter_has_partial_tag( self, item, val ):
        """
        Return True if any tag partially contains `val`.
        """
        for tag_str in self._tag_str_gen( item ):
            if val in tag_str:
                return True
        return False

    def filter_has_tag( self, item, val ):
        """
        Return True if any tag exactly equals `val`.
        """
        for tag_str in self._tag_str_gen( item ):
            if val == tag_str:
                return True
        return False

    def parse_bool( self, bool_string ):
        """
        Parse a boolean from a string.
        """
        #Be strict here to remove complexity of options.
        if bool_string in ( 'True', True ):
            return True
        if bool_string in ( 'False', False ):
            return False
        raise ValueError( 'invalid boolean: ' + str( bool_string ) )

    def parse_id_list( self, id_list_string, sep=',' ):
        """
        Split `id_list_string` at `sep`.
        """
        return id_list_string.split( sep )


# ==== Security Mixins
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

    # TODO:?? are these even useful?
    def list_accessible( self, trans, user, **kwargs ):
        """
        Return a list of items accessible to the user, raising an error if ANY
        are inaccessible.

        :raises exceptions.ItemAccessibilityException:
        """
        raise exceptions.NotImplemented( "Abstract Interface Method" )
        # NOTE: this will be a large, inefficient list if filters are not passed in kwargs
        # items = ModelManager.list( self, trans, **kwargs )
        # return [ self.error_unless_accessible( trans, item, user ) for item in items ]

    def filter_accessible( self, trans, user, **kwargs ):
        """
        Return a list of items accessible to the user.
        """
        raise exceptions.NotImplemented( "Abstract Interface Method" )
        # NOTE: this will be a large, inefficient list if filters are not  passed in kwargs
        # items = ModelManager.list( self, trans, **kwargs )
        # return filter( lambda item: self.is_accessible( trans, item, user ), items )


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
        raise exceptions.NotImplemented( "Abstract Interface Method" )
        # just alias to by_user (easier/same thing)
        #return self.by_user( trans, user, **kwargs )

    def filter_owned( self, trans, user, **kwargs ):
        """
        Return a list of items owned by the user.
        """
        # just alias to list_owned
        return self.list_owned( trans, user, **kwargs )


# ---- Deletable and Purgable models
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


# TODO: these are of questionable value if we don't want to enable users to delete/purge via update
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
        # TODO:?? flush=False?
        if new_deleted:
            self.manager.delete( trans, item, flush=False )
        else:
            self.manager.undelete( trans, item, flush=False )
        return item.deleted


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
