import json
import logging
import os
import re
from abc import abstractmethod
from json import dumps
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from packaging.version import Version

from galaxy import model
from galaxy.exceptions import (
    AuthenticationRequired,
    ItemAccessibilityException,
    RequestParameterInvalidException,
)
from galaxy.job_execution.actions.post import ActionBox
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.model import (
    History,
    HistoryDatasetAssociation,
    Job,
    LibraryDatasetDatasetAssociation,
    WorkflowRequestInputParameter,
)
from galaxy.model.base import transaction
from galaxy.model.dataset_collections.builder import CollectionBuilder
from galaxy.model.dataset_collections.matching import MatchingCollections
from galaxy.model.none_like import NoneDataset
from galaxy.objectstore import ObjectStorePopulator
from galaxy.tools._types import ToolStateJobInstancePopulatedT
from galaxy.tools.execute import (
    DatasetCollectionElementsSliceT,
    DEFAULT_DATASET_COLLECTION_ELEMENTS,
    DEFAULT_JOB_CALLBACK,
    DEFAULT_PREFERRED_OBJECT_STORE_ID,
    DEFAULT_RERUN_REMAP_JOB_ID,
    DEFAULT_SET_OUTPUT_HID,
    JobCallbackT,
)
from galaxy.tools.execution_helpers import (
    filter_output,
    on_text_for_names,
    ToolExecutionCache,
)
from galaxy.tools.parameters import update_dataset_ids
from galaxy.tools.parameters.basic import (
    DataCollectionToolParameter,
    DataToolParameter,
    SelectToolParameter,
)
from galaxy.tools.parameters.workflow_utils import RuntimeValue
from galaxy.tools.parameters.wrapped import (
    LegacyUnprefixedDict,
    WrappedParameters,
)
from galaxy.util import ExecutionTimer
from galaxy.util.template import fill_template

if TYPE_CHECKING:
    from galaxy.model import DatasetInstance
    from galaxy.tool_util.parser.output_objects import ToolOutput

log = logging.getLogger(__name__)


OutputDatasetsT = Dict[str, "DatasetInstance"]
ToolActionExecuteResult = Union[Tuple[Job, OutputDatasetsT, Optional[History]], Tuple[Job, OutputDatasetsT]]


class ToolAction:
    """
    The actions to be taken when a tool is run (after parameters have
    been converted and validated).
    """

    @abstractmethod
    def execute(
        self,
        tool,
        trans,
        incoming: Optional[ToolStateJobInstancePopulatedT] = None,
        history: Optional[History] = None,
        job_params=None,
        rerun_remap_job_id: Optional[int] = DEFAULT_RERUN_REMAP_JOB_ID,
        execution_cache: Optional[ToolExecutionCache] = None,
        dataset_collection_elements: Optional[DatasetCollectionElementsSliceT] = DEFAULT_DATASET_COLLECTION_ELEMENTS,
        completed_job: Optional[Job] = None,
        collection_info: Optional[MatchingCollections] = None,
        job_callback: Optional[JobCallbackT] = DEFAULT_JOB_CALLBACK,
        preferred_object_store_id: Optional[str] = DEFAULT_PREFERRED_OBJECT_STORE_ID,
        set_output_hid: bool = DEFAULT_SET_OUTPUT_HID,
        flush_job: bool = True,
        skip: bool = False,
    ) -> ToolActionExecuteResult:
        """Perform target tool action."""

    @abstractmethod
    def get_output_name(
        self,
        output,
        dataset=None,
        tool=None,
        on_text=None,
        trans=None,
        incoming=None,
        history=None,
        params=None,
        job_params=None,
    ) -> str:
        """Get name to assign a tool output."""


