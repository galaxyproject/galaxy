"""
Heterogenous lists/contents are difficult to query properly since unions are
not easily made.
"""

import pkg_resources
pkg_resources.require( "SQLAlchemy" )
from sqlalchemy import literal

from galaxy import model

from galaxy.managers import base
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
        filter_to_inside_container = self._filter_to_contained( container, self.contained_class )
        filters = base.munge_lists( filter_to_inside_container, filters )
        return self.contained_manager.list( filters=filters, limit=limit, offset=offset, order_by=order_by, **kwargs )

    def subcontainers( self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs ):
        """
        Returns only the containers within `container`.
        """
        filter_to_inside_container = self._filter_to_contained( container, self.subcontainer_class )
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

    # ---- private
    def session( self ):
        return self.app.model.context

    # not limited or offset contents query
    def _filter_to_contents_query( self, container, content_class, **kwargs ):
        # TODO: use list (or by_history etc.)
        container_filter = self._filter_to_contained( container, content_class )
        query = self.session().query( content_class ).filter( container_filter )
        return query

    def _filter_to_contained( self, container, content_class ):
        return content_class.history == container

    # limited and offset query
    def _union_of_contents( self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs ):
        """
        Returns a limited and offset list of both types of contents, filtered
        and in some order.
        """
        order_by = order_by or self.default_order_by
        order_by = order_by if isinstance( order_by, tuple ) else ( order_by, )

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
        get_unioned_typestr = lambda c: str( c[ 1 ] )
        get_unioned_id = lambda c: c[ 2 ]
        for result in contents_results:
            result_type = get_unioned_typestr( result )
            contents_id = get_unioned_id( result )
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
            result_type = get_unioned_typestr( result )
            contents_id = get_unioned_id( result )
            content = id_map[ result_type ][ contents_id ]
            contents.append( content )
        return contents

    common_columns = (
        "history_id",
        "model_class",
        "id",
        "collection_id",
        "hid",
        "name",
        "deleted",
        "purged",
        "visible",
        "create_time",
        "update_time",
    )

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
            # gen. do not have inner collections
            collection_id=literal( None )
        )
        return self.session().query( *columns ).filter( component_class.history_id == history_id )

    def _contents_common_query_for_subcontainer( self, history_id ):
        component_class = self.subcontainer_class
        columns = self._contents_common_columns( component_class,
            # TODO: should be purgable? fix
            purged=literal( False ),
            # these are attached instead to the inner collection
            create_time=model.DatasetCollection.create_time,
            update_time=model.DatasetCollection.update_time
        )
        subquery = self.session().query( *columns )
        # for the HDCA's we need to join the DatasetCollection since it has update/create times
        subquery = subquery.join( model.DatasetCollection,
            model.DatasetCollection.id == component_class.collection_id )
        subquery = subquery.filter( component_class.history_id == history_id )
        return subquery

    def _by_ids( self, component_class, id_list ):
        if not id_list:
            return []
        query = self.session().query( component_class ).filter( component_class.id.in_( id_list ) )
        return dict( ( row.id, row ) for row in query.all() )
