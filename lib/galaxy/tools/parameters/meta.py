import copy
import itertools
import logging

from galaxy import (
    exceptions,
    model,
    util
)
from galaxy.util import permutations

log = logging.getLogger( __name__ )


def expand_workflow_inputs( inputs ):
    """
    Expands incoming encoded multiple payloads, into the set of all individual payload combinations
    >>> params, param_keys = expand_workflow_inputs( {'1': {'input': {'batch': True, 'product': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}} )
    >>> print [ "%s" % ( p[ '1' ][ 'input' ][ 'hid' ] ) for p in params ]
    ['1', '2']
    >>> params, param_keys = expand_workflow_inputs( {'1': {'input': {'batch': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}} )
    >>> print [ "%s" % ( p[ '1' ][ 'input' ][ 'hid' ] ) for p in params ]
    ['1', '2']
    >>> params, param_keys = expand_workflow_inputs( {'1': {'input': {'batch': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}, '2': {'input': {'batch': True, 'values': [{'hid': '3'}, {'hid': '4'}] }}} )
    >>> print [ "%s%s" % ( p[ '1' ][ 'input' ][ 'hid' ], p[ '2' ][ 'input' ][ 'hid' ] ) for p in params ]
    ['13', '24']
    >>> params, param_keys = expand_workflow_inputs( {'1': {'input': {'batch': True, 'product': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}, '2': {'input': {'batch': True, 'values': [{'hid': '3'}, {'hid': '4'}, {'hid': '5'}] }}} )
    >>> print [ "%s%s" % ( p[ '1' ][ 'input' ][ 'hid' ], p[ '2' ][ 'input' ][ 'hid' ] ) for p in params ]
    ['13', '23', '14', '24', '15', '25']
    >>> params, param_keys = expand_workflow_inputs( {'1': {'input': {'batch': True, 'product': True, 'values': [{'hid': '1'}, {'hid': '2'}] }}, '2': {'input': {'batch': True, 'product': True, 'values': [{'hid': '3'}, {'hid': '4'}, {'hid': '5'}] }}, '3': {'input': {'batch': True, 'product': True, 'values': [{'hid': '6'}, {'hid': '7'}, {'hid': '8'}] }}} )
    >>> print [ "%s%s%s" % ( p[ '1' ][ 'input' ][ 'hid' ], p[ '2' ][ 'input' ][ 'hid' ], p[ '3' ][ 'input' ][ 'hid' ] ) for p in params ]
    ['136', '137', '138', '146', '147', '148', '156', '157', '158', '236', '237', '238', '246', '247', '248', '256', '257', '258']
    """
    linked_n = None
    linked = []
    product = []
    linked_keys = []
    product_keys = []
    for step_id, step in sorted( inputs.items() ):
        for key, value in sorted( step.items() ):
            if isinstance( value, dict ) and 'batch' in value and value[ 'batch' ] is True and 'values' in value and isinstance( value[ 'values' ], list ):
                nval = len( value[ 'values' ] )
                if 'product' in value and value[ 'product' ] is True:
                    product.append( value[ 'values' ] )
                    product_keys.append( ( step_id, key ) )
                else:
                    if linked_n is None:
                        linked_n = nval
                    elif linked_n != nval or nval is 0:
                        raise exceptions.RequestParameterInvalidException( 'Failed to match linked batch selections. Please select equal number of data files.' )
                    linked.append( value[ 'values' ] )
                    linked_keys.append( ( step_id, key ) )
    params = []
    params_keys = []
    linked = linked or [ [ None ] ]
    product = product or [ [ None ] ]
    linked_keys = linked_keys or [ ( None, None ) ]
    product_keys = product_keys or [ ( None, None ) ]
    for linked_values, product_values in itertools.product( zip( *linked ), itertools.product( *product ) ):
        new_params = copy.deepcopy( inputs )
        new_keys = []
        for ( step_id, key ), value in list(zip( linked_keys, linked_values )) + list(zip( product_keys, product_values )):
            if step_id is not None:
                new_params[ step_id ][ key ] = value
                new_keys.append( value[ 'hid' ] )
        params_keys.append( new_keys )
        params.append( new_params )
    return params, params_keys


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