class DefaultToolAction(ToolAction):
    """Default tool action is to run an external command"""

    produces_real_jobs: bool = True

    def _collect_input_datasets(
        self,
        tool,
        param_values,
        trans: ProvidesHistoryContext,
        history,
        current_user_roles=None,
        dataset_collection_elements=None,
        collection_info=None,
    ):
        """
        Collect any dataset inputs from incoming. Returns a mapping from
        parameter name to Dataset instance for each tool parameter that is
        of the DataToolParameter type.
        """
        if current_user_roles is None:
            current_user_roles = trans.get_current_user_roles()
        input_datasets = LegacyUnprefixedDict()
        all_permissions: Dict[str, Set[str]] = {}

        def record_permission(action, role_id):
            if action not in all_permissions:
                all_permissions[action] = set()
            all_permissions[action].add(role_id)

        def visitor(input, value, prefix, prefixed_name: str, parent=None, **kwargs):
            def process_dataset(data, formats=None):
                if not data or isinstance(data, RuntimeValue):
                    return None
                if formats is None:
                    formats = input.formats

                data = getattr(data, "hda", data)

                direct_match, target_ext, converted_dataset = data.find_conversion_destination(formats)
                if not direct_match and target_ext:
                    if converted_dataset:
                        data = converted_dataset
                    else:
                        data = data.get_converted_dataset(trans, target_ext, target_context=parent, history=history)

                input_name = prefixed_name
                # Checked security of whole collection all at once if mapping over this input, else
                # fetch dataset details for this input from the database.
                if collection_info and collection_info.is_mapped_over(input_name):
                    action_tuples = collection_info.map_over_action_tuples(input_name)
                    if not trans.user_is_admin and not trans.app.security_agent.can_access_datasets(
                        current_user_roles, action_tuples
                    ):
                        raise ItemAccessibilityException(
                            "User does not have permission to use a dataset provided for input."
                        )
                    for action, role_id in action_tuples:
                        record_permission(action, role_id)
                else:
                    if not trans.user_is_admin and not trans.app.security_agent.can_access_dataset(
                        current_user_roles, data.dataset
                    ):
                        raise ItemAccessibilityException(
                            f"User does not have permission to use dataset ({data.name}) provided for input."
                        )
                    permissions = trans.app.security_agent.get_permissions(data.dataset)
                    for action, roles in permissions.items():
                        for role in roles:
                            record_permission(action.action, model.cached_id(role))
                return data

            if isinstance(input, DataToolParameter):
                if isinstance(value, list):
                    # If there are multiple inputs with the same name, they
                    # are stored as name1, name2, ...
                    for i, v in enumerate(value):
                        processed_dataset = process_dataset(v)
                        if i == 0:
                            # Allow copying metadata to output, first item will be source.
                            input_datasets[prefixed_name] = processed_dataset
                            input_datasets.set_legacy_alias(new_key=prefixed_name, old_key=prefix + input.name)
                        input_datasets[prefixed_name + str(i + 1)] = processed_dataset
                        input_datasets.set_legacy_alias(
                            new_key=prefixed_name + str(i + 1), old_key=prefix + input.name + str(i + 1)
                        )
                        conversions = []
                        for conversion_name, conversion_extensions, conversion_datatypes in input.conversions:
                            new_data = process_dataset(input_datasets[prefixed_name + str(i + 1)], conversion_datatypes)
                            if not new_data or new_data.datatype.matches_any(conversion_datatypes):
                                input_datasets[prefixed_name[: -len(input.name)] + conversion_name + str(i + 1)] = (
                                    new_data
                                )
                                input_datasets.set_legacy_alias(
                                    new_key=prefixed_name[: -len(input.name)] + conversion_name + str(i + 1),
                                    old_key=prefix + conversion_name + str(i + 1),
                                )
                                conversions.append((conversion_name, new_data))
                            else:
                                raise Exception(
                                    f"A path for explicit datatype conversion has not been found: {input_datasets[prefixed_name + str(i + 1)].extension} --/--> {conversion_extensions}"
                                )
                        if parent:
                            parent[input.name][i] = input_datasets[prefixed_name + str(i + 1)]
                            for conversion_name, conversion_data in conversions:
                                # allow explicit conversion to be stored in job_parameter table
                                parent[conversion_name][
                                    i
                                ] = conversion_data.id  # a more robust way to determine JSONable value is desired
                        else:
                            param_values[input.name][i] = input_datasets[prefixed_name + str(i + 1)]
                            for conversion_name, conversion_data in conversions:
                                # allow explicit conversion to be stored in job_parameter table
                                param_values[conversion_name][
                                    i
                                ] = conversion_data.id  # a more robust way to determine JSONable value is desired
                else:
                    input_datasets[prefixed_name] = process_dataset(value)
                    input_datasets.set_legacy_alias(new_key=prefixed_name, old_key=prefix + input.name)
                    conversions = []
                    for conversion_name, conversion_extensions, conversion_datatypes in input.conversions:
                        new_data = process_dataset(input_datasets[prefixed_name], conversion_datatypes)
                        if not new_data or new_data.datatype.matches_any(conversion_datatypes):
                            input_datasets[prefix + conversion_name] = new_data
                            conversions.append((conversion_name, new_data))
                        else:
                            raise Exception(
                                f"A path for explicit datatype conversion has not been found: {input_datasets[prefixed_name].extension} --/--> {conversion_extensions}"
                            )
                    target_dict = parent
                    if not target_dict:
                        target_dict = param_values
                    target_dict[input.name] = input_datasets[prefixed_name]
                    for conversion_name, conversion_data in conversions:
                        # allow explicit conversion to be stored in job_parameter table
                        target_dict[conversion_name] = (
                            conversion_data.id
                        )  # a more robust way to determine JSONable value is desired
            elif isinstance(input, DataCollectionToolParameter):
                if not value:
                    return

                collection = None
                child_collection = False
                if hasattr(value, "child_collection"):
                    # if we are mapping a collection over a tool, we only require the child_collection
                    child_collection = True
                    collection = value.child_collection
                else:
                    # else the tool takes a collection as input so we need everything
                    collection = value.collection

                action_tuples = collection.dataset_action_tuples
                if not trans.user_is_admin and not trans.app.security_agent.can_access_datasets(
                    current_user_roles, action_tuples
                ):
                    raise ItemAccessibilityException(
                        "User does not have permission to use a dataset provided for input."
                    )
                for action, role_id in action_tuples:
                    record_permission(action, role_id)

                _, extensions = collection.dataset_states_and_extensions_summary
                conversion_required = False
                for ext in extensions:
                    if ext:
                        datatype = trans.app.datatypes_registry.get_datatype_by_extension(ext)
                        if not datatype:
                            raise RequestParameterInvalidException(
                                f"Extension '{ext}' unknown, cannot use dataset collection as input"
                            )
                        if not datatype.matches_any(input.formats):
                            conversion_required = True
                            break
                processed_dataset_dict = {}
                for i, v in enumerate(collection.dataset_instances):
                    processed_dataset = None
                    if conversion_required:
                        processed_dataset = process_dataset(v)
                        if processed_dataset is not v:
                            processed_dataset_dict[v] = processed_dataset
                    input_datasets[prefixed_name + str(i + 1)] = processed_dataset or v
                    input_datasets.set_legacy_alias(
                        new_key=prefixed_name + str(i + 1), old_key=prefix + input.name + str(i + 1)
                    )
                if conversion_required:
                    collection_type_description = (
                        trans.app.dataset_collection_manager.collection_type_descriptions.for_collection_type(
                            collection.collection_type
                        )
                    )
                    collection_builder = CollectionBuilder(collection_type_description)
                    collection_builder.replace_elements_in_collection(
                        template_collection=collection,
                        replacement_dict=processed_dataset_dict,
                    )
                    new_collection = collection_builder.build()
                    if child_collection:
                        value.child_collection = new_collection
                    else:
                        value.collection = new_collection
            elif isinstance(input, SelectToolParameter) and isinstance(value, HistoryDatasetAssociation):
                input_datasets[prefixed_name] = value

        tool.visit_inputs(param_values, visitor)
        return input_datasets, all_permissions

    def collect_input_dataset_collections(self, tool, param_values):
        def append_to_key(the_dict: LegacyUnprefixedDict, key, legacy_key, value):
            if key not in the_dict:
                the_dict[key] = []
            the_dict.set_legacy_alias(new_key=key, old_key=legacy_key)
            the_dict[key].append(value)

        input_dataset_collections = LegacyUnprefixedDict()

        def visitor(input, value, prefix, parent=None, prefixed_name=None, **kwargs):
            if isinstance(input, DataToolParameter):
                values = value
                if not isinstance(values, list):
                    values = [value]
                for i, value in enumerate(values):
                    if isinstance(value, model.HistoryDatasetCollectionAssociation) or isinstance(
                        value, model.DatasetCollectionElement
                    ):
                        append_to_key(input_dataset_collections, prefixed_name, prefix + input.name, (value, True))
                        target_dict = parent
                        if not target_dict:
                            target_dict = param_values
                        # This is just a DataToolParameter, so replace this
                        # collection with individual datasets. Database will still
                        # record collection which should be enought for workflow
                        # extraction and tool rerun.
                        if isinstance(value, model.DatasetCollectionElement):
                            if value.child_collection:
                                # if we are mapping a collection over a tool, we only require the child_collection
                                dataset_instances = value.child_collection.dataset_instances
                            else:
                                continue
                        else:
                            # else the tool takes a collection as input so we need everything
                            dataset_instances = value.collection.dataset_instances
                        if i == 0:
                            target_dict[input.name] = []
                        target_dict[input.name].extend(dataset_instances)
            elif isinstance(input, DataCollectionToolParameter):
                append_to_key(input_dataset_collections, prefixed_name, prefix + input.name, (value, False))

        tool.visit_inputs(param_values, visitor)
        return input_dataset_collections

    def _check_access(self, tool, trans):
        assert tool.allow_user_access(trans.user), f"User ({trans.user}) is not allowed to access this tool."

    def _collect_inputs(self, tool, trans, incoming, history, current_user_roles, collection_info):
        """Collect history as well as input datasets and collections."""
        # Set history.
        if not history:
            history = tool.get_default_history_by_trans(trans, create=True)

        # Track input dataset collections - but replace with simply lists so collect
        # input datasets can process these normally.
        inp_dataset_collections = self.collect_input_dataset_collections(tool, incoming)
        # Collect any input datasets from the incoming parameters
        inp_data, all_permissions = self._collect_input_datasets(
            tool,
            incoming,
            trans,
            history=history,
            current_user_roles=current_user_roles,
            collection_info=collection_info,
        )

        preserved_tags = {}
        preserved_hdca_tags = {}
        # grab tags from incoming HDAs
        for data in inp_data.values():
            if not data:
                continue
            for tag in data.auto_propagated_tags:
                preserved_tags[tag.value] = tag
        # grab tags from incoming HDCAs
        for collection_pairs in inp_dataset_collections.values():
            for collection, _ in collection_pairs:
                # if sub-collection mapping, this will be an DC not an HDCA
                # (e.g. part of collection not a collection instance) and thus won't have tags.
                if hasattr(collection, "tags"):
                    for tag in collection.auto_propagated_tags:
                        preserved_hdca_tags[tag.value] = tag
        preserved_tags.update(preserved_hdca_tags)
        return history, inp_data, inp_dataset_collections, preserved_tags, preserved_hdca_tags, all_permissions

    def execute(
        self,
        tool,
        trans,
        incoming: Optional[ToolStateJobInstancePopulatedT] = None,
        history: Optional[History] = None,
        job_params=None,
        rerun_remap_job_id: Optional[int] = DEFAULT_RERUN_REMAP_JOB_ID,
        execution_cache: Optional[ToolExecutionCache] = None,
        dataset_collection_elements=None,
        completed_job: Optional[Job] = None,
        collection_info: Optional[MatchingCollections] = None,
        job_callback: Optional[JobCallbackT] = DEFAULT_JOB_CALLBACK,
        preferred_object_store_id: Optional[str] = DEFAULT_PREFERRED_OBJECT_STORE_ID,
        set_output_hid: bool = DEFAULT_SET_OUTPUT_HID,
        flush_job: bool = True,
        skip: bool = False,
    ) -> ToolActionExecuteResult:
        """
        Executes a tool, creating job and tool outputs, associating them, and
        submitting the job to the job queue. If history is not specified, use
        trans.history as destination for tool's output datasets.
        """
        trans.check_user_activation()
        incoming = incoming or {}
        self._check_access(tool, trans)
        app = trans.app
        if execution_cache is None:
            execution_cache = ToolExecutionCache(trans)
        current_user_roles = execution_cache.current_user_roles
        (
            history,
            inp_data,
            inp_dataset_collections,
            preserved_tags,
            preserved_hdca_tags,
            all_permissions,
        ) = self._collect_inputs(tool, trans, incoming, history, current_user_roles, collection_info)
        assert history  # tell type system we've set history and it is no longer optional
        # Build name for output datasets based on tool name and input names
        on_text = self._get_on_text(inp_data)

        # format='input" previously would give you a random extension from
        # the input extensions, now it should just give "input" as the output
        # format.
        input_ext = "data" if Version(str(tool.profile)) < Version("16.04") else "input"
        input_dbkey = incoming.get("dbkey", "?")
        for name, data in reversed(list(inp_data.items())):
            if not data:
                data = NoneDataset(datatypes_registry=app.datatypes_registry)
                continue

            # Convert LDDA to an HDA.
            if isinstance(data, LibraryDatasetDatasetAssociation) and not completed_job:
                data = data.to_history_dataset_association(None)
                inp_data[name] = data

            if Version(str(tool.profile)) < Version("16.04"):
                input_ext = data.ext

            if data.dbkey not in [None, "?"]:
                input_dbkey = data.dbkey

            identifier = getattr(data, "element_identifier", None)
            if identifier is not None:
                incoming[f"{name}|__identifier__"] = identifier

        # Collect chromInfo dataset and add as parameters to incoming
        (chrom_info, db_dataset) = execution_cache.get_chrom_info(tool.id, input_dbkey)

        if db_dataset:
            inp_data.update({"chromInfo": db_dataset})
        incoming["chromInfo"] = chrom_info

        if not completed_job:
            # Determine output dataset permission/roles list
            if all_permissions:
                output_permissions = app.security_agent.guess_derived_permissions(all_permissions)
            else:
                # No valid inputs, we will use history defaults
                output_permissions = app.security_agent.history_get_default_permissions(history)

        # Add the dbkey to the incoming parameters
        incoming["dbkey"] = input_dbkey
        incoming["__input_ext"] = input_ext
        # wrapped params are used by change_format action and by output.label; only perform this wrapping once, as needed
        wrapped_params = self._wrapped_params(trans, tool, incoming, inp_data)

        out_data: Dict[str, DatasetInstance] = {}
        input_collections = LegacyUnprefixedDict({k: v[0][0] for k, v in inp_dataset_collections.items()})
        input_collections._legacy_mapping = inp_dataset_collections._legacy_mapping
        output_collections = OutputCollections(
            trans,
            history,
            tool=tool,
            tool_action=self,
            input_collections=input_collections,
            dataset_collection_elements=dataset_collection_elements,
            on_text=on_text,
            incoming=incoming,
            params=wrapped_params.params,
            job_params=job_params,
            tags=preserved_tags,
            hdca_tags=preserved_hdca_tags,
        )

        async_tool = tool.tool_type == "data_source_async"

        def handle_output(name, output, hidden=None):
            if async_tool and name in incoming:
                # HACK: output data has already been created as a result of the async controller
                dataid = incoming[name]
                data = trans.sa_session.get(HistoryDatasetAssociation, dataid)
                assert data is not None
                out_data[name] = data
            else:
                ext = determine_output_format(
                    output,
                    wrapped_params.params,
                    inp_data,
                    input_collections,
                    input_ext,
                    python_template_version=tool.python_template_version,
                    execution_cache=execution_cache,
                )
                create_datasets = True
                dataset = None

                if completed_job:
                    for output_dataset in completed_job.output_datasets:
                        if output_dataset.name == name:
                            create_datasets = False
                            completed_data = output_dataset.dataset
                            dataset = output_dataset.dataset.dataset
                            break

                data = app.model.HistoryDatasetAssociation(
                    extension=ext, dataset=dataset, create_dataset=create_datasets, flush=False
                )
                if create_datasets:
                    from_work_dir = output.from_work_dir
                    if from_work_dir is not None:
                        data.dataset.created_from_basename = os.path.basename(from_work_dir)
                if hidden is None:
                    hidden = output.hidden
                if not hidden and dataset_collection_elements is not None:  # Mapping over a collection - hide datasets
                    hidden = True
                if hidden:
                    data.visible = False
                if dataset_collection_elements is not None and name in dataset_collection_elements:
                    dataset_collection_elements[name].hda = data
                trans.sa_session.add(data)
                if not completed_job:
                    trans.app.security_agent.set_all_dataset_permissions(
                        data.dataset, output_permissions, new=True, flush=False
                    )
            data.copy_tags_to(preserved_tags.values())

            # This may not be necessary with the new parent/child associations
            data.designation = name
            # Copy metadata from one of the inputs if requested.

            # metadata source can be either a string referencing an input
            # or an actual object to copy.
            metadata_source = output.metadata_source
            if metadata_source:
                if isinstance(metadata_source, str):
                    metadata_source = inp_data.get(metadata_source)

            if metadata_source is not None:
                data.init_meta(copy_from=metadata_source)
            else:
                data.init_meta()
            # Take dbkey from LAST input
            data.dbkey = str(input_dbkey)
            # Set state
            if completed_job:
                data.blurb = completed_data.blurb
                data.peek = completed_data.peek
                data._metadata = completed_data._metadata
            else:
                data.blurb = "queued"
            # Set output label
            data.name = self.get_output_name(
                output, data, tool, on_text, trans, incoming, history, wrapped_params.params, job_params
            )
            # Store output
            out_data[name] = data
            if output.actions:
                # Apply pre-job tool-output-dataset actions; e.g. setting metadata, changing format
                output_action_params = dict(out_data)
                output_action_params.update(wrapped_params.params)
                output_action_params["__python_template_version__"] = tool.python_template_version
                output.actions.apply_action(data, output_action_params)
            # Flush all datasets at once.
            return data

        child_dataset_names = set()

        for name, output in tool.outputs.items():
            if not filter_output(tool, output, incoming):
                handle_output_timer = ExecutionTimer()
                if output.collection:
                    if completed_job and dataset_collection_elements and name in dataset_collection_elements:
                        # Output collection is mapped over and has already been copied from original job
                        continue
                    collections_manager = app.dataset_collection_manager
                    element_identifiers: List[Dict[str, Union[str, List[Dict[str, Union[str, List[Any]]]]]]] = []
                    # mypy doesn't yet support recursive type definitions
                    known_outputs = output.known_outputs(input_collections, collections_manager.type_registry)
                    # Just to echo TODO elsewhere - this should be restructured to allow
                    # nested collections.
                    for output_part_def in known_outputs:
                        # Add elements to top-level collection, unless nested...
                        current_element_identifiers = element_identifiers
                        current_collection_type = output.structure.collection_type

                        for parent_id in output_part_def.parent_ids or []:
                            # TODO: replace following line with formal abstractions for doing this.
                            current_collection_type = ":".join(current_collection_type.split(":")[1:])
                            name_to_index = {
                                value["name"]: index for (index, value) in enumerate(current_element_identifiers)
                            }
                            if parent_id not in name_to_index:
                                if parent_id not in current_element_identifiers:
                                    index = len(current_element_identifiers)
                                    current_element_identifiers.append(
                                        dict(
                                            name=parent_id,
                                            collection_type=current_collection_type,
                                            src="new_collection",
                                            element_identifiers=[],
                                        )
                                    )
                                else:
                                    index = name_to_index[parent_id]
                            current_element_identifiers = cast(
                                List[
                                    Dict[
                                        str,
                                        Union[str, List[Dict[str, Union[str, List[Any]]]]],
                                    ]
                                ],
                                current_element_identifiers[index]["element_identifiers"],
                            )

                        effective_output_name = output_part_def.effective_output_name
                        child_dataset_names.add(effective_output_name)
                        element = handle_output(effective_output_name, output_part_def.output_def, hidden=True)
                        history.stage_addition(element)
                        # TODO: this shouldn't exist in the top-level of the history at all
                        # but for now we are still working around that by hiding the contents
                        # there.
                        # Following hack causes dataset to no be added to history...
                        trans.sa_session.add(element)
                        current_element_identifiers.append(
                            {
                                "__object__": element,
                                "name": output_part_def.element_identifier,
                            }
                        )

                    if output.dynamic_structure:
                        assert not element_identifiers  # known_outputs must have been empty
                        element_kwds = dict(elements=collections_manager.ELEMENTS_UNINITIALIZED)
                    else:
                        element_kwds = dict(element_identifiers=element_identifiers)
                    output_collections.create_collection(
                        output=output, name=name, completed_job=completed_job, **element_kwds
                    )
                    log.info(f"Handled collection output named {name} for tool {tool.id} {handle_output_timer}")
                else:
                    handle_output(name, output)
                    log.info(f"Handled output named {name} for tool {tool.id} {handle_output_timer}")

        add_datasets_timer = tool.app.execution_timer_factory.get_timer(
            "internals.galaxy.tools.actions.add_datasets",
            "Added output datasets to history",
        )
        # Add all the top-level (non-child) datasets to the history unless otherwise specified
        for name, data in out_data.items():
            if name not in incoming and name not in child_dataset_names:
                # don't add already existing datasets, i.e. async created
                history.stage_addition(data)
        history.add_pending_items(set_output_hid=set_output_hid)

        log.info(add_datasets_timer)
        job_setup_timer = ExecutionTimer()
        # Create the job object
        job, galaxy_session = self._new_job_for_session(trans, tool, history)
        if skip:
            job.state = job.states.SKIPPED
            for output_collection in output_collections.out_collections.values():
                output_collection.mark_as_populated()
            for hdca in output_collections.out_collection_instances.values():
                hdca.visible = False
                hdca.collection.mark_as_populated()
            object_store_populator = ObjectStorePopulator(trans.app, trans.user)
            for data in out_data.values():
                data.set_skipped(object_store_populator)
        job.preferred_object_store_id = preferred_object_store_id
        self._record_inputs(trans, tool, job, incoming, inp_data, inp_dataset_collections)
        self._record_outputs(job, out_data, output_collections)
        # execute immediate post job actions and associate post job actions that are to be executed after the job is complete
        if job_callback:
            job_callback(job)
        if job_params:
            job.params = dumps(job_params)
        if completed_job:
            job.set_copied_from_job_id(completed_job.id)
        trans.sa_session.add(job)
        # Remap any outputs if this is a rerun and the user chose to continue dependent jobs
        # This functionality requires tracking jobs in the database.
        if app.config.track_jobs_in_database and rerun_remap_job_id is not None:
            self._remap_job_on_rerun(
                trans=trans,
                galaxy_session=galaxy_session,
                rerun_remap_job_id=rerun_remap_job_id,
                current_job=job,
                out_data=out_data,
            )
        log.info(f"Setup for job {job.log_str()} complete, ready to be enqueued {job_setup_timer}")

        # Some tools are not really executable, but jobs are still created for them ( for record keeping ).
        # Examples include tools that redirect to other applications ( epigraph ).  These special tools must
        # include something that can be retrieved from the params ( e.g., REDIRECT_URL ) to keep the job
        # from being queued.
        if "REDIRECT_URL" in incoming:
            # Get the dataset - there should only be 1
            for name in inp_data.keys():
                dataset = inp_data[name]
            redirect_url = tool.parse_redirect_url(dataset, incoming)
            # GALAXY_URL should be include in the tool params to enable the external application
            # to send back to the current Galaxy instance
            GALAXY_URL = incoming.get("GALAXY_URL", None)
            assert GALAXY_URL is not None, "GALAXY_URL parameter missing in tool config."
            redirect_url += f"&GALAXY_URL={GALAXY_URL}"
            # Job should not be queued, so set state to ok
            job.set_state(app.model.Job.states.OK)
            job.info = f"Redirected to: {redirect_url}"
            trans.sa_session.add(job)
            with transaction(trans.sa_session):
                trans.sa_session.commit()
            trans.response.send_redirect(redirect_url)
        else:
            if flush_job:
                # Set HID and add to history.
                job_flush_timer = ExecutionTimer()
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
                log.info(f"Flushed transaction for job {job.log_str()} {job_flush_timer}")

        return job, out_data, history

    def _remap_job_on_rerun(
        self,
        trans: ProvidesHistoryContext,
        galaxy_session: Optional[model.GalaxySession],
        rerun_remap_job_id: int,
        current_job: Job,
        out_data,
    ):
        """
        Re-connect dependent datasets for a job that is being rerun (because it failed initially).

        If a job fails, the user has the option to try the job again with changed parameters.
        To be able to resume jobs that depend on this jobs output datasets we change the dependent's job
        input datasets to be those of the job that is being rerun.
        """
        old_job = trans.sa_session.get(Job, rerun_remap_job_id)
        if not old_job:
            # I don't think that can really happen
            raise RequestParameterInvalidException("rerun_remap_job_id parameter is invalid")
        old_tool = trans.app.toolbox.get_tool(old_job.tool_id, exact=False)
        new_tool = trans.app.toolbox.get_tool(current_job.tool_id, exact=False)
        if old_tool and new_tool and old_tool.old_id != new_tool.old_id:
            # If we currently only have the old or new tool installed we'll find the other tool anyway with `exact=False`.
            # If we don't have the tool at all we'll fail anyway, no need to worry here.
            raise RequestParameterInvalidException(
                f"Old tool id ({old_job.tool_id}) does not match rerun tool id ({current_job.tool_id})"
            )
        if trans.user is not None:
            if old_job.user_id != trans.user.id:
                raise RequestParameterInvalidException(
                    "Cannot remap job dependencies for job not created by current user."
                )
        elif trans.user is None and galaxy_session:
            if old_job.session_id != galaxy_session.id:
                raise RequestParameterInvalidException(
                    "Cannot remap job dependencies for job not created by current user."
                )
        else:
            raise AuthenticationRequired("Authentication required to remap job dependencies")
        # Need to flush here so that referencing outputs by id works
        session = trans.sa_session()
        try:
            session.expire_on_commit = False
            with transaction(session):
                session.commit()
        finally:
            session.expire_on_commit = True
        try:
            # Start by hiding current job outputs before taking over the old job's (implicit) outputs.
            current_job.hide_outputs(flush=False)
            # Duplicate PJAs before remap.
            for pjaa in old_job.post_job_actions:
                current_job.add_post_job_action(pjaa.post_job_action)
            if old_job.workflow_invocation_step:
                replacement_dict = {}
                for parameter in old_job.workflow_invocation_step.workflow_invocation.input_parameters:
                    if parameter.type == WorkflowRequestInputParameter.types.REPLACEMENT_PARAMETERS:
                        replacement_dict[parameter.name] = parameter.value
                for pja in old_job.workflow_invocation_step.workflow_step.post_job_actions:
                    # execute immediate actions here, with workflow context.
                    if pja.action_type in ActionBox.immediate_actions:
                        ActionBox.execute(trans.app, trans.sa_session, pja, current_job, replacement_dict)
            for p in old_job.parameters:
                if p.name.endswith("|__identifier__"):
                    current_job.parameters.append(p.copy())
            remapped_hdas = self.__remap_data_inputs(old_job=old_job, current_job=current_job)
            for jtod in old_job.output_datasets:
                for job_to_remap, jtid in [(jtid.job, jtid) for jtid in jtod.dataset.dependent_jobs]:
                    if (trans.user is not None and job_to_remap.user_id == trans.user.id) or (
                        trans.user is None and galaxy_session and job_to_remap.session_id == galaxy_session.id
                    ):
                        self.__remap_parameters(job_to_remap, jtid, jtod, out_data)
                        trans.sa_session.add(job_to_remap)
                        trans.sa_session.add(jtid)
                        job_to_remap.resume()
                jtod.dataset.visible = False
                trans.sa_session.add(jtod)
            for jtodc in old_job.output_dataset_collection_instances:
                # Update JobToOutputDatasetCollectionAssociation to the current job
                jtodc.job = current_job
                hdca = jtodc.dataset_collection_instance
                hdca.collection.replace_failed_elements(remapped_hdas)
                if hdca.implicit_collection_jobs:
                    for job in hdca.implicit_collection_jobs.jobs:
                        if job.job_id == old_job.id:
                            job.job_id = current_job.id
                hdca.update()
            for jtoidca in old_job.output_dataset_collections:
                jtoidca.dataset_collection.replace_failed_elements(remapped_hdas)
        except Exception:
            log.exception("Cannot remap rerun dependencies.")

    def __remap_data_inputs(self, old_job, current_job):
        """Record output datasets from old_job and build a dictionary that maps the old output HDAs to the new output HDAs."""
        remapped_hdas = {}
        old_output_datasets = {jtod.name: jtod.dataset for jtod in old_job.output_datasets}
        for jtod in current_job.output_datasets:
            remapped_hdas[old_output_datasets[jtod.name]] = jtod.dataset
        return remapped_hdas

    def __remap_parameters(self, job_to_remap, jtid, jtod, out_data):
        input_values = {p.name: json.loads(p.value) for p in job_to_remap.parameters if p.value is not None}
        old_dataset_id = jtod.dataset_id
        new_dataset_id = out_data[jtod.name].id
        input_values = update_dataset_ids(input_values, {old_dataset_id: new_dataset_id}, src="hda")
        for p in job_to_remap.parameters:
            if p.name in input_values:
                p.value = json.dumps(input_values[p.name])
        jtid.dataset = out_data[jtod.name]
        jtid.dataset.hid = jtod.dataset.hid
        log.info(f"Job {job_to_remap.id} input HDA {jtod.dataset.id} remapped to new HDA {jtid.dataset.id}")

    def _wrapped_params(self, trans, tool, incoming, input_datasets=None):
        wrapped_params = WrappedParameters(trans, tool, incoming, input_datasets=input_datasets)
        return wrapped_params

    def _get_on_text(self, inp_data):
        input_names = []
        for data in reversed(list(inp_data.values())):
            if getattr(data, "hid", None):
                input_names.append(f"data {data.hid}")

        return on_text_for_names(input_names)

    def _new_job_for_session(self, trans, tool, history) -> Tuple[model.Job, Optional[model.GalaxySession]]:
        job = trans.app.model.Job()
        job.galaxy_version = trans.app.config.version_major
        galaxy_session = None

        if hasattr(trans, "get_galaxy_session"):
            galaxy_session = trans.get_galaxy_session()
            # If we're submitting from the API, there won't be a session.
            if isinstance(galaxy_session, trans.model.GalaxySession):
                job.session_id = model.cached_id(galaxy_session)
        if trans.user is not None:
            job.user_id = model.cached_id(trans.user)
            job.user = trans.user
        if history:
            job.history_id = model.cached_id(history)
        job.tool_id = tool.id
        try:
            # For backward compatibility, some tools may not have versions yet.
            job.tool_version = tool.version
        except AttributeError:
            job.tool_version = "1.0.0"
        job.dynamic_tool = tool.dynamic_tool
        return job, galaxy_session

    def _record_inputs(self, trans, tool, job, incoming, inp_data, inp_dataset_collections):
        # FIXME: Don't need all of incoming here, just the defined parameters
        #        from the tool. We need to deal with tools that pass all post
        #        parameters to the command as a special case.
        reductions: Dict[str, List[str]] = {}
        for name, dataset_collection_info_pairs in inp_dataset_collections.items():
            for dataset_collection, reduced in dataset_collection_info_pairs:
                if reduced:
                    if name not in reductions:
                        reductions[name] = []
                    reductions[name].append(dataset_collection)

                # TODO: verify can have multiple with same name, don't want to lose traceability
                if isinstance(dataset_collection, model.HistoryDatasetCollectionAssociation):
                    job.add_input_dataset_collection(name, dataset_collection)
                elif isinstance(dataset_collection, model.DatasetCollectionElement):
                    job.add_input_dataset_collection_element(name, dataset_collection)

        # If this an input collection is a reduction, we expanded it for dataset security, type
        # checking, and such, but the persisted input must be the original collection
        # so we can recover things like element identifier during tool command evaluation.
        def restore_reduction_visitor(input, value, prefix, parent=None, prefixed_name=None, **kwargs):
            if prefixed_name in reductions and isinstance(input, DataToolParameter):
                target_dict = parent
                if not target_dict:
                    target_dict = incoming

                target_dict[input.name] = []
                for reduced_collection in reductions[prefixed_name]:
                    if hasattr(reduced_collection, "child_collection"):
                        target_dict[input.name].append({"id": model.cached_id(reduced_collection), "src": "dce"})
                    else:
                        target_dict[input.name].append({"id": model.cached_id(reduced_collection), "src": "hdca"})

        if reductions:
            tool.visit_inputs(incoming, restore_reduction_visitor)

        for name, value in tool.params_to_strings(incoming, trans.app).items():
            job.add_parameter(name, value)
        self._record_input_datasets(trans, job, inp_data)

    def _record_outputs(self, job, out_data, output_collections):
        out_collections = output_collections.out_collections
        out_collection_instances = output_collections.out_collection_instances
        for name, dataset in out_data.items():
            job.add_output_dataset(name, dataset)
        for name, dataset_collection in out_collections.items():
            job.add_implicit_output_dataset_collection(name, dataset_collection)
        for name, dataset_collection_instance in out_collection_instances.items():
            job.add_output_dataset_collection(name, dataset_collection_instance)
            dataset_collection_instance.job = job

    def _record_input_datasets(self, trans, job, inp_data):
        for name, dataset in inp_data.items():
            # TODO: figure out why can't pass dataset_id here.
            job.add_input_dataset(name, dataset=dataset)

    def get_output_name(
        self,
        output,
        dataset=None,
        tool=None,
        on_text=None,
        trans=None,
        incoming=None,
        history=None,
        params=None,
        job_params=None,
    ) -> str:
        if output.label:
            params["tool"] = tool
            params["on_string"] = on_text
            return fill_template(output.label, context=params, python_template_version=tool.python_template_version)
        else:
            return self._get_default_data_name(
                dataset,
                tool,
                on_text=on_text,
                trans=trans,
                incoming=incoming,
                history=history,
                params=params,
                job_params=job_params,
            )

    def _get_default_data_name(
        self, dataset, tool, on_text=None, trans=None, incoming=None, history=None, params=None, job_params=None, **kwd
    ):
        name = tool.name
        if on_text:
            name += f" on {on_text}"
        return name


