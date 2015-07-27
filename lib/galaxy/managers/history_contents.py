"""
Heterogenous lists/contents are difficult to query properly since unions are
not easily made.
"""

import operator

import pkg_resources
pkg_resources.require( "SQLAlchemy" )
from sqlalchemy import literal

from galaxy import model

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
    order_contents_on = operator.attrgetter( 'hid' )

    def __init__( self, app ):
        super( HistoryContentsManager, self ).__init__()
        self.app = app
        self.contained_manager = hdas.HDAManager( app )
        self.subcontainer_manager = collections.DatasetCollectionManager( app )

    def session( self ):
        return self.app.model.context

    # ---- interface
    def contents( self, container, filters=None, limit=None, offset=None, order_by=None, **kwargs ):
        """
        Returns both types of contents: filtered and in some order.
        """
        # WIP
        # TODO: this is undoubtedly better solved in the actual SQL layer
        # create a union of common columns for the subclasses ids which can be filtered/limited
        subclasses = ( self.contained_class, self.subcontainer_class )
        contents_query = None
        for subclass in subclasses:
            subquery = self._subclass_id_query( subclass, container.id )
            contents_query = subquery if contents_query is None else contents_query.union( subquery )

        # TODO: this needs the same fn/orm split that happens in the main query
        for orm_filter in ( filters or [] ):
            contents_query = contents_query.filter( orm_filter )

        if limit is not None:
            contents_query = contents_query.limit( limit )
        if offset is not None:
            contents_query = contents_query.offset( offset )
        # if order_by is not None:
        #     contents_query = contents_query.order_by( order_by )
        contents_results = contents_query.all()

        # build the id lists from the union query
        id_map = { subclass.__name__: [] for subclass in subclasses }
        TYPE_COLUMN = 2
        ID_COLUMN = 3
        for result in contents_results:
            result_type = str( result[ TYPE_COLUMN ] )
            if result_type == 'dataset':
                id_map[ self.contained_class.__name__ ].append( result[ ID_COLUMN ] )
            elif result_type == 'collection':
                id_map[ self.subcontainer_class.__name__ ].append( result[ ID_COLUMN ] )
            else:
                raise TypeError( 'Unknown contents type:', result_type )
        print id_map

        # query the contained classes using the id_lists for each
        for subclass in subclasses:
            id_list = id_map[ subclass.__name__ ]
            id_map[ subclass.__name__ ] = self._by_ids( subclass, id_list )

        # re-assemble in order
        contents = []
        # TODO: or as generator?
        for result in contents_results:
            result_type = str( result[ TYPE_COLUMN ] )
            if result_type == 'dataset':
                content = id_map[ self.contained_class.__name__ ][ result[ ID_COLUMN ] ]
                contents.append( content )
            elif result_type == 'collection':
                content = id_map[ self.subcontainer_class.__name__ ][ result[ ID_COLUMN ] ]
                contents.append( content )
            else:
                raise TypeError( 'Unknown contents type:', result_type )
        return contents

    def _subclass_id_query( self, subclass, history_id ):
        # TODO: find a better way to do this across the class
        type_keys = {
            self.contained_class.__name__ : 'dataset',
            self.subcontainer_class.__name__ : 'collection',
        }
        subquery = self.session().query(
            subclass.history_id,
            subclass.hid,
            literal( type_keys.get( subclass.__name__ ) ),
            subclass.id,
            subclass.name,
            subclass.deleted.label( 'deleted' ),
            # TODO: fix
            subclass.purged if subclass == self.contained_class else literal( False ),
            subclass.visible
        ).filter( subclass.history_id == history_id )
        return subquery

    def _by_ids( self, subclass, id_list ):
        if not id_list:
            return []
        query = self.session().query( subclass ).filter( subclass.id.in_( id_list ) )
        return { row.id: row for row in query.all() }

    # ---- interface
    def contained( self, container, **kwargs ):
        """
        Returns non-container objects.
        """
        return self._filter_contents( container, self.contained_class, **kwargs )

    def subcontainers( self, container, **kwargs ):
        """
        Returns only the containers within this one.
        """
        return self._filter_contents( container, self.subcontainer_class, **kwargs )

    # ---- private
    def _filter_contents( self, container, content_class, **kwargs ):
        # TODO: use list (or by_history etc.)
        container_filter = self._filter_to_contained( container, content_class )
        query = self.session().query( content_class ).filter( container_filter )
        return query

    def _filter_to_contained( self, container, content_class ):
        return content_class.history == container

    def _content_manager( self, content ):
        # type sniffing is inevitable
        if isinstance( content, model.HistoryDatasetAssociation ):
            return self.hda_manager
        elif isinstance( content, model.HistoryDatasetCollectionAssociation ):
            return self.hdca_manager
        raise TypeError( 'Unknown contents class: ' + str( content ) )
