"""Decide which outputs a tool run creates and how they look, without creating them.

``DefaultToolAction.execute`` creates outputs from these decisions, and ``ExecutionTracker``
names and shapes the collections of a mapped-over run with them. Keeping the decisions apart
from object creation lets callers ask what a run would create.
"""

from collections.abc import (
    Iterator,
    Mapping,
)
from dataclasses import dataclass
from typing import (
    Any,
    cast,
    TYPE_CHECKING,
)

from packaging.version import Version

from galaxy.job_execution.output_format import (
    get_ext_or_implicit_ext,
    resolve_format_source,
)
from galaxy.tools.execution_helpers import (
    filter_output,
    ToolExecutionCache,
)
from galaxy.util.template import fill_template

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesHistoryContext
    from galaxy.model import (
        DatasetInstance,
        History,
        HistoryDatasetCollectionAssociation,
    )
    from galaxy.model.dataset_collections.structure import (
        Tree,
        UninitializedTree,
    )
    from galaxy.tool_util.parser.output_objects import (
        ToolOutput,
        ToolOutputBase,
        ToolOutputCollection,
    )
    from galaxy.tools import Tool
    from galaxy.tools.actions import ToolAction
    from galaxy.tools.parameters.basic import (
        BaseDataToolParameter,
        DataCollectionToolParameter,
    )
    from galaxy.tools.parameters.wrapped import LegacyUnprefixedDict


def input_ext_for(tool: "Tool", input_datasets: "LegacyUnprefixedDict") -> str:
    """Return the format that ``format="input"`` outputs get.

    Tools with profile 16.04 or later keep the literal ``input``; older tools take the format of
    their first data input.
    """
    if Version(str(tool.profile)) >= Version("16.04"):
        return "input"
    input_ext = "data"
    for data in reversed(list(input_datasets.values())):
        if data:
            input_ext = data.ext
    return input_ext


def determine_output_format(
    output: "ToolOutput",
    parameter_context: Mapping[str, Any],
    input_datasets: Mapping[str, "DatasetInstance | None"],
    input_dataset_collections: Mapping[str, "HistoryDatasetCollectionAssociation"],
    random_input_ext: str | None,
    python_template_version: "str | Version | None" = "3",
    execution_cache: ToolExecutionCache | None = None,
) -> str | None:
    """Determines the output format for a dataset based on an abstract
    description of the output (galaxy.tool_util.parser.ToolOutput), the parameter
    wrappers, a map of the input datasets (name => HDA), and the last input
    extensions in the tool form.

    TODO: Make the input extension used deterministic instead of random.
    """
    # the type should match the input
    ext = output.format
    if ext == "input":
        if input_datasets and random_input_ext in {"data", "auto"}:
            # Probably dealing with an implicitly converted dataset
            try:
                first_input_dataset = next(iter(input_datasets.values()))
                if first_input_dataset is not None:
                    random_input_ext = get_ext_or_implicit_ext(first_input_dataset)
            except Exception:
                pass
        ext = random_input_ext
    if (format_source := output.format_source) is not None:
        ext = resolve_format_source(format_source, input_datasets, input_dataset_collections, ext, execution_cache)

    # process change_format tags
    if output.change_format:
        for change_format_model in output.change_format:
            input_check = change_format_model.get("input")
            if input_check is not None:
                try:
                    if (
                        fill_template(
                            input_check, context=parameter_context, python_template_version=python_template_version
                        )
                        == change_format_model["value"]
                    ):
                        if change_format_model["format"]:
                            return change_format_model["format"]
                except Exception:
                    # bad tag input value; possibly referencing a param within a different conditional when block or other nonexistent grouping construct
                    continue
            else:
                input_dataset_check = change_format_model.get("input_dataset")
                if input_dataset_check is not None:
                    dataset = input_datasets.get(input_dataset_check)
                    # At this point check is a HistoryDatasetAssociation object.
                    check_format = change_format_model["format"] or ext
                    check_value = change_format_model["value"]
                    check_attribute = change_format_model["check_attribute"]
                    if dataset is not None and check_value is not None and check_attribute is not None:
                        # See if the attribute to be checked belongs to the HistoryDatasetAssociation object.
                        if hasattr(dataset, check_attribute):
                            if str(getattr(dataset, check_attribute)) == str(check_value):
                                return check_format
                        # See if the attribute to be checked belongs to the metadata associated with the
                        # HistoryDatasetAssociation object.
                        if dataset.metadata is not None:
                            metadata_value = dataset.metadata.get(check_attribute)
                            if metadata_value is not None:
                                if str(metadata_value) == str(check_value):
                                    return check_format
    return ext


