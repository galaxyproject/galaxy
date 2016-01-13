"""
Heterogenous lists/contents are difficult to query properly since unions are
not easily made.
"""

import operator

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

        # query 1: create a union of common columns for which the subclasses can be filtered/limited
        subclasses = ( self.contained_class, self.subcontainer_class )
        contents_query = None
        for subclass in subclasses:
            subquery = self._contents_common_query( subclass, container.id )
            contents_query = subquery if contents_query is None else contents_query.union( subquery )

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

        # partition ids into a map of { subclass names -> list of ids } from the above union query
        id_map = { subclass.__name__: [] for subclass in subclasses }
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

        # query 2 & 3: use the ids to query each subclass
        # query the contained classes using the id_lists for each
        for subclass in subclasses:
            id_list = id_map[ subclass.__name__ ]
            id_map[ subclass.__name__ ] = self._by_ids( subclass, id_list )
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

    def _contents_common_query( self, subclass, history_id ):
        if subclass == self.contained_class:
            return ( self.session().query( *self._common_columns_in_contained() )
                                   .filter( subclass.history_id == history_id ) )

        # for the HDCA's we need to join the DatasetCollection since it has update/create times
        subquery = self.session().query( *self._common_columns_in_subcontainer() )
        subquery = subquery.join( model.DatasetCollection,
            model.DatasetCollection.id == self.subcontainer_class.collection_id )
        subquery = subquery.filter( subclass.history_id == history_id )
        # print subquery
        return subquery

    def _common_columns_in_contained( self ):
        subclass = self.contained_class
        return (
            # container (history_id), type, id
            subclass.history_id,
            literal( subclass.__name__ ),
            subclass.id,
            # no collection id for nonsubcontainers
            literal( None ),

            # all the common columns that can be filtered/ordered by
            subclass.hid.label( 'hid' ),
            subclass.name,
            subclass.deleted.label( 'deleted' ),
            # TODO: fix
            subclass.purged,
            subclass.visible,
            subclass.create_time,
            subclass.update_time
        )

    def _common_columns_in_subcontainer( self ):
        subclass = self.subcontainer_class
        return (
            # container (history_id), type, id
            subclass.history_id,
            literal( subclass.__name__ ),
            subclass.id,
            subclass.collection_id,

            # all the common columns that can be filtered/ordered by
            subclass.hid.label( 'hid' ),
            subclass.name,
            subclass.deleted.label( 'deleted' ),
            # TODO: should be purgable right? fix
            literal( False ),
            subclass.visible,
            # join is necessary for this to work
            model.DatasetCollection.create_time,
            model.DatasetCollection.update_time
        )

    def _by_ids( self, subclass, id_list ):
        if not id_list:
            return []
        query = self.session().query( subclass ).filter( subclass.id.in_( id_list ) )
        return { row.id: row for row in query.all() }
