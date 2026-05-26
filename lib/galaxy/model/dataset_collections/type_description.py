"""Collection type descriptions and the compatibility algebra.

Three operations on collection types, each answering a distinct question:

- ``accepts(other)``: asymmetric direct-edge check. True iff an output
  collection of type ``other`` can be connected to an input slot whose
  declared type is ``self``. Used at workflow-editor edge validation.
  Convention: ``input_type.accepts(output_type)``.
- ``compatible(other)``: symmetric sibling-matching check. True iff two
  collection types match such that they could drive a common map-over
  over sibling inputs of one tool. Used where neither side is the input
  and order of arrival must not change the answer.
- ``can_map_over(other)``: asymmetric nesting check. True iff ``self`` has
  proper subcollections of type ``other`` — i.e. ``self`` can be mapped
  over to feed a slot expecting ``other``. Convention:
  ``output_type.can_map_over(input_type)``.

The TypeScript equivalents live in
``client/src/components/Workflow/Editor/modules/collectionTypeDescription.ts``
and must stay in sync (``accepts`` / ``compatible`` / ``canMapOver``). See
``types/collection_semantics.yml`` "Type Compatibility Algebra" for the
lattice diagram and worked examples.
"""

import re
from typing import (
    Optional,
    TYPE_CHECKING,
    Union,
)

from galaxy.exceptions import RequestParameterInvalidException
from .registry import DATASET_COLLECTION_TYPES_REGISTRY

if TYPE_CHECKING:
    from galaxy.tool_util_models.tool_source import FieldDict


COLLECTION_TYPE_REGEX = re.compile(
    r"^((list|paired|paired_or_unpaired|record)(:(list|paired|paired_or_unpaired|record))*|sample_sheet|sample_sheet:paired|sample_sheet:record|sample_sheet:paired_or_unpaired)$"
)


class CollectionTypeDescriptionFactory:
    def __init__(self, type_registry=DATASET_COLLECTION_TYPES_REGISTRY):
        # taking in type_registry though not using it, because we will someday
        # I think.
        self.type_registry = type_registry

    def for_collection_type(self, collection_type, fields: Optional[Union[str, list["FieldDict"]]] = None):
        assert collection_type is not None
        return CollectionTypeDescription(collection_type, self, fields=fields)


