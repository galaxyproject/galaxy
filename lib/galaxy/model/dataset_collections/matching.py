from collections.abc import (
    Hashable,
    Iterable,
)
from dataclasses import dataclass
from typing import (
    Any,
    Optional,
)

from galaxy import exceptions
from galaxy.util import bunch
from .structure import (
    get_collection,
    get_structure,
    leaf,
)

CANNOT_MATCH_ERROR_MESSAGE = "Cannot match collection types."


@dataclass
class MatchingCollectionAxis:
    """One independently iterable dimension of an implicit map-over."""

    structure: Any
    axis_id: Hashable | None = None

    def coordinates(self):
        for coordinate_index, path in enumerate(self.structure.walk_coordinates()):
            yield path, coordinate_index


@dataclass
class MatchingCollectionBinding:
    """An input collection sliced by one or more ordered axes."""

    collection: Any
    axis_indices: tuple[int, ...]
    subcollection_type: Any = None


@dataclass
class MatchingCollectionCondition:
    """Condition values indexed over a specific ordered set of axes."""

    axis_indices: tuple[int, ...]
    values: list[bool | None]


class CollectionsToMatch:
    """Structure representing a set of collections that need to be matched up
    when running tools (possibly workflows in the future as well).
    """

    def __init__(self):
        self.collections = {}

    def add(self, input_name, hdca, subcollection_type=None, linked=True, axis_id=None):
        self.collections[input_name] = bunch.Bunch(
            hdca=hdca,
            subcollection_type=subcollection_type,
            linked=linked,
            axis_id=axis_id,
        )

    def has_collections(self):
        return len(self.collections) > 0

    def items(self):
        return self.collections.items()