class OutputCollections:
    """Keeps track of collections (DC or HDCA) created by actions.

    Actions do fairly different things depending on whether we are creating
    just part of an collection or a whole output collection (mapping_over_collection
    parameter).
    """

    def __init__(
        self,
        trans,
        history,
        tool,
        tool_action,
        input_collections,
        dataset_collection_elements,
        on_text,
        incoming,
        params,
        job_params,
        tags,
        hdca_tags,
    ):
        self.trans = trans
        self.tag_handler = trans.tag_handler
        self.history = history
        self.tool = tool
        self.tool_action = tool_action
        self.input_collections = input_collections
        self.dataset_collection_elements = dataset_collection_elements
        self.on_text = on_text
        self.incoming = incoming
        self.params = params
        self.job_params = job_params
        self.out_collections = {}
        self.out_collection_instances = {}
        self.tags = tags  # all inherited tags
        self.hdca_tags = hdca_tags  # only tags inherited from input HDCAs

    def create_collection(
        self, output, name, collection_type=None, completed_job=None, propagate_hda_tags=True, **element_kwds
    ):
        input_collections = self.input_collections
        collections_manager = self.trans.app.dataset_collection_manager
        collection_type = collection_type or output.structure.collection_type
        if collection_type is None:
            collection_type_source = output.structure.collection_type_source
            if collection_type_source is None:
                # TODO: Not a new problem, but this should be determined
                # sooner.
                raise Exception("Could not determine collection type to create.")
            if collection_type_source not in input_collections:
                raise Exception(f"Could not find collection type source with name [{collection_type_source}].")

            # Using the collection_type_source string we get the DataCollectionToolParameter
            data_param = self.tool.inputs
            groups = collection_type_source.split("|")
            for group in groups:
                values = group.split("_")
                if values[-1].isdigit():
                    key = "_".join(values[0:-1])
                    # We don't care about the repeat index, we just need to find the correct DataCollectionToolParameter
                else:
                    key = group
                if isinstance(data_param, dict):
                    data_param = data_param.get(key)
                else:
                    data_param = data_param.inputs.get(key)
            collection_type_description = data_param._history_query(self.trans).can_map_over(
                input_collections[collection_type_source]
            )
            if collection_type_description:
                collection_type = collection_type_description.collection_type
            else:
                collection_type = input_collections[collection_type_source].collection.collection_type

        if "elements" in element_kwds:

            def check_elements(elements):
                if hasattr(elements, "items"):  # else it is ELEMENTS_UNINITIALIZED object.
                    for value in elements.values():
                        # Either a HDA (if) or a DatasetCollection or a recursive dict.
                        if getattr(value, "history_content_type", None) == "dataset":
                            assert value.history is not None or value.history_id is not None
                        elif hasattr(value, "dataset_instances"):
                            for dataset in value.dataset_instances:
                                assert dataset.history is not None or dataset.history_id is not None
                        else:
                            assert value["src"] == "new_collection"
                            check_elements(value["elements"])

            elements = element_kwds["elements"]
            check_elements(elements)

        if self.dataset_collection_elements is not None:
            dc = collections_manager.create_dataset_collection(
                self.trans, collection_type=collection_type, **element_kwds
            )
            if name in self.dataset_collection_elements:
                self.dataset_collection_elements[name].child_collection = dc
                # self.trans.sa_session.add(self.dataset_collection_elements[name])
            self.out_collections[name] = dc
        else:
            hdca_name = self.tool_action.get_output_name(
                output,
                None,
                self.tool,
                self.on_text,
                self.trans,
                self.incoming,
                self.history,
                self.params,
                self.job_params,
            )
            hdca = collections_manager.create(
                self.trans,
                self.history,
                name=hdca_name,
                collection_type=collection_type,
                trusted_identifiers=True,
                tags=self.tags if propagate_hda_tags else self.hdca_tags,
                set_hid=False,
                flush=False,
                completed_job=completed_job,
                output_name=name,
                **element_kwds,
            )
            # name here is name of the output element - not name
            # of the hdca.
            self.history.stage_addition(hdca)
            self.out_collection_instances[name] = hdca


