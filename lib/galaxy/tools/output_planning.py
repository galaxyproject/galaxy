"""Decide which outputs a tool run creates and how they look, without creating them.

``DefaultToolAction.execute`` creates outputs from these decisions, and ``ExecutionTracker``
names and shapes the collections of a mapped-over run with them. Keeping the decisions apart
from object creation lets callers ask what a run would create.
"""

from collections.abc import (
    Iterable,
    Iterator,
    Mapping,
)
from dataclasses import dataclass
from typing import (
    Any,
    cast,
    Literal,
    TYPE_CHECKING,
)

from packaging.version import Version

from galaxy.job_execution.output_format import (
    get_ext_or_implicit_ext,
    resolve_format_source,
)
from galaxy.model.dataset_collections.structure import Tree
from galaxy.tool_util.parser.output_actions import (
    FormatToolOutputAction,
    ToolOutputActionConditional,
    ToolOutputActionGroup,
)
from galaxy.tool_util.parser.output_collection_def import DEFAULT_DATASET_COLLECTOR_DESCRIPTION
from galaxy.tool_util.parser.output_objects import (
    tool_output_is_collection,
    ToolExpressionOutput,
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
    from galaxy.model.dataset_collections.structure import UninitializedTree
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
        *,
        history: "History | None",
        job_params: Any,
        execution_cache: ToolExecutionCache | None,
        mapping_over: bool,
        input_collection_parameters: Mapping[str, "BaseDataToolParameter"],
        unconverted_inputs: Iterable[str],
    ):
        """
        :param incoming: populated tool state, read by output filters
        :param params: wrapped parameters, the context of ``change_format`` and output labels
        :param mapping_over: whether this job is one of a mapped-over run, whose datasets are hidden
        :param input_collection_parameters: the collection input parameters by name, to resolve the
            ``type_source`` of output collections
        :param unconverted_inputs: inputs left in a datatype a run would convert them from; formats
            that follow them are not known
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
        self.input_collection_parameters = input_collection_parameters
        self.unconverted_inputs = frozenset(unconverted_inputs)
        # format_source names an input without its section or conditional prefix
        self._unconverted_names = {
            name.rsplit("|", 1)[-1] for name in self.unconverted_inputs
        } | self.unconverted_inputs

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

    def planned_outputs(self) -> list["PlannedOutput"]:
        """Describe the outputs of this job as a run would create them."""
        planned = []
        for name, output in self.included_outputs():
            if tool_output_is_collection(output):
                planned.append(self._planned_collection(name, output))
            elif isinstance(output, ToolExpressionOutput):
                planned.append(PlannedOutput(name, self._label(output), "parameter", hidden=self.hidden(output)))
            else:
                output = cast("ToolOutput", output)
                planned.append(
                    PlannedOutput(
                        name,
                        self._label(output),
                        "data",
                        format=self.known_format(output),
                        format_source=output.format_source,
                        hidden=self.hidden(output),
                        dynamic=_discovers_datasets(output),
                    )
                )
        return planned

    def known_format(self, output: "ToolOutput") -> str | None:
        """Return the format a run gives a dataset output, or None if only the job decides it."""
        if output.actions and _actions_can_change_format(output.actions):
            return None
        follows_unconverted = (
            output.format_source is not None and _input_name(output.format_source) in self._unconverted_names
        ) or (output.format == "input" and self.unconverted_inputs)
        if follows_unconverted:
            return None
        ext = self.format(output)
        return None if ext in RUNTIME_FORMATS else ext

    def _planned_collection(self, name: str, output: "ToolOutputCollection") -> "PlannedOutput":
        try:
            collection_type: str | None = output_collection_type(
                self.trans, output, self.input_collections, self.input_collection_parameters
            )
        except Exception:
            collection_type = None
        element_count = None
        part_formats: set[str | None] = set()
        parts = None
        if not output.dynamic_structure:
            try:
                parts = output.known_outputs(
                    self.input_collections, self.trans.app.dataset_collection_manager.type_registry
                )
            except (AttributeError, KeyError):
                # structured_like can name an optional collection input the form hasn't filled.
                parts = None
        if parts is not None:
            element_count = len({(part.parent_ids or [part.element_identifier])[0] for part in parts})
            part_formats = {self.known_format(part.output_def) for part in parts}
        return PlannedOutput(
            name,
            self._label(output),
            "collection",
            format=part_formats.pop() if len(part_formats) == 1 else None,
            collection_type=collection_type,
            element_count=element_count,
            hidden=self.hidden(output),
            dynamic=output.dynamic_structure,
        )

    def _label(self, output: "ToolOutputBase") -> str | None:
        try:
            return self.name(output)
        except Exception:
            # A label template can read inputs a partly filled form does not have yet.
            return None


# Formats a run replaces once the job has produced the dataset; "input" is what format="input"
# gives on tools with profile 16.04 or later.
RUNTIME_FORMATS = {"auto", "_sniff_", "input"}


def _discovers_datasets(output: "ToolOutput") -> bool:
    # Every data output gets the legacy collector of primary_<id>_ files; only declared ones count.
    return any(
        description is not DEFAULT_DATASET_COLLECTOR_DESCRIPTION
        for description in output.dataset_collector_descriptions
    )


def _input_name(format_source: str) -> str:
    # format_source can point into a collection input, e.g. "input1[0]" or "input1['forward']"
    return format_source.split("[", 1)[0]


def _actions_can_change_format(group: "ToolOutputActionGroup") -> bool:
    for action in group.actions:
        if isinstance(action, FormatToolOutputAction):
            return True
        if isinstance(action, ToolOutputActionConditional) and any(
            _actions_can_change_format(case) for case in action.cases
        ):
            return True
    return False


@dataclass(frozen=True)
class PlannedOutput:
    """An output that a tool run would create, as described before it runs.

    ``format``, ``collection_type`` and ``element_count`` are None when only the job decides them.
    """

    name: str
    label: str | None
    output_type: Literal["data", "collection", "parameter"]
    format: str | None = None
    format_source: str | None = None
    collection_type: str | None = None
    element_count: int | None = None
    hidden: bool = False
    dynamic: bool = False
    mapped_over: bool = False


@dataclass(frozen=True)
class PlannedRun:
    """The jobs and outputs a tool request would create."""

    job_count: int
    outputs: list[PlannedOutput]


def planned_implicit_outputs(
    plans: Mapping[str, "ImplicitOutputPlan"], job_planner: OutputPlanner | None
) -> list[PlannedOutput]:
    """Describe the output collections of a mapped-over run.

    :param job_planner: the planner of the run's first job, which decides the formats of the
        datasets each collection gathers; None if the run has no jobs
    """
    planned = []
    for name, plan in plans.items():
        output = plan.output
        structure = plan.structure
        format = None
        if (
            job_planner is not None
            and not tool_output_is_collection(output)
            and not isinstance(output, ToolExpressionOutput)
        ):
            format = job_planner.known_format(cast("ToolOutput", output))
        planned.append(
            PlannedOutput(
                name,
                plan.name,
                "collection",
                format=format,
                format_source=getattr(output, "format_source", None),
                collection_type=structure.collection_type_description.collection_type,
                element_count=len(structure.children) if isinstance(structure, Tree) else None,
                dynamic=tool_output_is_collection(output) and output.dynamic_structure,
                mapped_over=True,
            )
        )
    return planned


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
