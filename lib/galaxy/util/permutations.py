""" There is some shared logic between matching/multiplying inputs in workflows
and tools. This module is meant to capture some general permutation logic that
can be applicable for both cases but will only be used in the newer tools case
first.

Maybe this doesn't make sense and maybe much of this stuff could be replaced
with itertools product and permutations. These are open questions.
"""
from galaxy.exceptions import MessageException
from galaxy.util.bunch import Bunch

input_classification = Bunch(
    SINGLE="single",
    MATCHED="matched",
    MULTIPLIED="multiplied",
)


class InputMatchedException( MessageException ):
    """ Indicates problem matching inputs while building up inputs
    permutations. """


def expand_multi_inputs( inputs, classifier, key_filter=None ):
    key_filter = key_filter or ( lambda x: True )

    single_inputs, matched_multi_inputs, multiplied_multi_inputs = __split_inputs(
        inputs,
        classifier,
        key_filter
    )

    # Build up every combination of inputs to be run together.
    input_combos = __extend_with_matched_combos( single_inputs, matched_multi_inputs )
    input_combos = __extend_with_multiplied_combos( input_combos, multiplied_multi_inputs )

    return input_combos


def __split_inputs( inputs, classifier, key_filter ):
    key_filter = key_filter or ( lambda x: True )
    input_keys = filter( key_filter, inputs )

    single_inputs = {}
    matched_multi_inputs = {}
    multiplied_multi_inputs = {}

    for input_key in input_keys:
        input_type, expanded_val = classifier( input_key )
        if input_type == input_classification.SINGLE:
            single_inputs[ input_key ] = expanded_val
        elif input_type == input_classification.MATCHED:
            matched_multi_inputs[ input_key ] = expanded_val
        elif input_type == input_classification.MULTIPLIED:
            multiplied_multi_inputs[ input_key ] = expanded_val

    return ( single_inputs, matched_multi_inputs, multiplied_multi_inputs )


def __extend_with_matched_combos( single_inputs, multi_inputs ):
    """

    {a => 1, b => 2} and {c => {3, 4}, d => {5, 6}}

    Becomes

    [ {a => 1, b => 2, c => 3, d => 5}, {a => 1, b => 2, c => 4, d => 6}, ]

    """

    if len( multi_inputs ) == 0:
        return [ single_inputs ]

    matched_multi_inputs = []

    first_multi_input_key = multi_inputs.keys()[ 0 ]
    first_multi_value = multi_inputs.get(first_multi_input_key)

    for value in first_multi_value:
        new_inputs = __copy_and_extend_inputs( single_inputs, first_multi_input_key, value )
        matched_multi_inputs.append( new_inputs )

    for multi_input_key, multi_input_values in multi_inputs.iteritems():
        if multi_input_key == first_multi_input_key:
            continue
        if len( multi_input_values ) != len( first_multi_value ):
            raise InputMatchedException()

        for index, value in enumerate( multi_input_values ):
            matched_multi_inputs[ index ][ multi_input_key ] = value

    return matched_multi_inputs


def __extend_with_multiplied_combos( input_combos, multi_inputs ):
    combos = input_combos

    for multi_input_key, multi_input_value in multi_inputs.iteritems():
        iter_combos = []

        for combo in combos:
            for input_value in multi_input_value:
                iter_combo = __copy_and_extend_inputs( combo, multi_input_key, input_value )
                iter_combos.append( iter_combo )

        combos = iter_combos

    return combos


def __copy_and_extend_inputs( inputs, key, value ):
    new_inputs = dict( inputs )
    new_inputs[ key ] = value
    return new_inputs
