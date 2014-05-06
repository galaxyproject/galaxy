from galaxy.util import permutations
from galaxy import model
from galaxy import util
from galaxy import exceptions


def expand_meta_parameters( trans, incoming, inputs ):
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
                return permutations.input_classification.MULTIPLIED, multi_value
            else:
                if len( multi_value ) == 0:
                    multi_value = None
                return permutations.input_classification.SINGLE, multi_value[ 0 ]
        else:
            return permutations.input_classification.SINGLE, incoming[ input_key ]

    def collection_classifier( input_key ):
        multirun_key = "%s|__collection_multirun__" % input_key
        if multirun_key in incoming:
            encoded_hdc_id = incoming[ multirun_key ]
            hdc_id = trans.app.security.decode_id( encoded_hdc_id )
            hdc = trans.sa_session.query( model.HistoryDatasetCollectionAssociation ).get( hdc_id )
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
        collection_multirun_found = try_replace_key( key, "|__collection_multirun__" )

    if multirun_found and collection_multirun_found:
        # In theory doable, but to complicated for a first pass.
        message = "Cannot specify parallel execution across both multiple datasets and dataset collections."
        raise exceptions.ToolMetaParameterException( message )

    if multirun_found:
        return permutations.expand_multi_inputs( incoming_template, classifier )
    else:
        return permutations.expand_multi_inputs( incoming_template, collection_classifier )
