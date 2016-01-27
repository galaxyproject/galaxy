"""
Heterogenous lists/contents are difficult to query properly since unions are
not easily made.
"""

from sqlalchemy import literal
from sqlalchemy import text
from sqlalchemy import asc, desc

from galaxy import model
from galaxy import exceptions as glx_exceptions

from galaxy.managers import base
from galaxy.managers import deletable
from galaxy.managers import containers
from galaxy.managers import hdas
from galaxy.managers import collections

import logging
log = logging.getLogger( __name__ )


# into its own class to have it's own filters, etc.
# TODO: but can't inherit from model manager (which assumes only one model)
class HistoryContentsManager( containers.ContainerManagerMixin ):

    root_container_class = model.History
    contained_class = model.HistoryDatasetAssociation
    subcontainer_class = model.HistoryDatasetCollectionAssociation
    default_order_by = 'hid'

    def __init__( self, app ):
        self.app = app
        self.contained_manager = hdas.HDAManager( app )
        self.subcontainer_manager = collections.DatasetCollectionManager( app )

    # ---- interface
    def contained( self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs ):
        """
        Returns non-subcontainer objects within `container`.
        """
        filter_to_inside_container = self._get_filter_for_contained( container, self.contained_class )
        filters = base.munge_lists( filter_to_inside_container, filters )
        return self.contained_manager.list( filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs )

    def subcontainers( self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs ):
        """
        Returns only the containers within `container`.
        """
        filter_to_inside_container = self._get_filter_for_contained( container, self.subcontainer_class )
        filters = base.munge_lists( filter_to_inside_container, filters )
        # TODO: collections.DatasetCollectionManager doesn't have the list
        # return self.subcontainer_manager.list( filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs )
        return self.session().query( self.subcontainer_class ).filter( filters ).all()

    def contents( self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs ):
        """
        Returns a list of both/all types of contents, filtered and in some order.
        """
        # TODO?: we could branch here based on 'if limit is None and offset is None' - to a simpler (non-union) query
        # for now, I'm just using this (even for non-limited/offset queries) to reduce code paths
        return self._union_of_contents( container,
            filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs )

    # order_by parsing - similar to FilterParser but not enough yet to warrant a class?
    def parse_order_by( self, order_by_string, default=None ):
        """Return an ORM compatible order_by using the given string"""
        if order_by_string in ( 'hid', 'hid-dsc' ):
            return desc( 'hid' )
        if order_by_string == 'hid-asc':
            return asc( 'hid' )
        if order_by_string in ( 'create_time', 'create_time-dsc' ):
            return desc( 'create_time' )
        if order_by_string == 'create_time-asc':
            return asc( 'create_time' )
        if order_by_string in ( 'update_time', 'update_time-dsc' ):
            return desc( 'update_time' )
        if order_by_string == 'update_time-asc':
            return asc( 'update_time' )
        if order_by_string in ( 'name', 'name-asc' ):
            return asc( 'name' )
        if order_by_string == 'name-dsc':
            return desc( 'name' )
        if default:
            return self.parse_order_by( default )
        raise glx_exceptions.RequestParameterInvalidException( 'Unkown order_by', order_by=order_by_string,
            available=[ 'create_time', 'update_time', 'name', 'hid' ])

    #: the columns which are common to both subcontainers and non-subcontainers.
    #  (Also the attributes that may be filtered or orderered_by)
    common_columns = (
        "history_id",
        "model_class",
        "id",
        "history_content_type",
        "collection_id",
        "hid",
        "name",
        "deleted",
        "purged",
        "visible",
        "create_time",
        "update_time",
    )

    # ---- private
    def session( self ):
        return self.app.model.context

    def _filter_to_contents_query( self, container, content_class, **kwargs ):
        # TODO: use list (or by_history etc.)
        container_filter = self._get_filter_for_contained( container, content_class )
        query = self.session().query( content_class ).filter( container_filter )
        return query

    def _get_filter_for_contained( self, container, content_class ):
        return content_class.history == container

    def _union_of_contents( self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs ):
        """
        Returns a limited and offset list of both types of contents, filtered
        and in some order.
        """
        order_by = order_by if order_by is not None else self.default_order_by
        order_by = order_by if isinstance( order_by, ( tuple, list ) ) else ( order_by, )

        # TODO: 3 queries and 3 iterations over results - this is undoubtedly better solved in the actual SQL layer
        # via one common table for contents, Some Yonder Resplendent and Fanciful Join, or ORM functionality
        # Here's the (bizarre) strategy:
        #   1. create a union of common columns between contents classes - filter, order, and limit/offset this
        #   2. extract the ids returned from 1 for each class, query each content class by that id list
        #   3. use the results/order from 1 to recombine/merge the 2+ query result lists from 2, return that

        # note: I'm trying to keep these private functions as generic as possible in order to move them toward base later

        # query 1: create a union of common columns for which the component_classes can be filtered/limited
        contained_query = self._contents_common_query_for_contained( container.id )
        subcontainer_query = self._contents_common_query_for_subcontainer( container.id )
        contents_query = contained_query.union( subcontainer_query )

        # TODO: this needs the same fn/orm split that happens in the main query
        for orm_filter in ( filters or [] ):
            contents_query = contents_query.filter( orm_filter )

        contents_query = contents_query.order_by( *order_by )

        if limit is not None:
            contents_query = contents_query.limit( limit )
        if offset is not None:
            contents_query = contents_query.offset( offset )
        contents_results = contents_query.all()
        # print 'contents_results'
        # for r in contents_results:
        #     print r

        # partition ids into a map of { component_class names -> list of ids } from the above union query
        id_map = dict( (( self.contained_class.__name__, [] ), ( self.subcontainer_class.__name__, [] )) )
        for result in contents_results:
            result_type = self._get_union_classstr( result )
            contents_id = self._get_union_id( result )
            if result_type in id_map:
                id_map[ result_type ].append( contents_id )
            else:
                raise TypeError( 'Unknown contents type:', result_type )
        # print 'id_map'
        # for tuple_ in id_map.items():
        #     print tuple_

        # query 2 & 3: use the ids to query each component_class
        # query the contained classes using the id_lists for each
        for component_class in ( self.contained_class, self.subcontainer_class ):
            id_list = id_map[ component_class.__name__ ]
            id_map[ component_class.__name__ ] = self._by_ids( component_class, id_list )
        # for tuple_ in id_map.items():
        #     print tuple_

        # cycle back over the union query to create an ordered list of the objects returned in queries 2 & 3 above
        contents = []
        # TODO: or as generator?
        for result in contents_results:
            result_type = self._get_union_classstr( result )
            contents_id = self._get_union_id( result )
            content = id_map[ result_type ][ contents_id ]
            contents.append( content )
        return contents

    def _contents_common_columns( self, component_class, **kwargs ):
        columns = []
        # pull column from class by name or override with kwargs if listed there, then label
        for column_name in self.common_columns:
            if column_name in kwargs:
                column = kwargs.get( column_name, None )
            elif column_name == "model_class":
                column = literal( component_class.__name__ )
            else:
                column = getattr( component_class, column_name )
            column = column.label( column_name )
            columns.append( column )
        return columns

    def _contents_common_query_for_contained( self, history_id ):
        component_class = self.contained_class
        columns = self._contents_common_columns( component_class,
            history_content_type=literal( 'dataset' ),
            # gen. do not have inner collections
            collection_id=literal( None )
        )
        return self.session().query( *columns ).filter( component_class.history_id == history_id )

    def _contents_common_query_for_subcontainer( self, history_id ):
        component_class = self.subcontainer_class
        columns = self._contents_common_columns( component_class,
            history_content_type=literal( 'dataset_collection' ),
            # TODO: should be purgable? fix
            purged=literal( False ),
            # these are attached instead to the inner collection joined below
            create_time=model.DatasetCollection.create_time,
            update_time=model.DatasetCollection.update_time
        )
        subquery = self.session().query( *columns )
        # for the HDCA's we need to join the DatasetCollection since it has update/create times
        subquery = subquery.join( model.DatasetCollection,
            model.DatasetCollection.id == component_class.collection_id )
        subquery = subquery.filter( component_class.history_id == history_id )
        return subquery

    def _get_union_classstr( self, union ):
        """Return the string name of the class for this row in the union results"""
        return str( union[ 1 ] )

    def _get_union_id( self, union ):
        """Return the id for this row in the union results"""
        return union[ 2 ]

    def _by_ids( self, component_class, id_list ):
        if not id_list:
            return []
        query = self.session().query( component_class ).filter( component_class.id.in_( id_list ) )
        return dict( ( row.id, row ) for row in query.all() )


class HistoryContentsFilters( base.ModelFilterParser, deletable.PurgableFiltersMixin ):
    # surprisingly (but ominously), this works for both content classes in the union that's filtered
    model_class = model.HistoryDatasetAssociation

    def _parse_orm_filter( self, attr, op, val ):
        # the following allows 'q=history_content_type-eq&qv=dataset', etc. while still using contents above
        # (although it might be better to branch to the individual content managers since this filter makes the union unneccessary)
        # TODO: instead branch to subcontainers or contained (from within contents)
        # TODO: factor out ability to run text orm queries into base
        if attr == 'history_content_type' and op == 'eq':
            if val == 'dataset':
                return text( 'history_content_type = "dataset"' )
            if val == 'dataset_collection':
                return text( 'history_content_type = "dataset_collection"' )
        return super( HistoryContentsFilters, self )._parse_orm_filter( attr, op, val )

    def _add_parsers( self ):
        super( HistoryContentsFilters, self )._add_parsers()
        deletable.PurgableFiltersMixin._add_parsers( self )
        self.orm_filter_parsers.update({
            'name'      : { 'op': ( 'eq', 'contains', 'like' ) },
            'visible'   : { 'op': ( 'eq' ), 'val': self.parse_bool }
        })