def get_ext_or_implicit_ext(hda):
    if hda.implicitly_converted_parent_datasets:
        # implicitly_converted_parent_datasets is a list of ImplicitlyConvertedDatasetAssociation
        # objects, and their type is the target_ext, so this should be correct even if there
        # are multiple ImplicitlyConvertedDatasetAssociation objects (meaning 2 datasets had been converted
        # to produce a dataset with the required datatype)
        return hda.implicitly_converted_parent_datasets[0].type
    return hda.ext


def determine_output_format(
    output: "ToolOutput",
    parameter_context,
    input_datasets,
    input_dataset_collections,
    random_input_ext,
    python_template_version="3",
    execution_cache=None,
):
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
                random_input_ext = get_ext_or_implicit_ext(first_input_dataset)
            except Exception:
                pass
        ext = random_input_ext
    format_source = output.format_source
    if format_source is not None and format_source in input_datasets:
        try:
            input_dataset = input_datasets[output.format_source]
            ext = get_ext_or_implicit_ext(input_dataset)
        except Exception:
            pass
    elif format_source is not None:
        element_index = None
        collection_name = format_source
        if re.match(r"^[^\[\]]*\[[^\[\]]*\]$", format_source):
            collection_name, element_index = format_source[0:-1].split("[")
            # Treat as json to interpret "forward" vs 0 with type
            # Make it feel more like Python, single quote better in XML also.
            element_index = element_index.replace("'", '"')
            element_index = json.loads(element_index)

        if collection_name in input_dataset_collections:
            try:
                input_collection = input_dataset_collections[collection_name]
                input_collection_collection = input_collection.collection
                if element_index is None:
                    # just pick the first HDA
                    input_dataset = input_collection_collection.dataset_instances[0]
                else:
                    try:
                        input_element = input_collection_collection[element_index]
                    except KeyError:
                        if execution_cache:
                            dataset_elements = execution_cache.cached_collection_elements.get(
                                input_collection_collection.id
                            )
                            if dataset_elements is None:
                                dataset_elements = execution_cache.cached_collection_elements[
                                    input_collection_collection.id
                                ] = input_collection_collection.dataset_elements
                        else:
                            dataset_elements = input_collection_collection.dataset_elements
                        for element in dataset_elements:
                            if element.element_identifier == element_index:
                                input_element = element
                                break
                    input_dataset = input_element.element_object
                ext = get_ext_or_implicit_ext(input_dataset)
            except Exception as e:
                log.debug("Exception while trying to determine format_source: %s", e)

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
