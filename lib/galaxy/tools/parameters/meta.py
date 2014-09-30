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

    def classify_unmodified_parameter( input_key ):
        value = incoming[ input_key ]
        if isinstance( value, dict ) and 'values' in value:
            # Explicit meta wrapper for inputs...
            is_batch = value.get( 'batch', False )
            is_linked = value.get( 'linked', True )
            if is_batch and is_linked:
                classification = permutations.input_classification.MATCHED
            elif is_batch:
                classification = permutations.input_classification.MULTIPLIED
            else:
                classification = permutations.input_classification.SINGLE
            if __collection_multirun_parameter( value ):
                collection_value = value[ 'values' ][ 0 ]
                values = __expand_collection_parameter( trans, input_key, collection_value, collections_to_match )
            else:
                values = value[ 'values' ]
        else:
            classification = permutations.input_classification.SINGLE
            values = value
        return classification, values

    from galaxy.dataset_collections import matching
    collections_to_match = matching.CollectionsToMatch()

    def classifier( input_key ):
        collection_multirun_key = "%s|__collection_multirun__" % input_key
        multirun_key = "%s|__multirun__" % input_key
        if multirun_key in incoming:
            multi_value = util.listify( incoming[ multirun_key ] )
            if len( multi_value ) > 1:
                return permutations.input_classification.MATCHED, multi_value
            else:
                if len( multi_value ) == 0:
                    multi_value = None
                return permutations.input_classification.SINGLE, multi_value[ 0 ]
        elif collection_multirun_key in incoming:
            incoming_val = incoming[ collection_multirun_key ]
            values = __expand_collection_parameter( trans, input_key, incoming_val, collections_to_match )
            return permutations.input_classification.MATCHED, values
        else:
            return classify_unmodified_parameter( input_key )

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
        if isinstance( value, dict ) and 'values' in value:
            batch = value.get( 'batch', False )
            if batch:
                if __collection_multirun_parameter( value ):
                    collection_multirun_found = True
                else:
                    multirun_found = True
            else:
                continue
        else:
            # Old-style batching (remove someday? - pretty hacky and didn't live in API long)
            try_replace_key( key, "|__multirun__" ) or multirun_found
            try_replace_key( key, "|__collection_multirun__" ) or collection_multirun_found

    expanded_incomings = permutations.expand_multi_inputs( incoming_template, classifier )
    if collections_to_match.has_collections():
        collection_info = trans.app.dataset_collections_service.match_collections( collections_to_match )
    else:
        collection_info = None
    return expanded_incomings, collection_info


def __expand_collection_parameter( trans, input_key, incoming_val, collections_to_match ):
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
            subcollection_type = incoming_val.get( 'map_over_type', None )
        except TypeError:
            encoded_hdc_id = incoming_val
            subcollection_type = None
    hdc_id = trans.app.security.decode_id( encoded_hdc_id )
    hdc = trans.sa_session.query( model.HistoryDatasetCollectionAssociation ).get( hdc_id )
    collections_to_match.add( input_key, hdc, subcollection_type=subcollection_type )
    if subcollection_type is not None:
        from galaxy.dataset_collections import subcollections
        subcollection_elements = subcollections.split_dataset_collection_instance( hdc, subcollection_type )
        return subcollection_elements
    else:
        hdas = hdc.collection.dataset_instances
        return hdas


def __collection_multirun_parameter( value ):
    batch_values = util.listify( value[ 'values' ] )
    if len( batch_values ) == 1:
        batch_over = batch_values[ 0 ]
        if isinstance( batch_over, dict ) and ('src' in batch_over) and (batch_over[ 'src' ] == 'hdca'):
            return True
    return False
