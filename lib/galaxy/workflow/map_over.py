"""Plan implicit map-over of workflow steps across collections.

When a step's data inputs are connected to collections with deeper structure
than the input consumes, Galaxy runs the step once per matching coordinate and
collects the results - the step is "mapped over" its inputs.
``MapOverPlanner.compute_collection_info`` builds that plan for one step: the
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
    from galaxy.workflow.run import WorkflowProgress


class MapOverPlanner:
    """Build the map-over plan for one workflow step (see module docstring)."""

    def __init__(self, trans: "ProvidesHistoryContext"):
        self.trans = trans

    def compute_collection_info(
        self, progress: "WorkflowProgress", step, all_inputs
    ) -> matching.MatchingCollections | None:
        """
        Use get_all_inputs (if implemented) to determine collection mapping for execution.
        """
        collections_to_match = self._find_collections_to_match(progress, step, all_inputs)
        # Have implicit collections...
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

    def _find_collections_to_match(self, progress: "WorkflowProgress", step, all_inputs) -> matching.CollectionsToMatch:
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
                multiple = input_dict["multiple"]
                if is_data_param:
                    if multiple:
                        # multiple="true" data input, acts like "list" collection_type.
                        effective_input_collection_type = ["list"]
                    else:
                        collections_to_match.add(name, data)
                        continue
                else:
                    effective_input_collection_type = input_dict.get("collection_types")
                    if not effective_input_collection_type:
                        if progress.subworkflow_structure:
                            effective_input_collection_type = [
                                progress.subworkflow_structure.collection_type_description.collection_type
                            ]
                        elif input_dict.get("collection_type"):
                            effective_input_collection_type = [input_dict.get("collection_type")]
                type_list = []
                if progress.subworkflow_structure:
                    # If we have progress.subworkflow_structure were mapping a subworkflow invocation over a higher-dimension input
                    # e.g an outer list:list over an inner list. Whatever we do, the inner workflow cannot reduce the outer list.
                    # This is what we're setting up here.
                    type_list = progress.subworkflow_structure.collection_type_description.collection_type.split(":")
                    leaf_type = type_list.pop(0)
                    if type_list and type_list[-1] == effective_input_collection_type:
                        effective_input_collection_type = [":".join(type_list[:-1])] if ":".join(type_list[:-1]) else []
                history_query = HistoryQuery.from_collection_types(
                    effective_input_collection_type,
                    dataset_collection_type_descriptions,
                )
                if not progress.subworkflow_structure and history_query.direct_match(data):
                    continue

                subcollection_type_description = history_query.can_map_over(data) or None
                if subcollection_type_description:
                    # Translate paired_or_unpaired to concrete mapping type for
                    # flat collections. Mirrors logic in basic.py:2675-2679 that
                    # the API tool execution path uses.
                    _sub_ct = subcollection_type_description.collection_type
                    _hdca_ct = data.collection.collection_type
                    if _sub_ct == "paired_or_unpaired" and not _hdca_ct.endswith("paired_or_unpaired"):
                        if _hdca_ct.endswith("paired"):
                            subcollection_type_description = dataset_collection_type_descriptions.for_collection_type(
                                "paired"
                            )
                        else:
                            subcollection_type_description = dataset_collection_type_descriptions.for_collection_type(
                                "single_datasets"
                            )
                    subcollection_type_list = subcollection_type_description.collection_type.split(":")
                    for collection_type in reversed(subcollection_type_list):
                        if type_list:
                            leaf_type = type_list.pop(0)
                            assert collection_type == leaf_type
                    if type_list:
                        subcollection_type_description = dataset_collection_type_descriptions.for_collection_type(
                            ":".join(type_list)
                        )
                    collections_to_match.add(name, data, subcollection_type=subcollection_type_description)
                elif is_data_param and progress.subworkflow_structure:
                    collections_to_match.add(name, data, subcollection_type=subcollection_type_description)
                continue

            collections_to_match.add(name, data)

        known_input_names = {input_dict["name"] for input_dict in all_inputs}

        if step.when_expression:
            for step_input in step.inputs:
                step_input_name = step_input.name
                input_in_execution_state = step_input_name not in known_input_names
                if input_in_execution_state:
                    maybe_collection = progress.replacement_for_connection(
                        step.input_connections_by_name[step_input_name][0]
                    )
                    if hasattr(maybe_collection, "collection"):
                        # Is that always right ?
                        collections_to_match.add(step_input_name, maybe_collection)

        return collections_to_match