class CollectionTypeDescription:
    """Abstraction over dataset collection type that ties together string
    representation in database/model with type registry.
    """

    collection_type: str

    def __init__(
        self,
        collection_type: Union[str, "CollectionTypeDescription"],
        collection_type_description_factory: CollectionTypeDescriptionFactory,
        fields: Optional[Union[str, list["FieldDict"]]] = None,
    ):
        if isinstance(collection_type, CollectionTypeDescription):
            self.collection_type = collection_type.collection_type
        else:
            self.collection_type = collection_type
        self.collection_type_description_factory = collection_type_description_factory
        self.fields = fields
        self.__has_subcollections = self.collection_type.find(":") > 0

    def child_collection_type(self):
        rank_collection_type = self.rank_collection_type()
        return self.collection_type[len(rank_collection_type) + 1 :]

    def child_collection_type_description(self):
        child_collection_type = self.child_collection_type()
        return self.collection_type_description_factory.for_collection_type(child_collection_type)

    def effective_collection_type_description(self, subcollection_type):
        effective_collection_type = self.effective_collection_type(subcollection_type)
        return self.collection_type_description_factory.for_collection_type(effective_collection_type)

    def effective_collection_type(self, subcollection_type):
        if hasattr(subcollection_type, "collection_type"):
            subcollection_type = subcollection_type.collection_type

        if not self.can_map_over(subcollection_type):
            raise ValueError(f"Cannot compute effective subcollection type of {subcollection_type} over {self}")

        if subcollection_type == "single_datasets":
            return self.collection_type

        normalized = _normalize_collection_type(self.collection_type)
        normalized_sub = _normalize_collection_type(subcollection_type)

        if subcollection_type == "paired_or_unpaired":
            if self.collection_type.endswith(":paired"):
                # paired_or_unpaired consumes the :paired suffix
                return self.collection_type[: -len(":paired")]
            elif normalized.endswith("list"):
                # paired_or_unpaired acts like single_datasets for collections
                # whose innermost type is list (each element wrapped as unpaired)
                return self.collection_type
            else:
                # strip last rank (paired_or_unpaired consumes it)
                return self.collection_type[: self.collection_type.rfind(":")]

        if normalized_sub.endswith(":paired_or_unpaired"):
            # Compound :paired_or_unpaired suffix — iterative peel-off matching
            # TS effectiveMapOver logic. Strip ranks from both sides, then
            # optionally strip one more if :paired was consumed.
            current = self.collection_type
            current_other = subcollection_type
            while ":" in current_other:
                current_other = current_other[: current_other.rfind(":")]
                current = current[: current.rfind(":")]
            if normalized.endswith(":paired"):
                current = current[: current.rfind(":")]
            return current

        return self.collection_type[: -(len(subcollection_type) + 1)]

    def can_map_over(self, other_collection_type) -> bool:
        """Asymmetric nesting check: can this collection be mapped over to
        feed an input requiring ``other_collection_type``?

        Convention: ``output.can_map_over(input)``. True iff ``self`` has
        proper subcollections matching ``other`` — a type is not considered
        to map over itself (that's a direct edge, handled by ``accepts``).

        Mirrors TypeScript ``CollectionTypeDescription.canMapOver``. Naming
        kept parallel across languages because both encode the same
        operational question at workflow-editor connection time.
        """
        if hasattr(other_collection_type, "collection_type"):
            other_collection_type = other_collection_type.collection_type
        # sample_sheet asymmetry: a sample_sheet input can only be fed by a
        # sample_sheet output (a plain-list output lacks the column metadata
        # the input expects). ``self`` is the output being mapped over;
        # ``other`` is the input collection type. Check before normalization
        # (which equates sample_sheet and list).
        # Duplicates the asymmetry encoded in ``accepts`` — load-bearing for
        # ``multiply`` / ``effective_collection_type`` map-over arithmetic.
        # Removing this guard is a separate refactor; see follow-up issue.
        if other_collection_type.startswith("sample_sheet") and not self.collection_type.startswith("sample_sheet"):
            return False
        collection_type = _normalize_collection_type(self.collection_type)
        other_collection_type = _normalize_collection_type(other_collection_type)
        if collection_type == other_collection_type:
            return False
        if collection_type.endswith(f":{other_collection_type}"):
            return True
        if other_collection_type == "paired_or_unpaired":
            # this can be thought of as a subcollection of anything except a pair
            # since it would match a pair exactly
            return collection_type != "paired"
        if other_collection_type.endswith(":paired_or_unpaired"):
            # Compound :paired_or_unpaired suffix — e.g. list:list can map over
            # list:paired_or_unpaired. Strip the :paired_or_unpaired to get the
            # required higher ranks, optionally strip :paired from self (since
            # paired_or_unpaired consumes paired), then check alignment.
            higher_ranks_required = other_collection_type[: other_collection_type.rfind(":")]
            if collection_type.endswith(":paired"):
                higher_ranks = collection_type[: collection_type.rfind(":")]
            else:
                higher_ranks = collection_type
            return higher_ranks.endswith(higher_ranks_required) and higher_ranks != higher_ranks_required
        if other_collection_type == "single_datasets":
            # effectively any collection has unpaired subcollections
            return True
        return False

    def accepts(self, other_collection_type) -> bool:
        """Asymmetric direct-edge check: does an input slot of type ``self``
        accept an output of type ``other_collection_type``?

        Convention: ``input_type.accepts(output_type)``. Used at
        workflow-editor edge validation. For sibling-matching (where
        neither side is the input slot), use ``compatible`` instead.

        See ``types/collection_semantics.yml`` "Type Compatibility Algebra".
        """
        if hasattr(other_collection_type, "collection_type"):
            other_collection_type = other_collection_type.collection_type
        # sample_sheet asymmetry: a sample_sheet input is only satisfied by a
        # sample_sheet output — a plain-list output lacks the column metadata
        # the sample_sheet input expects. Check before normalization (which
        # otherwise equates the two).
        if self.collection_type.startswith("sample_sheet") and not other_collection_type.startswith("sample_sheet"):
            return False
        collection_type = _normalize_collection_type(self.collection_type)
        other_collection_type = _normalize_collection_type(other_collection_type)
        if other_collection_type == collection_type:
            return True
        elif other_collection_type == "paired" and collection_type == "paired_or_unpaired":
            return True

        if collection_type.endswith(":paired_or_unpaired"):
            as_plain_list = collection_type[: -len(":paired_or_unpaired")]
            if other_collection_type == as_plain_list:
                return True
            as_paired_list = f"{as_plain_list}:paired"
            if other_collection_type == as_paired_list:
                return True

        return False

    def compatible(self, other_collection_type) -> bool:
        """Symmetric sibling-matching check: do ``self`` and ``other`` match
        such that they could drive a common map-over over sibling inputs of
        a single tool?

        Implemented as ``self.accepts(other) or other.accepts(self)``. Used
        at sibling-matching sites (Python ``Tree.compatible_shape`` at
        runtime; TS ``mappingConstraints`` at connection time) where
        neither side is the input slot and order of arrival should not
        change the answer.

        See ``types/collection_semantics.yml`` "Type Compatibility Algebra".
        """
        if not hasattr(other_collection_type, "collection_type"):
            other_collection_type = self.collection_type_description_factory.for_collection_type(other_collection_type)
        return self.accepts(other_collection_type) or other_collection_type.accepts(self)

    def subcollection_type_description(self):
        if not self.__has_subcollections:
            raise ValueError(f"Cannot generate subcollection type description for flat type {self.collection_type}")
        subcollection_type = self.collection_type.split(":", 1)[1]
        return self.collection_type_description_factory.for_collection_type(subcollection_type)

    def has_subcollections(self):
        return self.__has_subcollections

    def rank_collection_type(self):
        """Return the top-level collection type corresponding to this
        collection type. For instance the "rank" type of a list of paired
        data ("list:paired") is "list".
        """
        return self.collection_type.split(":")[0]

    def rank_type_plugin(self):
        return self.collection_type_description_factory.type_registry.get(self.rank_collection_type())

    @property
    def dimension(self):
        return len(self.collection_type.split(":")) + 1

    def multiply(self, other_collection_type):
        collection_type = map_over_collection_type(self, other_collection_type)
        return self.collection_type_description_factory.for_collection_type(collection_type)

    def __str__(self):
        return f"CollectionTypeDescription[{self.collection_type}]"

    def validate(self):
        """Validate that this collection type is a valid Galaxy collection type."""
        if COLLECTION_TYPE_REGEX.match(self.collection_type) is None:
            raise RequestParameterInvalidException(f"Invalid collection type: [{self.collection_type}]")


def map_over_collection_type(mapped_over_collection_type, target_collection_type):
    if hasattr(mapped_over_collection_type, "collection_type"):
        mapped_over_collection_type = mapped_over_collection_type.collection_type

    if not target_collection_type:
        return mapped_over_collection_type
    else:
        if hasattr(target_collection_type, "collection_type"):
            target_collection_type = target_collection_type.collection_type

        return f"{mapped_over_collection_type}:{target_collection_type}"


def _normalize_collection_type(collection_type: str) -> str:
    """Normalize collection type for comparison purposes.

    sample_sheet behaves like list for mapping/matching.
    """
    if collection_type.startswith("sample_sheet"):
        return "list" + collection_type[len("sample_sheet") :]
    return collection_type


COLLECTION_TYPE_DESCRIPTION_FACTORY = CollectionTypeDescriptionFactory()
