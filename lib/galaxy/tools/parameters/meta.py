from galaxy.util import permutations
from galaxy import model
from galaxy import util
from galaxy import exceptions

import logging
log = logging.getLogger( __name__ )


def expand_meta_parameters( trans, tool, incoming ):
    """
    Take in a dictionary of raw incoming parameters and expand to a list
    of expanded incoming parameters (one set of parameters per tool
    execution).
    """

    def classifier( input_key ):
        multirun_key = "%s|__multirun__" % input_key
        if multirun_key in incoming:
            multi_value = util.listify( incoming[ multirun_key ] )
            if len( multi_value ) > 1:
                return permutations.input_classification.MATCHED, multi_value
            else:
                if len( multi_value ) == 0:
                    multi_value = None
                return permutations.input_classification.SINGLE, multi_value[ 0 ]
        else:
            return permutations.input_classification.SINGLE, incoming[ input_key ]

    from galaxy.dataset_collections import matching
    collections_to_match = matching.CollectionsToMatch()

    def collection_classifier( input_key ):
        multirun_key = "%s|__collection_multirun__" % input_key
        if multirun_key in incoming:
            incoming_val = incoming[ multirun_key ]
            # If subcollectin multirun of data_collection param - value will
            # be "hdca_id|subcollection_type" else it will just be hdca_id
            if "|" in incoming_val:
                encoded_hdc_id, subcollection_type = incoming_val.split( "|", 1 )
            else:
                try:
                    src = incoming_val[ "src" ]
                    if src != "hdca":
                        raise exceptions.ToolMetaParameterException( "Invalid dataset collection source type %s" % src )
                    encoded_hdc_id = incoming_val[ "id" ]
                except TypeError:
                    encoded_hdc_id = incoming_val
                subcollection_type = None
            hdc_id = trans.app.security.decode_id( encoded_hdc_id )
            hdc = trans.sa_session.query( model.HistoryDatasetCollectionAssociation ).get( hdc_id )
            collections_to_match.add( input_key, hdc, subcollection_type=subcollection_type )
            if subcollection_type is not None:
                from galaxy.dataset_collections import subcollections
                subcollection_elements = subcollections.split_dataset_collection_instance( hdc, subcollection_type )
                return permutations.input_classification.MATCHED, subcollection_elements
            else:
                hdas = hdc.collection.dataset_instances
                return permutations.input_classification.MATCHED, hdas
        else:
            return permutations.input_classification.SINGLE, incoming[ input_key ]

    # Stick an unexpanded version of multirun keys so they can be replaced,
    # by expand_mult_inputs.
    incoming_template = incoming.copy()

    # Will reuse this in subsequent work, so design this way now...
    def try_replace_key( key, suffix ):
        found = key.endswith( suffix )
        if found:
            simple_key = key[ 0:-len( suffix ) ]
            if simple_key not in incoming_template:
                incoming_template[ simple_key ] = None
        return found

    multirun_found = False
    collection_multirun_found = False
    for key, value in incoming.iteritems():
        multirun_found = try_replace_key( key, "|__multirun__" ) or multirun_found
        collection_multirun_found = try_replace_key( key, "|__collection_multirun__" ) or collection_multirun_found

    if sum( [ 1 if f else 0 for f in [ multirun_found, collection_multirun_found ] ] ) > 1:
        # In theory doable, but to complicated for a first pass.
        message = "Cannot specify parallel execution across both multiple datasets and dataset collections."
        raise exceptions.ToolMetaParameterException( message )

    if multirun_found:
        return permutations.expand_multi_inputs( incoming_template, classifier ), None
    else:
        expanded_incomings = permutations.expand_multi_inputs( incoming_template, collection_classifier )
        if collections_to_match.has_collections():
            collection_info = trans.app.dataset_collections_service.match_collections( collections_to_match )
        else:
            collection_info = None
        return expanded_incomings, collection_info
