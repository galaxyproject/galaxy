""" Module for reasoning about structure of and matching hierarchical collections of data.
"""
import logging
log = logging.getLogger( __name__ )

from .type_description import map_over_collection_type


class Leaf( object ):

    def __len__( self ):
        return 1

    @property
    def is_leaf( self ):
        return True

leaf = Leaf()


class Tree( object ):

    def __init__( self, dataset_collection, collection_type_description ):
        self.collection_type_description = collection_type_description
        children = []
        for element in dataset_collection.elements:
            if collection_type_description.has_subcollections():
                child_collection = element.child_collection
                subcollection_type_description = collection_type_description.subcollection_type_description()  # Type description of children
                children.append( ( element.element_identifier, Tree( child_collection, collection_type_description=subcollection_type_description )  ) )
            else:
                children.append( ( element.element_identifier, leaf ) )

        self.children = children

    def walk_collections( self, hdca_dict ):
        return self._walk_collections( dict_map( lambda hdca: hdca.collection, hdca_dict ) )

    def _walk_collections( self, collection_dict ):
        for index, ( identifier, substructure ) in enumerate( self.children ):
            def element( collection ):
                return collection[ index ]

            if substructure.is_leaf:
                yield dict_map( element, collection_dict )
            else:
                sub_collections = dict_map( lambda collection: element( collection ).child_collection, collection_dict )
                for element in substructure._walk_collections( sub_collections ):
                    yield element

    @property
    def is_leaf( self ):
        return False

    def can_match( self, other_structure ):
        if not self.collection_type_description.can_match_type( other_structure.collection_type_description ):
            return False

        if len( self.children ) != len( other_structure.children ):
            return False

        for my_child, other_child in zip( self.children, other_structure.children ):
            # At least one is nested collection...
            if my_child[ 1 ].is_leaf != other_child[ 1 ].is_leaf:
                return False

            if not my_child[ 1 ].is_leaf and not my_child[ 1 ].can_match( other_child[ 1 ]):
                return False

        return True

    def __len__( self ):
        return sum( [ len( c[ 1 ] ) for c in self.children ] )

    def element_identifiers_for_outputs( self, trans, outputs ):
        element_identifiers = []
        elements_collection_type = None
        for identifier, child in self.children:
            if isinstance( child, Tree ):
                child_identifiers = child.element_identifiers_for_outputs( trans, outputs[ 0:len( child ) ] )
                child_identifiers[ "name" ] = identifier
                element_identifiers.append( child_identifiers )
                elements_collection_type = child_identifiers[ "collection_type" ]
            else:
                output_object = outputs[ 0 ]
                element_identifiers.append( dict( name=identifier, __object__=output_object ) )
                if hasattr( output_object, "collection_type" ):
                    elements_collection_type = output_object.collection_type

            outputs = outputs[ len( child ): ]

        collection_type = map_over_collection_type( self.collection_type_description.rank_collection_type(), elements_collection_type )
        return dict(
            src="new_collection",
            collection_type=collection_type,
            element_identifiers=element_identifiers,
        )


def dict_map( func, input_dict ):
    return dict( [ ( k, func(v) ) for k, v in input_dict.iteritems() ] )


def get_structure( dataset_collection_instance, collection_type_description, leaf_subcollection_type=None ):
    if leaf_subcollection_type:
        collection_type_description = collection_type_description.effective_collection_type_description( leaf_subcollection_type )

    return Tree( dataset_collection_instance.collection, collection_type_description )