class MatchingCollections:
    """Structure holding the result of matching a list of collections
    together. This class being different than the class above and being
    created in the DatasetCollectionManager layer may seem like
    overkill but I suspect in the future plugins will be subtypable for
    instance so matching collections will need to make heavy use of the
    dataset collection type registry managed by the dataset collections
    service - hence the complexity now.
    """

    def __init__(self):
        self.linked_structure = None
        self.unlinked_structures = []
        self.unlinked_collections = []
        self.collections = {}
        self.subcollection_types = {}
        self.action_tuples = {}
        self.mapping_axes: list[MatchingCollectionAxis] = []
        self.bindings: dict[str, MatchingCollectionBinding] = {}
        self.conditions: list[MatchingCollectionCondition] = []
        self._when_values = None

    def __attempt_add_to_linked_match(
        self, input_name, hdca, child_collection, collection_type_description, subcollection_type
    ):
        structure = get_structure(
            child_collection, collection_type_description, leaf_subcollection_type=subcollection_type
        )
        if not self.linked_structure:
            self.linked_structure = structure
            self.collections[input_name] = hdca
            self.subcollection_types[input_name] = subcollection_type
        else:
            if not self.linked_structure.compatible_shape(structure):
                raise exceptions.MessageException(CANNOT_MATCH_ERROR_MESSAGE)
            self.collections[input_name] = hdca
            self.subcollection_types[input_name] = subcollection_type

    def slice_collections(self):
        """Yield slices across every mapping axis in stable outer-to-inner order."""
        return self._slices()

    def _slices(self):
        axis_cardinalities = tuple(len(axis.structure) for axis in self.mapping_axes)
        for condition in self.conditions:
            condition_count = self._condition_coordinate_count(condition, axis_cardinalities)
            if len(condition.values) not in (1, condition_count):
                raise ValueError("Condition values do not match mapping coordinates")
        for coordinates in self._coordinate_product(0, []):
            coordinate_paths = [path for path, _ordinal in coordinates]
            sliced_collections = {
                input_name: self._slice_binding(binding, coordinate_paths)
                for input_name, binding in self.bindings.items()
            }
            coordinate_when_values = [
                self._condition_value(condition, coordinates, axis_cardinalities) for condition in self.conditions
            ]
            if any(when_value is False for when_value in coordinate_when_values):
                combined_when_value = False
            elif any(when_value is True for when_value in coordinate_when_values):
                combined_when_value = True
            else:
                combined_when_value = None
            yield sliced_collections, combined_when_value

    def _coordinate_product(self, axis_index, coordinates):
        if axis_index < len(self.mapping_axes):
            for coordinate in self.mapping_axes[axis_index].coordinates():
                yield from self._coordinate_product(axis_index + 1, [*coordinates, coordinate])
            return
        yield coordinates

    def _condition_value(self, condition, coordinates, axis_cardinalities):
        coordinate_index = 0
        for axis_index in condition.axis_indices:
            _path, axis_ordinal = coordinates[axis_index]
            coordinate_index *= axis_cardinalities[axis_index]
            coordinate_index += axis_ordinal
        values = condition.values
        if len(values) == 1:
            return values[0]
        return values[coordinate_index]

    @staticmethod
    def _condition_coordinate_count(condition, axis_cardinalities):
        count = 1
        for axis_index in condition.axis_indices:
            count *= axis_cardinalities[axis_index]
        return count

    @staticmethod
    def _slice_binding(binding, coordinate_paths):
        path = tuple(index for axis_index in binding.axis_indices for index in coordinate_paths[axis_index])
        collection = get_collection(binding.collection)
        element = None
        for depth, index in enumerate(path):
            element = collection[index]
            if depth < len(path) - 1:
                collection = element.child_collection
        return element

    @property
    def when_values(self):
        return self._when_values

    @when_values.setter
    def when_values(self, when_values):
        self._when_values = when_values
        self.conditions = [
            condition for condition in self.conditions if condition.axis_indices != tuple(range(len(self.mapping_axes)))
        ]
        if when_values:
            self.conditions.append(
                MatchingCollectionCondition(
                    axis_indices=tuple(range(len(self.mapping_axes))),
                    values=when_values,
                )
            )

    def subcollection_mapping_type(self, input_name):
        return self.subcollection_types[input_name]

    @property
    def structure(self):
        """Yield cross product of all unlinked collections structures to linked collection structure."""
        effective_structure = leaf
        for axis in self.mapping_axes:
            effective_structure = effective_structure.multiply(axis.structure)
        return None if effective_structure.is_leaf else effective_structure

    @classmethod
    def from_axes(
        cls,
        axes: Iterable[MatchingCollectionAxis],
        bindings: dict[str, MatchingCollectionBinding] | None = None,
        conditions: Iterable[MatchingCollectionCondition] | None = None,
    ) -> "MatchingCollections":
        matching_collections = cls()
        matching_collections.mapping_axes = list(axes)
        matching_collections.bindings = bindings or {}
        matching_collections.conditions = list(conditions or [])
        return matching_collections

    def with_inherited_mapping(self, inherited: "MatchingCollections") -> "MatchingCollections":
        """Compose local mapping with inherited axes without inheriting parent bindings."""
        axes = list(inherited.mapping_axes)
        local_axis_indices = {}
        for local_index, local_axis in enumerate(self.mapping_axes):
            combined_index = None
            if local_axis.axis_id is not None:
                for inherited_index, inherited_axis in enumerate(axes):
                    if local_axis.axis_id == inherited_axis.axis_id:
                        if not self._axes_have_compatible_shape(local_axis, inherited_axis):
                            raise exceptions.MessageException(CANNOT_MATCH_ERROR_MESSAGE)
                        combined_index = inherited_index
                        break
            if combined_index is None:
                combined_index = len(axes)
                axes.append(local_axis)
            local_axis_indices[local_index] = combined_index

        bindings = {
            name: MatchingCollectionBinding(
                collection=binding.collection,
                axis_indices=tuple(dict.fromkeys(local_axis_indices[index] for index in binding.axis_indices)),
                subcollection_type=binding.subcollection_type,
            )
            for name, binding in self.bindings.items()
        }
        conditions = list(inherited.conditions)
        conditions.extend(
            MatchingCollectionCondition(
                axis_indices=tuple(local_axis_indices[index] for index in condition.axis_indices),
                values=condition.values,
            )
            for condition in self.conditions
        )
        combined = self.from_axes(axes, bindings, conditions)
        combined.collections = self.collections.copy()
        combined.subcollection_types = self.subcollection_types.copy()
        return combined

    @staticmethod
    def _axes_have_compatible_shape(left, right):
        left_structure = left.structure
        right_structure = right.structure
        if left_structure.children_known and right_structure.children_known:
            return left_structure.compatible_shape(right_structure)
        return left_structure.collection_type_description.compatible(right_structure.collection_type_description)

    def map_over_action_tuples(self, input_name):
        if input_name not in self.action_tuples:
            collection_instance = self.collections[input_name]
            self.action_tuples[input_name] = get_collection(collection_instance).dataset_action_tuples
        return self.action_tuples[input_name]

    def is_mapped_over(self, input_name):
        return input_name in self.collections

    @staticmethod
    def for_collections(collections_to_match, collection_type_descriptions) -> Optional["MatchingCollections"]:
        if not collections_to_match.has_collections():
            return None

        matching_collections = MatchingCollections()
        unlinked_axes: list[MatchingCollectionAxis] = []
        unlinked_bindings: list[tuple[str, Any, Any]] = []
        linked_axis_id = None
        for input_key, to_match in sorted(collections_to_match.items()):
            hdca = to_match.hdca
            # Resolve the contained collection: for an HDCA this is
            # hdca.collection; for a DCE it is dce.child_collection
            # (not dce.collection which is the *parent*).
            # Both collection_type_description and get_structure must
            # use the same collection so the type and elements agree.
            child_collection = get_collection(hdca)
            collection_type_description = collection_type_descriptions.for_collection_type(
                child_collection.collection_type
            )
            subcollection_type = to_match.subcollection_type

            if to_match.linked:
                if to_match.axis_id is not None:
                    if linked_axis_id is not None and linked_axis_id != to_match.axis_id:
                        raise exceptions.MessageException(CANNOT_MATCH_ERROR_MESSAGE)
                    linked_axis_id = to_match.axis_id
                matching_collections.__attempt_add_to_linked_match(
                    input_key, hdca, child_collection, collection_type_description, subcollection_type
                )
            else:
                structure = get_structure(
                    child_collection,
                    collection_type_description,
                    leaf_subcollection_type=subcollection_type,
                )
                matching_collections.unlinked_structures.append(structure)
                matching_collections.unlinked_collections.append((input_key, hdca))
                unlinked_axes.append(
                    MatchingCollectionAxis(
                        structure=structure,
                        axis_id=to_match.axis_id,
                    )
                )
                unlinked_bindings.append((input_key, hdca, subcollection_type))

        matching_collections.mapping_axes.extend(unlinked_axes)
        for axis_index, (input_key, hdca, subcollection_type) in enumerate(unlinked_bindings):
            matching_collections.bindings[input_key] = MatchingCollectionBinding(
                collection=hdca,
                axis_indices=(axis_index,),
                subcollection_type=subcollection_type,
            )
        if matching_collections.linked_structure is not None:
            linked_axis_index = len(matching_collections.mapping_axes)
            matching_collections.mapping_axes.append(
                MatchingCollectionAxis(
                    structure=matching_collections.linked_structure,
                    axis_id=linked_axis_id,
                )
            )
            for input_key, hdca in matching_collections.collections.items():
                matching_collections.bindings[input_key] = MatchingCollectionBinding(
                    collection=hdca,
                    axis_indices=(linked_axis_index,),
                    subcollection_type=matching_collections.subcollection_types[input_key],
                )

        return matching_collections
