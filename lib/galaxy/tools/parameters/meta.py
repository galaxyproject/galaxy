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

    to_remove = []
    for key in incoming.keys():
        if key.endswith("|__identifier__"):
            to_remove.append(key)
    for key in to_remove:
        incoming.pop(key)

    def classifier( input_key ):
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
                values = __expand_collection_parameter( trans, input_key, collection_value, collections_to_match, linked=is_linked )
            else:
                values = value[ 'values' ]
        else:
            classification = permutations.input_classification.SINGLE
            values = value
        return classification, values

    from galaxy.dataset_collections import matching
    collections_to_match = matching.CollectionsToMatch()

    # Stick an unexpanded version of multirun keys so they can be replaced,
    # by expand_mult_inputs.
    incoming_template = incoming.copy()

    expanded_incomings = permutations.expand_multi_inputs( incoming_template, classifier )
    if collections_to_match.has_collections():
        collection_info = trans.app.dataset_collections_service.match_collections( collections_to_match )
    else:
        collection_info = None
    return expanded_incomings, collection_info


def __expand_collection_parameter( trans, input_key, incoming_val, collections_to_match, linked=False ):
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
    collections_to_match.add( input_key, hdc, subcollection_type=subcollection_type, linked=linked )
    if subcollection_type is not None:
        from galaxy.dataset_collections import subcollections
        subcollection_elements = subcollections.split_dataset_collection_instance( hdc, subcollection_type )
        return subcollection_elements
    else:
        hdas = []
        for element in hdc.collection.dataset_elements:
            hda = element.dataset_instance
            hda.element_identifier = element.element_identifier
            hdas.append( hda )
        return hdas


def __collection_multirun_parameter( value ):
    is_batch = value.get( 'batch', False )
    if not is_batch:
        return False

    batch_values = util.listify( value[ 'values' ] )
    if len( batch_values ) == 1:
        batch_over = batch_values[ 0 ]
        if isinstance( batch_over, dict ) and ('src' in batch_over) and (batch_over[ 'src' ] == 'hdca'):
            return True
    return False
