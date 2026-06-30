"""Collection type matching adapter for workflow connection validation.

Thin layer over galaxy.tool_util.collections that adds sentinel types
(NULL_COLLECTION_TYPE, ANY_COLLECTION_TYPE) and free functions for
connection validation (can_match, can_map_over, effective_map_over).

The base class methods (accepts, can_map_over, effective_collection_type)
do the real work — this module handles sentinel dispatch and the dataset
(non-collection) case.
"""

from galaxy.tool_util.collections import (
    COLLECTION_TYPE_DESCRIPTION_FACTORY,
    CollectionTypeDescription,
)


class _NullCollectionType:
    """Represents a plain dataset — not a collection."""

    is_collection = False
    collection_type = None
    rank = 0

    def __repr__(self):
        return "NULL_COLLECTION_TYPE"


class _AnyCollectionType:
    """Represents an unconstrained collection input (no collection_type declared)."""

    is_collection = True
    collection_type = "any"
    rank = -1

    def __repr__(self):
        return "ANY_COLLECTION_TYPE"


NULL_COLLECTION_TYPE = _NullCollectionType()
ANY_COLLECTION_TYPE = _AnyCollectionType()

CollectionTypeOrSentinel = CollectionTypeDescription | _NullCollectionType | _AnyCollectionType


def collection_type_rank(ctd: CollectionTypeDescription) -> int:
    """TS-compatible rank: 'list' = 1, 'list:paired' = 2."""
    return ctd.collection_type.count(":") + 1


def _split_collection_type(ctd: CollectionTypeDescription) -> list[CollectionTypeDescription]:
    """Split a comma-separated collection_type into individual types.

    Galaxy tool inputs can declare collection_type="list,list:paired" meaning
    the input accepts any of those types. This splits them for matching.
    """
    ct = ctd.collection_type
    if "," not in ct:
        return [ctd]
    return [COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(t.strip()) for t in ct.split(",")]


def can_match(
    output: CollectionTypeOrSentinel,
    input_type: CollectionTypeOrSentinel,
) -> bool:
    """Can output directly satisfy input (no mapping)?

    Convention: can_match(output, input) — wraps the asymmetric edge check
    input_type.accepts(output) with sentinel handling.
    """
    if output is NULL_COLLECTION_TYPE or input_type is NULL_COLLECTION_TYPE:
        return False
    if input_type is ANY_COLLECTION_TYPE:
        return output is not NULL_COLLECTION_TYPE
    if output is ANY_COLLECTION_TYPE:
        return False
    assert isinstance(input_type, CollectionTypeDescription)
    assert isinstance(output, CollectionTypeDescription)
    for variant in _split_collection_type(input_type):
        if variant.accepts(output):
            return True
    return False


def can_map_over(
    output: CollectionTypeOrSentinel,
    input_type: CollectionTypeOrSentinel,
) -> bool:
    """Can output be mapped over input?

    True when output contains subcollections matching input_type, meaning the
    step would execute once per outer element with each subcollection fed to
    the tool input.
    """
    if output is NULL_COLLECTION_TYPE or output is ANY_COLLECTION_TYPE:
        return False
    if input_type is ANY_COLLECTION_TYPE:
        return False
    assert isinstance(output, CollectionTypeDescription)
    if input_type is NULL_COLLECTION_TYPE:
        # Any collection can map over a plain dataset input
        return True
    assert isinstance(input_type, CollectionTypeDescription)
    for variant in _split_collection_type(input_type):
        if output.can_map_over(variant):
            return True
    return False


def compatible(
    a: CollectionTypeOrSentinel,
    b: CollectionTypeOrSentinel,
) -> bool:
    """Symmetric sibling-matching: do a and b match such that they could
    drive a common map-over over sibling inputs?

    Wraps the symmetric base method ``CollectionTypeDescription.compatible``
    with sentinel handling. Order of arguments must not change the answer.

    Used at sites resolving sibling map-over contributions where neither
    side is the input slot — pre-rebase code used asymmetric can_match here
    and produced order-dependent results.
    """
    if a is NULL_COLLECTION_TYPE and b is NULL_COLLECTION_TYPE:
        return True
    if a is NULL_COLLECTION_TYPE or b is NULL_COLLECTION_TYPE:
        return False
    if a is ANY_COLLECTION_TYPE or b is ANY_COLLECTION_TYPE:
        return True
    assert isinstance(a, CollectionTypeDescription)
    assert isinstance(b, CollectionTypeDescription)
    return a.compatible(b)


def is_list_like(ctd: CollectionTypeDescription) -> bool:
    """Is this a list-like collection type (eligible for multi-data reduction)?

    sample_sheet normalizes to list for matching purposes.
    """
    ct = ctd.collection_type
    if ct.startswith("sample_sheet"):
        ct = "list" + ct[len("sample_sheet") :]
    return ct == "list" or ct.startswith("list:")


def effective_map_over(
    output: CollectionTypeOrSentinel,
    input_type: CollectionTypeOrSentinel,
) -> CollectionTypeDescription | None:
    """Compute remainder collection type after mapping output over input.

    Returns the CollectionTypeDescription representing the implicit collection
    structure produced by mapping, or None if mapping is not possible.
    """
    if not can_map_over(output, input_type):
        return None
    assert isinstance(output, CollectionTypeDescription)
    if input_type is NULL_COLLECTION_TYPE:
        # Mapping over a dataset — full collection type is the map-over structure
        return COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(output.collection_type)
    assert isinstance(input_type, CollectionTypeDescription)
    # Find the matching variant for comma-separated types
    for variant in _split_collection_type(input_type):
        if output.can_map_over(variant):
            effective = output.effective_collection_type(variant)
            return COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(effective)
    return None
