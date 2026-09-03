"""Plan implicit map-over of workflow steps across collections.

When a step's data inputs are connected to collections with deeper structure
than the input consumes, Galaxy runs the step once per matching coordinate and
collects the results - the step is "mapped over" its inputs.
``MapOverPlanner.plan_map_over`` builds that plan for one step: the
resulting ``MatchingCollections`` (called ``collection_info`` throughout the
workflow run code) records how each input is sliced.
"""

from typing import TYPE_CHECKING

from galaxy import (
    exceptions,
    model,
)
from galaxy.model.dataset_collections import matching
from galaxy.model.dataset_collections.query import HistoryQuery
from galaxy.model.dataset_collections.structure import (
    Tree,
    UninitializedTree,
)

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesHistoryContext
    from galaxy.model import WorkflowStep
    from galaxy.workflow.modules import InputDescription
    from galaxy.workflow.run import WorkflowProgress


class MapOverPlanner:
    """Build the map-over plan for one workflow step (see module docstring)."""

    def __init__(self, trans: "ProvidesHistoryContext"):
        self.trans = trans

    def plan_map_over(
        self, progress: "WorkflowProgress", step: "WorkflowStep", all_inputs: "list[InputDescription]"
    ) -> matching.MatchingCollections | None:
        """Build the map-over plan for one workflow step.

        ``all_inputs`` holds the step's input descriptions as produced by
        ``WorkflowModule.get_all_inputs``. Falls back to the plan inherited
        from a mapped-over subworkflow invocation when the step adds no
        mapping of its own.
        """
        collections_to_match = self._find_collections_to_match(progress, step, all_inputs)
        inherited_bindings, axis_refinements = self._extract_inherited_axis_bindings(
            progress, step, collections_to_match
        )
        direct_linked_input_names = [
            input_name for input_name, to_match in collections_to_match.items() if to_match.linked
        ]
        residual_binding_names = [
            input_name
            for input_name, (
                _to_match,
                _inherited_axes,
                residual_axes,
                _inherited_path_ranks,
            ) in inherited_bindings.items()
            if residual_axes
        ]
        linked_axis_id = self._assign_linked_axis_identity(
            progress,
            step,
            collections_to_match,
            residual_binding_names,
        )
        collection_info = self.trans.app.dataset_collection_manager.match_collections(collections_to_match)
        collection_info = self._add_residual_linked_axis(
            collection_info,
            inherited_bindings,
            linked_axis_id,
            direct_linked_input_names,
        )
        inherited_collection_info = progress.subworkflow_collection_info
        if inherited_collection_info or inherited_bindings:
            if inherited_collection_info:
                context = inherited_collection_info.without_bindings()
            else:
                context = matching.MatchingCollections.from_axes([])
            for axis_id, refined_axis in axis_refinements.items():
                context = context.refine_axis(
                    axis_id,
                    refined_axis.structure,
                    axis_components=refined_axis.axis_components,
                )
            if collection_info:
                collection_info = collection_info.with_inherited_mapping(context)
            else:
                collection_info = context
            for input_name, (
                to_match,
                inherited_axes,
                residual_axes,
                inherited_path_slices,
            ) in inherited_bindings.items():
                axis_indices = tuple(self._axis_index(collection_info, axis) for axis in inherited_axes)
                axis_path_slices = inherited_path_slices
                if residual_axes:
                    axis_indices += (self._axis_index_for_id(collection_info, linked_axis_id),)
                    residual_path_rank = sum(self._axis_rank(axis) for axis in residual_axes)
                    axis_path_slices += ((0, residual_path_rank),)
                collection_info.bindings[input_name] = matching.MatchingCollectionBinding(
                    collection=to_match.hdca,
                    axis_indices=axis_indices,
                    subcollection_type=to_match.subcollection_type,
                    axis_path_slices=axis_path_slices,
                )
                collection_info.collections[input_name] = to_match.hdca
                collection_info.subcollection_types[input_name] = to_match.subcollection_type
        elif collection_info:
            # The invocation is not mapped over, but it might still be conditional.
            collection_info.when_values = progress.when_values
        return collection_info

    @staticmethod
    def _add_residual_linked_axis(
        collection_info,
        inherited_bindings,
        linked_axis_id,
        direct_linked_input_names,
    ):
        residual_structures = []
        for input_name, (
            _to_match,
            _inherited_axes,
            residual_axes,
            _inherited_path_ranks,
        ) in inherited_bindings.items():
            if residual_axes:
                structure = matching.leaf
                for axis in residual_axes:
                    structure = structure.multiply(axis.structure)
                residual_axis = matching.MatchingCollectionAxis(
                    structure,
                    linked_axis_id,
                    MapOverPlanner._combined_axis_components(residual_axes),
                )
                residual_structures.append((input_name, residual_axis))
        if not residual_structures:
            return collection_info

        linked_structure = collection_info.linked_structure if collection_info else None
        structure_candidates = list(residual_structures)
        if linked_structure:
            linked_axis = next(axis for axis in collection_info.mapping_axes if axis.axis_id == linked_axis_id)
            structure_candidates.append((min(direct_linked_input_names), linked_axis))
        _reference_name, selected_axis = min(
            structure_candidates,
            key=lambda item: (
                -MapOverPlanner._axis_rank(item[1]),
                not item[1].structure.children_known,
                item[0],
            ),
        )
        reference_structure = selected_axis.structure
        reference_axis = selected_axis
        reference_components = list(selected_axis.components())
        for _input_name, candidate_axis in structure_candidates:
            if not matching.MatchingCollections._axes_have_compatible_or_refined_shape(reference_axis, candidate_axis):
                raise exceptions.MessageException(matching.CANNOT_MATCH_ERROR_MESSAGE)
            reference_components.extend(candidate_axis.components())
        reference_components.append((linked_axis_id, 0, MapOverPlanner._structure_rank(reference_structure)))
        reference_axis = matching.MatchingCollectionAxis(
            reference_structure,
            linked_axis_id,
            tuple(dict.fromkeys(reference_components)),
        )

        if (
            collection_info
            and linked_structure
            and MapOverPlanner._structure_rank(reference_structure) > MapOverPlanner._structure_rank(linked_structure)
        ):
            linked_axis_index = MapOverPlanner._axis_index_for_id(collection_info, linked_axis_id)
            linked_path_rank = MapOverPlanner._structure_rank(linked_structure)
            for binding in collection_info.bindings.values():
                if linked_axis_index in binding.axis_indices:
                    path_slices = list(binding.axis_path_slices or ((0, None),) * len(binding.axis_indices))
                    binding_axis_index = binding.axis_indices.index(linked_axis_index)
                    path_slices[binding_axis_index] = (0, linked_path_rank)
                    binding.axis_path_slices = tuple(path_slices)

        if collection_info is None:
            collection_info = matching.MatchingCollections.from_axes([reference_axis])
            collection_info.linked_structure = reference_structure
        elif linked_structure is None:
            collection_info.mapping_axes.append(reference_axis)
            collection_info.linked_structure = reference_structure
        else:
            collection_info.linked_structure = reference_structure
            for axis_index, axis in enumerate(collection_info.mapping_axes):
                if axis.axis_id == linked_axis_id:
                    collection_info.mapping_axes[axis_index] = reference_axis
                    break
        return collection_info

    @staticmethod
    def _axis_index(collection_info, axis):
        for axis_index, candidate in enumerate(collection_info.mapping_axes):
            if axis.axis_id is not None and axis.axis_id == candidate.axis_id:
                return axis_index
            if axis is candidate:
                return axis_index
        raise exceptions.MessageException(matching.CANNOT_MATCH_ERROR_MESSAGE)

    @staticmethod
    def _axis_index_for_id(collection_info, axis_id):
        for axis_index, candidate in enumerate(collection_info.mapping_axes):
            if candidate.axis_id == axis_id:
                return axis_index
        raise exceptions.MessageException(matching.CANNOT_MATCH_ERROR_MESSAGE)

    def _extract_inherited_axis_bindings(self, progress, step, collections_to_match):
        inherited_collection_info = progress.subworkflow_collection_info
        if not inherited_collection_info:
            return {}, {}
        inherited_axes_by_id = {axis.axis_id: axis for axis in inherited_collection_info.mapping_axes}
        source_axes_by_input = {
            input_name: self._source_mapping_axes(progress, step, input_name)
            for input_name, _to_match in collections_to_match.items()
        }
        inherited_binding_names = {
            input_name
            for input_name, axes in source_axes_by_input.items()
            if any(axis.axis_id in inherited_axes_by_id for axis in axes)
        }
        has_direct_linked_peer = any(
            input_name not in inherited_binding_names and to_match.linked
            for input_name, to_match in collections_to_match.items()
        )
        inherited_bindings = {}
        axis_refinements = {}
        embedded_direct_axes = []
        for input_name, to_match in list(collections_to_match.items()):
            axes = source_axes_by_input[input_name]
            if input_name in inherited_binding_names:
                collections_to_match.pop(input_name)
                inherited_axes = tuple(axis for axis in axes if axis.axis_id in inherited_axes_by_id)
                mapping_structure = self._mapping_structure(to_match)
                mapping_rank = self._structure_rank(mapping_structure)
                inherited_path_ranks = []
                remaining_mapping_rank = mapping_rank
                for source_axis in inherited_axes:
                    context_axis = inherited_axes_by_id[source_axis.axis_id]
                    source_rank = self._axis_rank(source_axis)
                    context_rank = self._axis_rank(context_axis)
                    if source_rank > context_rank:
                        self._record_axis_refinement(
                            axis_refinements,
                            source_axis.axis_id,
                            source_axis.structure,
                            source_axis.components(),
                        )
                    consumed_rank = min(source_rank, remaining_mapping_rank)
                    inherited_path_ranks.append(consumed_rank)
                    remaining_mapping_rank -= consumed_rank
                inherited_rank = sum(inherited_path_ranks)
                residual_rank = max(0, mapping_rank - inherited_rank)
                residual_axes = self._take_axis_prefix(
                    (axis for axis in axes if axis.axis_id not in inherited_axes_by_id),
                    residual_rank,
                )
                covered_residual_rank = sum(self._axis_rank(axis) for axis in residual_axes)
                missing_residual_rank = residual_rank - covered_residual_rank
                if missing_residual_rank:
                    # A collection materialized by a mapped step can reveal a
                    # deeper, branch-dependent shape for the inherited axis.
                    # Keep that entire tree as one axis: splitting off a
                    # synthetic suffix would incorrectly require every outer
                    # branch to have the same shape and identifiers.
                    residual_structure = None
                    if len(inherited_axes) == 1 and residual_axes:
                        try:
                            residual_structure = self._structure_suffix(mapping_structure, inherited_rank)
                        except exceptions.MessageException:
                            pass
                    if len(inherited_axes) == 1 and (
                        (not residual_axes and not has_direct_linked_peer)
                        or (residual_axes and residual_structure is None)
                    ):
                        inherited_axis = inherited_axes[0]
                        if residual_axes:
                            axis_components = self._combined_axis_components((*inherited_axes, *residual_axes))
                            embedded_direct_axes.append((inherited_axis, residual_axes))
                        else:
                            axis_components = inherited_axis.components()
                        self._record_axis_refinement(
                            axis_refinements,
                            inherited_axis.axis_id,
                            mapping_structure,
                            axis_components,
                        )
                        inherited_path_ranks[0] = mapping_rank
                        residual_axes = ()
                    elif len(inherited_axes) == 1 and not has_direct_linked_peer and residual_structure is not None:
                        residual_axes = (matching.MatchingCollectionAxis(residual_structure, residual_axes[0].axis_id),)
                    else:
                        suffix_structure = self._structure_suffix(
                            mapping_structure,
                            inherited_rank + covered_residual_rank,
                        )
                        suffix_rank = self._structure_rank(suffix_structure)
                        suffix_axis = matching.MatchingCollectionAxis(
                            suffix_structure,
                            (
                                "consumer-residual",
                                tuple(axis.axis_id for axis in axes),
                                covered_residual_rank,
                            ),
                        )
                        if suffix_rank > missing_residual_rank:
                            suffix_axis = self._truncate_axis(suffix_axis, missing_residual_rank)
                        residual_axes += (suffix_axis,)
                inherited_bindings[input_name] = (
                    to_match,
                    inherited_axes,
                    residual_axes,
                    tuple((0, rank) for rank in inherited_path_ranks),
                )
        self._promote_embedded_residual_axes(inherited_bindings, axis_refinements)
        self._promote_direct_linked_bindings(
            collections_to_match,
            inherited_bindings,
            axis_refinements,
            embedded_direct_axes,
        )
        return inherited_bindings, axis_refinements

    @staticmethod
    def _axis_rank(axis):
        return MapOverPlanner._structure_rank(axis.structure)

    @staticmethod
    def _structure_rank(structure):
        return len(structure.collection_type_description.collection_type.split(":"))

    @classmethod
    def _record_axis_refinement(cls, refinements, axis_id, structure, axis_components=None):
        candidate = matching.MatchingCollectionAxis(structure, axis_id, axis_components)
        existing = refinements.get(axis_id)
        if existing is None:
            refinements[axis_id] = candidate
            return
        existing_rank = cls._axis_rank(existing)
        candidate_rank = cls._structure_rank(structure)
        if existing_rank == candidate_rank:
            if not matching.MatchingCollections._axes_have_compatible_shape(
                existing,
                candidate,
            ):
                raise exceptions.MessageException(matching.CANNOT_MATCH_ERROR_MESSAGE)
            merged_components = tuple(dict.fromkeys((*existing.components(), *candidate.components())))
            refinements[axis_id] = matching.MatchingCollectionAxis(
                existing.structure,
                axis_id,
                merged_components,
            )
        elif existing_rank < candidate_rank:
            matching.MatchingCollections.from_axes([existing]).refine_axis(axis_id, structure)
            refinements[axis_id] = candidate
        else:
            matching.MatchingCollections.from_axes([candidate]).refine_axis(axis_id, existing.structure)

    @classmethod
    def _combined_axis_components(cls, axes):
        components = []
        offset = 0
        for axis in axes:
            components.extend(
                (component_id, offset + start, offset + stop) for component_id, start, stop in axis.components()
            )
            offset += cls._axis_rank(axis)
        return tuple(components)

    @staticmethod
    def _promote_embedded_residual_axes(inherited_bindings, axis_refinements):
        for input_name, (to_match, inherited_axes, residual_axes, inherited_path_slices) in list(
            inherited_bindings.items()
        ):
            remaining_residual_axes = []
            inherited_axes = list(inherited_axes)
            inherited_path_slices = list(inherited_path_slices)
            for residual_axis in residual_axes:
                promoted = False
                for inherited_axis in tuple(inherited_axes):
                    refined_axis = axis_refinements.get(inherited_axis.axis_id)
                    component_slice = refined_axis and refined_axis.component_path_slice(residual_axis.axis_id)
                    if component_slice:
                        inherited_axes.append(inherited_axis)
                        inherited_path_slices.append(component_slice)
                        promoted = True
                        break
                if not promoted:
                    remaining_residual_axes.append(residual_axis)
            inherited_bindings[input_name] = (
                to_match,
                tuple(inherited_axes),
                tuple(remaining_residual_axes),
                tuple(inherited_path_slices),
            )

    def _promote_direct_linked_bindings(
        self,
        collections_to_match,
        inherited_bindings,
        axis_refinements,
        embedded_direct_axes,
    ):
        if not embedded_direct_axes:
            return
        for input_name, to_match in list(collections_to_match.items()):
            if not to_match.linked:
                continue
            direct_axis = matching.MatchingCollectionAxis(self._mapping_structure(to_match))
            direct_rank = self._axis_rank(direct_axis)
            candidates = {}
            for inherited_axis, residual_axes in embedded_direct_axes:
                refined_axis = axis_refinements[inherited_axis.axis_id]
                for residual_axis in residual_axes:
                    component_slice = refined_axis.component_path_slice(residual_axis.axis_id)
                    residual_rank = self._axis_rank(residual_axis)
                    if (
                        component_slice
                        and direct_rank <= residual_rank
                        and matching.MatchingCollections._axes_have_compatible_or_refined_shape(
                            direct_axis, residual_axis
                        )
                    ):
                        direct_slice = (component_slice[0], component_slice[0] + direct_rank)
                        candidates[(inherited_axis.axis_id, direct_slice)] = inherited_axis
            if len(candidates) != 1:
                raise exceptions.MessageException(matching.CANNOT_MATCH_ERROR_MESSAGE)
            (axis_id, component_slice), inherited_axis = next(iter(candidates.items()))
            assert inherited_axis.axis_id == axis_id
            collections_to_match.pop(input_name)
            inherited_bindings[input_name] = (
                to_match,
                (inherited_axis,),
                (),
                (component_slice,),
            )

    def _structure_suffix(self, structure, prefix_rank):
        if prefix_rank == 0:
            return structure
        collection_types = structure.collection_type_description.collection_type.split(":")[prefix_rank:]
        type_description = self.trans.app.dataset_collection_manager.collection_type_descriptions.for_collection_type(
            ":".join(collection_types)
        )
        if not structure.children_known:
            return UninitializedTree(type_description)

        candidates = [structure]
        for _depth in range(prefix_rank):
            next_candidates = []
            for candidate in candidates:
                for _identifier, child in candidate.children:
                    if child.is_leaf:
                        raise exceptions.MessageException(matching.CANNOT_MATCH_ERROR_MESSAGE)
                    next_candidates.append(child)
            candidates = next_candidates
        if not candidates:
            return UninitializedTree(type_description)
        reference = candidates[0]
        for candidate in candidates[1:]:
            if not reference.compatible_shape(candidate) or not self._structures_have_same_identifiers(
                reference, candidate
            ):
                raise exceptions.MessageException(matching.CANNOT_MATCH_ERROR_MESSAGE)
        return reference

    @classmethod
    def _structures_have_same_identifiers(cls, left, right):
        if left.is_leaf or right.is_leaf:
            return left.is_leaf and right.is_leaf
        if [identifier for identifier, _child in left.children] != [
            identifier for identifier, _child in right.children
        ]:
            return False
        return all(
            cls._structures_have_same_identifiers(left_child, right_child)
            for (_left_identifier, left_child), (_right_identifier, right_child) in zip(left.children, right.children)
        )

    def _mapping_structure(self, to_match):
        child_collection = matching.get_collection(to_match.hdca)
        collection_type_description = (
            self.trans.app.dataset_collection_manager.collection_type_descriptions.for_collection_type(
                child_collection.collection_type
            )
        )
        return matching.get_structure(
            child_collection,
            collection_type_description,
            leaf_subcollection_type=to_match.subcollection_type,
        )

    def _take_axis_prefix(self, axes, rank):
        selected_axes = []
        remaining_rank = rank
        for axis in axes:
            if remaining_rank <= 0:
                break
            axis_rank = len(axis.structure.collection_type_description.collection_type.split(":"))
            if axis_rank <= remaining_rank:
                selected_axes.append(axis)
                remaining_rank -= axis_rank
            else:
                selected_axes.append(self._truncate_axis(axis, remaining_rank))
                remaining_rank = 0
        return tuple(selected_axes)

    def _truncate_axis(self, axis, rank):
        collection_type = axis.structure.collection_type_description.collection_type
        prefix_collection_type = ":".join(collection_type.split(":")[:rank])
        type_description = self.trans.app.dataset_collection_manager.collection_type_descriptions.for_collection_type(
            prefix_collection_type
        )

        def truncate_structure(structure, remaining_rank, description):
            if not structure.children_known:
                return UninitializedTree(description)
            if remaining_rank == 1:
                children = [(identifier, matching.leaf) for identifier, _child in structure.children]
            else:
                child_description = description.subcollection_type_description()
                children = [
                    (identifier, truncate_structure(child, remaining_rank - 1, child_description))
                    for identifier, child in structure.children
                ]
            return Tree(children, description)

        return matching.MatchingCollectionAxis(
            truncate_structure(axis.structure, rank, type_description),
            ("axis-prefix", axis.axis_id, rank),
        )

    @staticmethod
    def _source_mapping_axes(progress, step, input_name):
        axes = []
        for connection in step.input_connections_by_name.get(input_name, []):
            source_step_id = connection.output_step.id
            source_axes = progress.inherited_input_axes.get(source_step_id)
            if source_axes is None:
                source_axes = progress.output_mapping_axes.get((source_step_id, connection.output_name))
            for axis in source_axes or ():
                if not any(axis.axis_id == existing.axis_id for existing in axes):
                    axes.append(axis)
        return tuple(axes)

    @staticmethod
    def _assign_linked_axis_identity(progress, step, collections_to_match, residual_binding_names=()):
        linked_inputs = [(name, to_match) for name, to_match in collections_to_match.items() if to_match.linked]
        linked_input_names = [name for name, _to_match in linked_inputs]
        linked_input_names.extend(residual_binding_names)
        if not linked_input_names:
            return None

        source_tokens = set()
        for input_name in linked_input_names:
            for connection in step.input_connections_by_name.get(input_name, []):
                source_tokens.add((connection.output_step.id, connection.output_name))

        invocation_uuid = progress.workflow_invocation.uuid
        assert invocation_uuid is not None
        axis_id = ("workflow-map", str(invocation_uuid), tuple(sorted(source_tokens)))
        for _input_name, to_match in linked_inputs:
            to_match.axis_id = axis_id
        return axis_id

    def _find_collections_to_match(
        self, progress: "WorkflowProgress", step: "WorkflowStep", all_inputs: "list[InputDescription]"
    ) -> matching.CollectionsToMatch:
        collections_to_match = matching.CollectionsToMatch()
        dataset_collection_type_descriptions = self.trans.app.dataset_collection_manager.collection_type_descriptions

        for input_dict in all_inputs:
            name = input_dict["name"]
            data = progress.replacement_for_input(self.trans, step, input_dict)
            if not isinstance(data, (model.DatasetCollectionInstance, model.DatasetCollectionElement)):
                continue
            if not data.collection.allow_implicit_mapping:
                continue

            is_data_param = input_dict["input_type"] == "dataset"
            is_data_collection_param = input_dict["input_type"] == "dataset_collection"
            if is_data_param or is_data_collection_param:
                if is_data_param:
                    if input_dict["multiple"]:
                        # multiple="true" data input, acts like "list" collection_type.
                        consumed_collection_types = ["list"]
                    else:
                        collections_to_match.add(name, data)
                        continue
                else:
                    consumed_collection_types = self._declared_collection_input_types(progress, input_dict)
                remaining_outer_types = self._reserve_outer_structure(progress)
                history_query = HistoryQuery.from_collection_types(
                    consumed_collection_types,
                    dataset_collection_type_descriptions,
                )
                if not progress.subworkflow_structure and history_query.direct_match(data):
                    continue

                subcollection_type_description = history_query.can_map_over(data) or None
                if subcollection_type_description:
                    subcollection_type_description = self._concrete_subcollection_type(
                        subcollection_type_description, data
                    )
                    subcollection_type_description = self._consume_outer_structure(
                        subcollection_type_description, remaining_outer_types
                    )
                    collections_to_match.add(name, data, subcollection_type=subcollection_type_description)
                elif is_data_param and progress.subworkflow_structure:
                    collections_to_match.add(name, data, subcollection_type=subcollection_type_description)
                continue

            collections_to_match.add(name, data)

        self._add_when_expression_collections(progress, step, all_inputs, collections_to_match)
        return collections_to_match

    def _declared_collection_input_types(self, progress: "WorkflowProgress", input_dict: "InputDescription"):
        """Collection types a dataset_collection input declares it consumes.

        Falls back to the mapped-over subworkflow invocation's structure and
        then the input's single declared collection type.
        """
        declared = input_dict.get("collection_types")
        if not declared:
            if progress.subworkflow_structure:
                declared = [progress.subworkflow_structure.collection_type_description.collection_type]
            elif collection_type := input_dict.get("collection_type"):
                declared = [collection_type]
        return declared

    def _reserve_outer_structure(self, progress: "WorkflowProgress") -> list[str]:
        """Set aside collection levels owned by a mapped-over subworkflow invocation.

        When mapping a subworkflow invocation over a higher-dimension input -
        e.g. an outer list:list over an inner list - the inner workflow cannot
        reduce the outer list. Returns the outer levels below the outermost,
        to be accounted for by ``_consume_outer_structure``.
        """
        remaining_outer_types: list[str] = []
        if progress.subworkflow_structure:
            remaining_outer_types = progress.subworkflow_structure.collection_type_description.collection_type.split(
                ":"
            )
            remaining_outer_types.pop(0)
        return remaining_outer_types

    def _concrete_subcollection_type(self, subcollection_type_description, data):
        """Translate paired_or_unpaired to a concrete mapping type for flat collections.

        Mirrors ``DataCollectionToolParameter._classify_hdca`` in
        ``galaxy.tools.parameters.basic``, which the API tool execution path
        uses.
        """
        subcollection_type = subcollection_type_description.collection_type
        input_collection_type = data.collection.collection_type
        if subcollection_type == "paired_or_unpaired" and not input_collection_type.endswith("paired_or_unpaired"):
            type_descriptions = self.trans.app.dataset_collection_manager.collection_type_descriptions
            concrete_type = "paired" if input_collection_type.endswith("paired") else "single_datasets"
            subcollection_type_description = type_descriptions.for_collection_type(concrete_type)
        return subcollection_type_description

    def _consume_outer_structure(self, subcollection_type_description, remaining_outer_types: list[str]):
        """Fold outer levels reserved by ``_reserve_outer_structure`` into the mapping.

        The levels the matched subcollection already covers are checked off;
        any levels still left become the subcollection type so the outer
        structure is preserved by the mapping.
        """
        subcollection_type_list = subcollection_type_description.collection_type.split(":")
        for collection_type in reversed(subcollection_type_list):
            if remaining_outer_types:
                outer_type = remaining_outer_types.pop(0)
                assert collection_type == outer_type
        if remaining_outer_types:
            type_descriptions = self.trans.app.dataset_collection_manager.collection_type_descriptions
            subcollection_type_description = type_descriptions.for_collection_type(":".join(remaining_outer_types))
        return subcollection_type_description

    def _add_when_expression_collections(
        self,
        progress: "WorkflowProgress",
        step: "WorkflowStep",
        all_inputs: "list[InputDescription]",
        collections_to_match: matching.CollectionsToMatch,
    ) -> None:
        """Match collections wired to a conditional step's execution state.

        Inputs consumed only by the step's when expression do not appear in
        ``all_inputs`` but still drive mapping.
        """
        if not step.when_expression:
            return
        known_input_names = {input_dict["name"] for input_dict in all_inputs}
        for step_input in step.inputs:
            step_input_name = step_input.name
            if step_input_name is None:
                continue
            input_in_execution_state = step_input_name not in known_input_names
            if input_in_execution_state:
                maybe_collection = progress.replacement_for_connection(
                    step.input_connections_by_name[step_input_name][0]
                )
                if hasattr(maybe_collection, "collection"):
                    # TODO: is a "collection" attribute always enough to treat this as matchable?
                    collections_to_match.add(step_input_name, maybe_collection)


def collect_output_mapping_axes(subworkflow, subworkflow_progress, collection_info):
    output_mapping_axes = {}
    for workflow_output in subworkflow.workflow_outputs:
        workflow_output_label = (
            workflow_output.label or f"{workflow_output.workflow_step.order_index}:{workflow_output.output_name}"
        )
        axes = subworkflow_progress.output_mapping_axes.get(
            (workflow_output.workflow_step_id, workflow_output.output_name)
        )
        if axes:
            output_mapping_axes[workflow_output_label] = axes
        elif collection_info:
            output_mapping_axes[workflow_output_label] = tuple(collection_info.mapping_axes)
    return output_mapping_axes
