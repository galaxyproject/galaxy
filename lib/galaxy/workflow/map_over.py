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
    model,
)
from galaxy.model.dataset_collections import matching
from galaxy.model.dataset_collections.query import HistoryQuery

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
        collection_info = self.trans.app.dataset_collection_manager.match_collections(collections_to_match)
        if collection_info:
            if progress.subworkflow_collection_info:
                # We've mapped over a subworkflow. Slices of the invocation might be conditional
                # and progress.subworkflow_collection_info.when_values holds the appropriate when_values
                collection_info.when_values = progress.subworkflow_collection_info.when_values
            else:
                # The invocation is not mapped over, but it might still be conditional.
                # Multiplication and linking should be handled by slice_collection()
                collection_info.when_values = progress.when_values
        return collection_info or progress.subworkflow_collection_info

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
            input_in_execution_state = step_input_name not in known_input_names
            if input_in_execution_state:
                maybe_collection = progress.replacement_for_connection(
                    step.input_connections_by_name[step_input_name][0]
                )
                if hasattr(maybe_collection, "collection"):
                    # TODO: is a "collection" attribute always enough to treat this as matchable?
                    collections_to_match.add(step_input_name, maybe_collection)