class OutputPlanner:
    """Decide which outputs one job of a tool creates and their format, name and visibility.

    Built from inputs already collected for the job; reading the decisions changes nothing.
    """

    def __init__(
        self,
        trans: "ProvidesHistoryContext",
        tool: "Tool",
        tool_action: "ToolAction",
        incoming: dict[str, Any],
        params: dict[str, Any],
        input_datasets: "LegacyUnprefixedDict",
        input_collections: Mapping[str, "HistoryDatasetCollectionAssociation"],
        input_ext: str,
        on_text: str | None,
        history: "History | None" = None,
        job_params: Any = None,
        execution_cache: ToolExecutionCache | None = None,
        mapping_over: bool = False,
    ):
        """
        :param incoming: populated tool state, read by output filters
        :param params: wrapped parameters, the context of ``change_format`` and output labels
        :param mapping_over: whether this job is one of a mapped-over run, whose datasets are hidden
        """
        self.trans = trans
        self.tool = tool
        self.tool_action = tool_action
        self.incoming = incoming
        self.params = params
        self.input_datasets = input_datasets
        self.input_collections = input_collections
        self.input_ext = input_ext
        self.on_text = on_text
        self.history = history
        self.job_params = job_params
        self.execution_cache = execution_cache
        self.mapping_over = mapping_over

    def included_outputs(self) -> Iterator[tuple[str, "ToolOutputBase"]]:
        """Yield the tool outputs that the output filters keep, in tool order."""
        for name, output in self.tool.outputs.items():
            if not filter_output(self.tool, output, self.incoming):
                yield name, output

    def format(self, output: "ToolOutput") -> str | None:
        """Return the format of a dataset output, before ``<actions>`` run on the created dataset."""
        return determine_output_format(
            output,
            self.params,
            self.input_datasets,
            self.input_collections,
            self.input_ext,
            python_template_version=self.tool.python_template_version,
            execution_cache=self.execution_cache,
        )

    def name(self, output: "ToolOutputBase", dataset: "DatasetInstance | None" = None) -> str:
        """Return the name of an output: its rendered label, or the tool action's default name."""
        return self.tool_action.get_output_name(
            output,
            dataset,
            self.tool,
            self.on_text,
            self.trans,
            self.incoming,
            self.history,
            self.params,
            self.job_params,
        )

    def hidden(self, output: "ToolOutputBase") -> bool:
        return bool(output.hidden) or self.mapping_over


def output_collection_type(
    trans: "ProvidesHistoryContext",
    output: "ToolOutputCollection",
    input_collections: Mapping[str, "HistoryDatasetCollectionAssociation"],
    input_collection_parameters: Mapping[str, "BaseDataToolParameter"],
) -> str:
    """Return the collection type of an output collection, following ``type_source`` if it has one."""
    collection_type = output.structure.collection_type
    if collection_type is not None:
        return collection_type
    collection_type_source = output.structure.collection_type_source
    if collection_type_source is None:
        raise Exception("Could not determine collection type to create.")
    data_param = input_collection_parameters.get(collection_type_source)
    if data_param is None:
        raise Exception(
            f"Output collection '{output.name}' has type_source '{collection_type_source}', which does not name a collection input."
        )
    input_collection = input_collections[collection_type_source]
    collection_param = cast("DataCollectionToolParameter", data_param)
    collection_type_description = collection_param._history_query(trans).can_map_over(input_collection)
    if collection_type_description:
        return cast(str, collection_type_description.collection_type)
    return input_collection.collection.collection_type


@dataclass(frozen=True)
class ImplicitOutputPlan:
    """An output collection that a mapped-over run creates around its jobs' outputs."""

    output: "ToolOutputBase"
    name: str
    structure: "Tree | UninitializedTree"
