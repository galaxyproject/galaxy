import json
import logging
import os
import re
import shlex
import string
import tempfile
from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
    Union,
)

from packaging.version import Version

from galaxy import model
from galaxy.authnz.util import provider_name_to_backend
from galaxy.job_execution.compute_environment import ComputeEnvironment
from galaxy.job_execution.setup import ensure_configs_directory
from galaxy.model.deferred import (
    materialize_collection_input,
    materializer_factory,
)
from galaxy.model.none_like import NoneDataset
from galaxy.security.object_wrapper import wrap_with_safe_string
from galaxy.structured_app import (
    BasicSharedApp,
    MinimalToolApp,
)
from galaxy.tool_util.data import TabularToolDataTable
from galaxy.tools.parameters import (
    visit_input_values,
    wrapped_json,
)
from galaxy.tools.parameters.basic import (
    DataCollectionToolParameter,
    DataToolParameter,
    SelectToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    Repeat,
    Section,
)
from galaxy.tools.wrappers import (
    DatasetCollectionWrapper,
    DatasetFilenameWrapper,
    DatasetListWrapper,
    ElementIdentifierMapper,
    InputValueWrapper,
    RawObjectWrapper,
    SelectToolParameterWrapper,
    ToolParameterValueWrapper,
)
from galaxy.util import (
    find_instance_nested,
    listify,
    RW_R__R__,
    safe_makedirs,
    unicodify,
)
from galaxy.util.template import (
    fill_template,
    InputNotFoundSyntaxError,
)
from galaxy.util.tree_dict import TreeDict
from galaxy.work.context import WorkRequestContext

if TYPE_CHECKING:
    from galaxy.tools import Tool

log = logging.getLogger(__name__)


class ToolErrorLog:
    def __init__(self):
        self.error_stack = []
        self.max_errors = 100

    def add_error(self, file, phase, exception):
        self.error_stack.insert(
            0, {"file": file, "time": str(datetime.now()), "phase": phase, "error": unicodify(exception)}
        )
        if len(self.error_stack) > self.max_errors:
            self.error_stack.pop()


global_tool_errors = ToolErrorLog()


class ToolTemplatingException(Exception):

    def __init__(self, *args: object, tool_id: Optional[str], tool_version: str, is_latest: bool) -> None:
        super().__init__(*args)
        self.tool_id = tool_id
        self.tool_version = tool_version
        self.is_latest = is_latest


def global_tool_logs(func, config_file: str, action_str: str, tool: "Tool"):
    try:
        return func()
    except Exception as e:
        # capture and log parsing errors
        global_tool_errors.add_error(config_file, action_str, e)
        raise ToolTemplatingException(
            f"Error occurred while {action_str.lower()} for tool '{tool.id}'",
            tool_id=tool.id,
            tool_version=tool.version,
            is_latest=tool.is_latest_version,
        ) from e


DeferrableObjectsT = Union[
    model.DatasetInstance, model.HistoryDatasetCollectionAssociation, model.DatasetCollectionElement
]


class ToolEvaluator:
    """An abstraction linking together a tool and a job runtime to evaluate
    tool inputs in an isolated, testable manner.
    """

    app: MinimalToolApp
    job: model.Job
    materialize_datasets: bool = True

    def __init__(self, app: MinimalToolApp, tool, job, local_working_directory):
        self.app = app
        self.job = job
        self.tool = tool
        self.local_working_directory = local_working_directory
        self.file_sources_dict: Dict[str, Any] = {}
        self.param_dict: Dict[str, Any] = {}
        self.extra_filenames: List[str] = []
        self.environment_variables: List[Dict[str, str]] = []
        self.version_command_line: Optional[str] = None
        self.command_line: Optional[str] = None
        self.interactivetools: List[Dict[str, Any]] = []

    def set_compute_environment(self, compute_environment: ComputeEnvironment, get_special: Optional[Callable] = None):
        """
        Setup the compute environment and established the outline of the param_dict
        for evaluating command and config cheetah templates.
        """
        self.compute_environment = compute_environment

        job = self.job
        incoming = {p.name: p.value for p in job.parameters}
        incoming = self.tool.params_from_strings(incoming, self.app)

        self.file_sources_dict = compute_environment.get_file_sources_dict()

        # Full parameter validation
        self._validate_incoming(incoming)

        # Restore input / output data lists
        inp_data, out_data, out_collections = job.io_dicts()

        # collect deferred datasets and collections.
        deferred_objects = self._deferred_objects(inp_data, incoming)

        # materialize deferred datasets
        materialized_objects = self._materialize_objects(deferred_objects, self.local_working_directory)

        # replace materialized objects back into tool input parameters
        self._replaced_deferred_objects(inp_data, incoming, materialized_objects)

        if get_special:
            special = get_special()
            if special:
                out_data["output_file"] = special

        # These can be passed on the command line if wanted as $__user_*__
        incoming.update(model.User.user_template_environment(self._user))

        # Build params, done before hook so hook can use
        self.param_dict = self.build_param_dict(
            incoming,
            inp_data,
            out_data,
            output_collections=out_collections,
        )
        self.execute_tool_hooks(inp_data=inp_data, out_data=out_data, incoming=incoming)

    def execute_tool_hooks(self, inp_data, out_data, incoming):
        # Certain tools require tasks to be completed prior to job execution
        # ( this used to be performed in the "exec_before_job" hook, but hooks are deprecated ).
        self.tool.exec_before_job(self.app, inp_data, out_data, self.param_dict)
        # Run the before queue ("exec_before_job") hook
        self.tool.call_hook(
            "exec_before_job", self.app, inp_data=inp_data, out_data=out_data, tool=self.tool, param_dict=incoming
        )

    def build_param_dict(self, incoming, input_datasets, output_datasets, output_collections):
        """
        Build the dictionary of parameters for substituting into the command
        line. Each value is wrapped in a `InputValueWrapper`, which allows
        all the attributes of the value to be used in the template, *but*
        when the __str__ method is called it actually calls the
        `to_param_dict_string` method of the associated input.
        """
        compute_environment = self.compute_environment
        job_working_directory = compute_environment.working_directory()

        param_dict = TreeDict(self.param_dict)

        param_dict["__datatypes_config__"] = param_dict["GALAXY_DATATYPES_CONF_FILE"] = os.path.join(
            job_working_directory, "registry.xml"
        )
        if self._history:
            param_dict["__history_id__"] = self.app.security.encode_id(self._history.id)
        param_dict["__galaxy_url__"] = self.compute_environment.galaxy_url()
        param_dict.update(self.tool.template_macro_params)
        # All parameters go into the param_dict
        param_dict.update(incoming)

        self.__populate_wrappers(param_dict, input_datasets, job_working_directory)
        self.__populate_input_dataset_wrappers(param_dict, input_datasets)
        self.__populate_output_dataset_wrappers(param_dict, output_datasets, job_working_directory)
        self.__populate_output_collection_wrappers(param_dict, output_collections, job_working_directory)
        self.__populate_unstructured_path_rewrites(param_dict)
        # Call param dict sanitizer, before non-job params are added, as we don't want to sanitize filenames.
        self.__sanitize_param_dict(param_dict)
        # Parameters added after this line are not sanitized
        self.__populate_non_job_params(param_dict)

        # MinimalJobWrapper.__prepare_upload_paramfile copies the paramfile to the job working directory
        # so we should use it (otherwise the upload tool does not work in real user setups)
        if self.job.tool_id == "upload1":
            param_dict["paramfile"] = os.path.join(job_working_directory, "upload_params.json")

        if "input" not in param_dict.data:

            def input():
                raise InputNotFoundSyntaxError(
                    "Unbound variable 'input'."
                )  # Don't let $input hang Python evaluation process.

            param_dict.data["input"] = input

        # Return the dictionary of parameters without injected parameters
        return param_dict.clean_copy()

    def _materialize_objects(
        self, deferred_objects: Dict[str, DeferrableObjectsT], job_working_directory: str
    ) -> Dict[str, DeferrableObjectsT]:
        if not self.materialize_datasets:
            return {}

        undeferred_objects: Dict[str, DeferrableObjectsT] = {}
        transient_directory = os.path.join(job_working_directory, "inputs")
        safe_makedirs(transient_directory)
        dataset_materializer = materializer_factory(
            False,  # unattached to a session.
            transient_directory=transient_directory,
            file_sources=self.app.file_sources,
        )
        for key, value in deferred_objects.items():
            if isinstance(value, model.DatasetInstance):
                if value.state != model.Dataset.states.DEFERRED:
                    continue

                assert isinstance(value, (model.HistoryDatasetAssociation, model.LibraryDatasetDatasetAssociation))
                undeferred = dataset_materializer.ensure_materialized(value)
                undeferred_objects[key] = undeferred
            else:
                undeferred_collection = materialize_collection_input(value, dataset_materializer)
                undeferred_objects[key] = undeferred_collection

        return undeferred_objects

    def _replaced_deferred_objects(
        self,
        inp_data: Dict[str, Optional[model.DatasetInstance]],
        incoming: dict,
        materalized_objects: Dict[str, DeferrableObjectsT],
    ):
        for key, value in materalized_objects.items():
            if isinstance(value, model.DatasetInstance):
                inp_data[key] = value

        def replace_deferred(input, value, context, prefixed_name=None, **kwargs):
            if prefixed_name in materalized_objects:
                return materalized_objects[prefixed_name]

        visit_input_values(self.tool.inputs, incoming, replace_deferred)

    def _validate_incoming(self, incoming: dict):
        request_context = WorkRequestContext(
            app=self.app, user=self._user, history=self._history, galaxy_session=self.job.galaxy_session
        )

        def validate_inputs(input, value, context, **kwargs):
            value = input.from_json(value, request_context, context)
            input.validate(value, request_context)

        visit_input_values(self.tool.inputs, incoming, validate_inputs)

    def _deferred_objects(
        self,
        input_datasets: Dict[str, Optional[model.DatasetInstance]],
        incoming: dict,
    ) -> Dict[str, DeferrableObjectsT]:
        """Collect deferred objects required for execution.

        Walk input datasets and collections and find inputs that need to be materialized.
        """
        deferred_objects: Dict[str, DeferrableObjectsT] = {}
        for key, value in input_datasets.items():
            if value is not None and value.state == model.Dataset.states.DEFERRED:
                if self._should_materialize_deferred_input(key, value):
                    deferred_objects[key] = value

        def find_deferred_collections(input, value, context, prefixed_name=None, **kwargs):
            if (
                isinstance(value, (model.HistoryDatasetCollectionAssociation, model.DatasetCollectionElement))
                and value.has_deferred_data
            ):
                deferred_objects[prefixed_name] = value

        visit_input_values(self.tool.inputs, incoming, find_deferred_collections)

        return deferred_objects

    def _should_materialize_deferred_input(self, input_name: str, input_value: DeferrableObjectsT) -> bool:
        """
        We can skip materializing some deferred datasets if the input can work with URIs that are prefixed
        with a known prefix set in `allow_uri_if_prefixed`.
        """
        deferred_input = self.tool.inputs[input_name]
        if isinstance(deferred_input, DataToolParameter) and isinstance(input_value, model.DatasetInstance):
            source_uri = input_value.sources[0].source_uri or ""
            for prefix in deferred_input.allow_uri_if_prefixed:
                if source_uri.startswith(prefix):
                    return False
        return True

    def __walk_inputs(self, inputs, input_values, func):
        def do_walk(inputs, input_values):
            """
            Wraps parameters as neccesary.
            """
            for input in inputs.values():
                if isinstance(input, Repeat):
                    for d in input_values[input.name]:
                        do_walk(input.inputs, d)
                elif isinstance(input, Conditional):
                    values = input_values[input.name]
                    current = values["__current_case__"]
                    func(values, input.test_param)
                    do_walk(input.cases[current].inputs, values)
                elif isinstance(input, Section):
                    values = input_values[input.name]
                    do_walk(input.inputs, values)
                else:
                    func(input_values, input)

        do_walk(inputs, input_values)

    def __populate_wrappers(self, param_dict, input_datasets, job_working_directory):
        def wrap_input(input_values, input):
            value = input_values[input.name]
            if isinstance(input, DataToolParameter) and input.multiple:
                dataset_instances = DatasetListWrapper.to_dataset_instances(value)
                input_values[input.name] = DatasetListWrapper(
                    job_working_directory,
                    dataset_instances,
                    compute_environment=self.compute_environment,
                    datatypes_registry=self.app.datatypes_registry,
                    tool=self.tool,
                    name=input.name,
                    formats=input.formats,
                )

            elif isinstance(input, DataToolParameter):
                dataset = input_values[input.name]
                wrapper_kwds = dict(
                    datatypes_registry=self.app.datatypes_registry,
                    tool=self.tool,
                    name=input.name,
                    compute_environment=self.compute_environment,
                )
                element_identifier = element_identifier_mapper.identifier(dataset, param_dict)
                if element_identifier:
                    wrapper_kwds["identifier"] = element_identifier
                wrapper_kwds["formats"] = input.formats
                input_values[input.name] = DatasetFilenameWrapper(dataset, **wrapper_kwds)
            elif isinstance(input, DataCollectionToolParameter):
                dataset_collection = value
                wrapper_kwds = dict(
                    datatypes_registry=self.app.datatypes_registry,
                    compute_environment=self.compute_environment,
                    tool=self.tool,
                    name=input.name,
                )
                wrapper = DatasetCollectionWrapper(job_working_directory, dataset_collection, **wrapper_kwds)
                input_values[input.name] = wrapper
            elif isinstance(input, SelectToolParameter):
                if input.multiple:
                    value = listify(value)
                input_values[input.name] = SelectToolParameterWrapper(
                    input, value, other_values=param_dict, compute_environment=self.compute_environment
                )
            else:
                input_values[input.name] = InputValueWrapper(
                    input, value, param_dict, profile=self.tool and self.tool.profile
                )

        # HACK: only wrap if check_values is not false, this deals with external
        #       tools where the inputs don't even get passed through. These
        #       tools (e.g. UCSC) should really be handled in a special way.
        if self.tool.check_values:
            element_identifier_mapper = ElementIdentifierMapper(input_datasets)
            self.__walk_inputs(self.tool.inputs, param_dict, wrap_input)

    def __populate_input_dataset_wrappers(self, param_dict, input_datasets):
        # FIXME: when self.check_values==True, input datasets are being wrapped
        #        twice (above and below, creating 2 separate
        #        DatasetFilenameWrapper objects - first is overwritten by
        #        second), is this necessary? - if we get rid of this way to
        #        access children, can we stop this redundancy, or is there
        #        another reason for this?
        # - Only necessary when self.check_values is False (==external dataset
        #   tool?: can this be abstracted out as part of being a datasouce tool?)
        # For now we try to not wrap unnecessarily, but this should be untangled at some point.
        matches = None
        for name, data in input_datasets.items():
            param_dict_value = param_dict.get(name, None)
            if data and param_dict_value is None:
                # We may have a nested parameter that is not fully prefixed.
                # We try recovering from param_dict, but tool authors should really use fully-qualified
                # variables
                if matches is None:
                    matches = find_instance_nested(param_dict, instances=(DatasetFilenameWrapper, DatasetListWrapper))
                wrapper = matches.get(name)
                if wrapper:
                    param_dict[name] = wrapper
                    continue
            if not isinstance(param_dict_value, ToolParameterValueWrapper):
                wrapper_kwds = dict(
                    datatypes_registry=self.app.datatypes_registry,
                    tool=self.tool,
                    name=name,
                    compute_environment=self.compute_environment,
                )
                param_dict[name] = DatasetFilenameWrapper(data, **wrapper_kwds)

    def __populate_output_collection_wrappers(self, param_dict, output_collections, job_working_directory):
        tool = self.tool
        for name, out_collection in output_collections.items():
            if name not in tool.output_collections:
                continue
                # message_template = "Name [%s] not found in tool.output_collections %s"
                # message = message_template % ( name, tool.output_collections )
                # raise AssertionError( message )

            wrapper_kwds = dict(
                datatypes_registry=self.app.datatypes_registry,
                compute_environment=self.compute_environment,
                io_type="output",
                tool=tool,
                name=name,
            )
            wrapper = DatasetCollectionWrapper(job_working_directory, out_collection, **wrapper_kwds)
            param_dict[name] = wrapper
            # TODO: Handle nested collections...
            for element_identifier, output_def in tool.output_collections[name].outputs.items():
                if not output_def.implicit:
                    dataset_wrapper = wrapper[element_identifier]
                    param_dict[output_def.name] = dataset_wrapper
                    log.info(f"Updating param_dict for {output_def.name} with {dataset_wrapper}")

    def __populate_output_dataset_wrappers(self, param_dict, output_datasets, job_working_directory):
        for name, hda in output_datasets.items():
            # Write outputs to the working directory (for security purposes)
            # if desired.
            param_dict[name] = DatasetFilenameWrapper(
                hda, compute_environment=self.compute_environment, io_type="output"
            )
            if "|__part__|" in name:
                unqualified_name = name.split("|__part__|")[-1]
                if unqualified_name not in param_dict:
                    param_dict[unqualified_name] = param_dict[name]
            output_path = str(param_dict[name])
            # Conditionally create empty output:
            # - may already exist (e.g. symlink output)
            # - parent directory might not exist (e.g. Pulsar)
            # TODO: put into JobIO, needed for fetch_data tasks
            if not os.path.exists(output_path) and os.path.exists(os.path.dirname(output_path)):
                open(output_path, "w").close()

        for out_name, output in self.tool.outputs.items():
            if out_name not in param_dict and output.filters:
                # Assume the reason we lack this output is because a filter
                # failed to pass; for tool writing convienence, provide a
                # NoneDataset
                ext = getattr(output, "format", None)  # populate only for output datasets (not collections)
                param_dict[out_name] = NoneDataset(datatypes_registry=self.app.datatypes_registry, ext=ext)

    def __populate_non_job_params(self, param_dict):
        # -- Add useful attributes/functions for use in creating command line.

        # Function for querying a data table.
        def get_data_table_entry(table_name, query_attr, query_val, return_attr):
            """
            Queries and returns an entry in a data table.
            """
            if table_name in self.app.tool_data_tables:
                table = self.app.tool_data_tables[table_name]
                if not isinstance(table, TabularToolDataTable):
                    raise Exception(f"Expected a TabularToolDataTable but got a {type(table)}: {table}.")
                return table.get_entry(query_attr, query_val, return_attr)

        param_dict["__tool_directory__"] = self.compute_environment.tool_directory()
        param_dict["__get_data_table_entry__"] = get_data_table_entry
        param_dict["__local_working_directory__"] = self.local_working_directory
        # We add access to app here, this allows access to app.config, etc
        param_dict["__app__"] = RawObjectWrapper(self.app)
        # More convienent access to app.config.new_file_path; we don't need to
        # wrap a string, but this method of generating additional datasets
        # should be considered DEPRECATED
        param_dict["__new_file_path__"] = self.compute_environment.new_file_path()
        # The following points to location (xxx.loc) files which are pointers
        # to locally cached data
        param_dict["__tool_data_path__"] = param_dict["GALAXY_DATA_INDEX_DIR"] = self.app.config.tool_data_path
        # For the upload tool, we need to know the root directory and the
        # datatypes conf path, so we can load the datatypes registry
        param_dict["__root_dir__"] = param_dict["GALAXY_ROOT_DIR"] = os.path.abspath(self.app.config.root)
        param_dict["__admin_users__"] = self.app.config.admin_users
        param_dict["__user__"] = RawObjectWrapper(param_dict.get("__user__", None))

    def __populate_unstructured_path_rewrites(self, param_dict):
        def rewrite_unstructured_paths(input_values, input):
            if isinstance(input, SelectToolParameter):
                input_values[input.name] = SelectToolParameterWrapper(
                    input,
                    input_values[input.name],
                    other_values=param_dict,
                    compute_environment=self.compute_environment,
                )

        if not self.tool.check_values and self.compute_environment:
            # The tools weren't "wrapped" yet, but need to be in order to get
            # the paths rewritten.
            self.__walk_inputs(self.tool.inputs, param_dict, rewrite_unstructured_paths)

    def _create_interactivetools_entry_points(self):
        if hasattr(self.app, "interactivetool_manager"):
            self.interactivetools = self._populate_interactivetools_template()
            self.app.interactivetool_manager.create_interactivetool(self.job, self.tool, self.interactivetools)

    def _populate_interactivetools_template(self):
        """
        Populate InteractiveTools templated values.
        """
        it = []
        for ep in getattr(self.tool, "ports", []):
            ep_dict = {}
            for key in (
                "port",
                "name",
                "label",
                "url",
                "requires_domain",
                "requires_path_in_url",
                "requires_path_in_header_named",
            ):
                val = ep.get(key, None)
                if val is not None and not isinstance(val, bool):
                    val = fill_template(
                        val, context=self.param_dict, python_template_version=self.tool.python_template_version
                    )
                    clean_val = []
                    for line in val.split("\n"):
                        clean_val.append(line.strip())
                    val = "\n".join(clean_val)
                    val = val.replace("\n", " ").replace("\r", " ").strip()
                ep_dict[key] = val
            it.append(ep_dict)
        return it

    def __sanitize_param_dict(self, param_dict):
        """
        Sanitize all values that will be substituted on the command line, with the exception of ToolParameterValueWrappers,
        which already have their own specific sanitization rules and also exclude special-cased named values.
        We will only examine the first level for values to skip; the wrapping function will recurse as necessary.

        Note: this method follows the style of the similar populate calls, in that param_dict is modified in-place.
        """
        # chromInfo is a filename, do not sanitize it.
        skip = ["chromInfo"] + list(self.tool.template_macro_params.keys())
        if not self.tool or not self.tool.options or self.tool.options.sanitize:
            for key, value in list(param_dict.items()):
                if key not in skip:
                    # Remove key so that new wrapped object will occupy key slot
                    del param_dict[key]
                    # And replace with new wrapped key
                    param_dict[wrap_with_safe_string(key, no_wrap_classes=ToolParameterValueWrapper)] = (
                        wrap_with_safe_string(value, no_wrap_classes=ToolParameterValueWrapper)
                    )

    def build(self):
        """
        Build runtime description of job to execute, evaluate command and
        config templates corresponding to this tool with these inputs on this
        compute environment.
        """
        config_file = self.tool.config_file
        global_tool_logs(
            self._create_interactivetools_entry_points, config_file, "Building Interactive Tool Entry Points", self.tool
        )
        global_tool_logs(
            self._build_config_files,
            config_file,
            "Building Config Files",
            self.tool,
        )
        global_tool_logs(self._build_param_file, config_file, "Building Param File", self.tool)
        global_tool_logs(self._build_command_line, config_file, "Building Command Line", self.tool)
        global_tool_logs(self._build_version_command, config_file, "Building Version Command Line", self.tool)
        global_tool_logs(self._build_environment_variables, config_file, "Building Environment Variables", self.tool)
        return (
            self.command_line,
            self.version_command_line,
            self.extra_filenames,
            self.environment_variables,
            self.interactivetools,
        )

    def _build_command_line(self):
        """
        Build command line to invoke this tool given a populated param_dict
        """
        command = self.tool.command or ""
        param_dict = self.param_dict
        interpreter = self.tool.interpreter
        command_line = None
        if not command:
            return
        try:
            # Substituting parameters into the command
            command_line = fill_template(
                command, context=param_dict, python_template_version=self.tool.python_template_version
            )
            cleaned_command_line = []
            # Remove leading and trailing whitespace from each line for readability.
            for line in command_line.split("\n"):
                cleaned_command_line.append(line.strip())
            command_line = "\n".join(cleaned_command_line)
            # Remove newlines from command line, and any leading/trailing white space
            command_line = command_line.replace("\n", " ").replace("\r", " ").strip()
        except Exception:
            # Modify exception message to be more clear
            # e.args = ( 'Error substituting into command line. Params: %r, Command: %s' % ( param_dict, self.command ), )
            raise
        if interpreter:
            # TODO: path munging for cluster/dataset server relocatability
            executable = command_line.split()[0]
            tool_dir = os.path.abspath(self.tool.tool_dir)
            abs_executable = os.path.join(tool_dir, executable)
            command_line = command_line.replace(executable, f"{interpreter} {shlex.quote(abs_executable)}", 1)
        self.command_line = command_line

    def _build_version_command(self):
        if version_string_cmd_raw := self.tool.version_string_cmd:
            version_command_template = string.Template(version_string_cmd_raw)
            version_command = version_command_template.safe_substitute(
                {"__tool_directory__": self.compute_environment.tool_directory()}
            )
            self.version_command_line = f"{version_command} > {self.compute_environment.version_path()} 2>&1;\n"

    def _build_config_files(self):
        """
        Build temporary file for file based parameter transfer if needed
        """
        param_dict = self.param_dict
        config_filenames = []
        for name, filename, content in self.tool.config_files:
            config_text, is_template = self.__build_config_file_text(content)
            # If a particular filename was forced by the config use it
            directory = ensure_configs_directory(self.local_working_directory)
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temp:
                config_filename = temp.name
            if filename is not None:
                # Explicit filename was requested, this is implemented as symbolic link
                # to the actual config file that is placed in tool working directory
                directory = os.path.join(self.local_working_directory, "working")
                os.link(config_filename, os.path.join(directory, filename))
            self.__write_workdir_file(config_filename, config_text, param_dict, is_template=is_template)
            self.__register_extra_file(name, config_filename)
            config_filenames.append(config_filename)
        return config_filenames

    def _build_environment_variables(self):
        param_dict = self.param_dict
        environment_variables = self.environment_variables
        for environment_variable_def in self.tool.environment_variables:
            directory = self.local_working_directory
            environment_variable = environment_variable_def.copy()
            environment_variable_template = environment_variable_def["template"]
            inject = environment_variable_def.get("inject")
            if inject == "api_key":
                if self._user and isinstance(self.app, BasicSharedApp):
                    from galaxy.managers import api_keys

                    environment_variable_template = api_keys.ApiKeyManager(self.app).get_or_create_api_key(self._user)
                else:
                    environment_variable_template = ""
                is_template = False
            elif inject and inject.startswith("oidc_"):
                environment_variable_template = self.get_oidc_token(inject)
                is_template = False
            elif inject and inject == "entry_point_path_for_label" and environment_variable_template:
                from galaxy.managers.interactivetool import InteractiveToolManager

                entry_point_label = environment_variable_template
                matching_eps = [ep for ep in self.job.interactivetool_entry_points if ep.label == entry_point_label]
                if matching_eps:
                    entry_point = matching_eps[0]
                    entry_point_path = InteractiveToolManager(self.app).get_entry_point_path(self.app, entry_point)
                    environment_variable_template = entry_point_path.rstrip("/")
                else:
                    environment_variable_template = ""
                is_template = False
            else:
                is_template = True
            with tempfile.NamedTemporaryFile(dir=directory, prefix="tool_env_", delete=False) as temp:
                config_filename = temp.name
            self.__write_workdir_file(
                config_filename,
                environment_variable_template,
                param_dict,
                is_template=is_template,
                strip=environment_variable_def.get("strip", False),
            )
            config_file_basename = os.path.basename(config_filename)
            # environment setup in job file template happens before `cd $working_directory`
            environment_variable["value"] = (
                f'`cat "{self.compute_environment.env_config_directory()}/{config_file_basename}"`'
            )
            environment_variable["raw"] = True
            environment_variable["job_directory_path"] = config_filename
            environment_variables.append(environment_variable)

        if home_dir := self.compute_environment.home_directory():
            environment_variable = dict(name="HOME", value=f'"{home_dir}"', raw=True)
            environment_variables.append(environment_variable)
        if tmp_dir := self.compute_environment.tmp_directory():
            for tmp_directory_var in self.tool.tmp_directory_vars:
                environment_variable = dict(name=tmp_directory_var, value=f'"{tmp_dir}"', raw=True)
                environment_variables.append(environment_variable)

    def get_oidc_token(self, inject):
        if not self._user:
            return "token-unavailable"

        p = re.compile("^oidc_(id|access|refresh)_token_(.*)$")
        match = p.match(inject)
        provider_backend = None
        if match:
            token_type = match.group(1)
            provider_backend = provider_name_to_backend(match.group(2))
        if not match or not provider_backend:
            return "token-unavailable"

        tokens = self._user.get_oidc_tokens(provider_backend)
        environment_variable_template = tokens[token_type] or "token-unavailable"

        return environment_variable_template

    def _build_param_file(self):
        """
        Build temporary file for file based parameter transfer if needed
        """
        param_dict = self.param_dict
        directory = self.local_working_directory
        command = self.tool.command
        if Version(str(self.tool.profile)) < Version("16.04") and command and "$param_file" in command:
            with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as param:
                for key, value in param_dict.items():
                    # parameters can be strings or lists of strings, coerce to list
                    if not isinstance(value, list):
                        value = [value]
                    for elem in value:
                        param.write(f"{key}={elem}\n")
            self.__register_extra_file("param_file", param.name)
            return param.name
        else:
            return None

    def __build_config_file_text(self, content):
        if isinstance(content, str):
            return content, True

        config_type = content.get("type", "inputs")
        if config_type == "inputs":
            content_format = content["format"]
            handle_files = content["handle_files"]
            if content_format != "json":
                template = "Galaxy can only currently convert inputs to json, format [%s] is unhandled"
                message = template % content_format
                raise Exception(message)
        elif config_type == "files":
            file_sources_dict = self.file_sources_dict
            rval = json.dumps(file_sources_dict)
            return rval, False
        else:
            raise Exception(f"Unknown config file type {config_type}")

        return (
            json.dumps(
                wrapped_json.json_wrap(self.tool.inputs, self.param_dict, self.tool.profile, handle_files=handle_files)
            ),
            False,
        )

    def __write_workdir_file(self, config_filename, content, context, is_template=True, strip=False):
        parent_dir = os.path.dirname(config_filename)
        if not os.path.exists(parent_dir):
            safe_makedirs(parent_dir)
        if is_template:
            value = fill_template(content, context=context, python_template_version=self.tool.python_template_version)
        else:
            value = unicodify(content)
        if strip:
            value = value.strip()
        with open(config_filename, "w", encoding="utf-8") as f:
            f.write(value)
        # For running jobs as the actual user, ensure the config file is globally readable
        os.chmod(config_filename, RW_R__R__)

    def __register_extra_file(self, name, local_config_path):
        """
        Takes in the local path to a config file and registers the (potentially
        remote) ultimate path of the config file with the parameter dict.
        """
        self.extra_filenames.append(local_config_path)
        config_basename = os.path.basename(local_config_path)
        compute_config_path = self.__join_for_compute(self.compute_environment.config_directory(), config_basename)
        self.param_dict[name] = compute_config_path

    def __join_for_compute(self, *args):
        """
        os.path.join but with compute_environment.sep for cross-platform
        compat.
        """
        return self.compute_environment.sep().join(args)

    @property
    def _history(self):
        return self.job.history

    @property
    def _user(self):
        if history := self._history:
            return history.user
        else:
            return self.job.user


class PartialToolEvaluator(ToolEvaluator):
    """
    ToolEvaluator that only builds Environment Variables.
    """

    materialize_datasets = False

    def build(self):
        config_file = self.tool.config_file
        global_tool_logs(self._build_environment_variables, config_file, "Building Environment Variables", self.tool)
        return (
            self.command_line,
            self.version_command_line,
            self.extra_filenames,
            self.environment_variables,
            self.interactivetools,
        )


class RemoteToolEvaluator(ToolEvaluator):
    """ToolEvaluator that skips unnecessary steps already executed during job setup."""

    materialize_datasets = True

    def execute_tool_hooks(self, inp_data, out_data, incoming):
        # These have already run while preparing the job
        pass

    def build(self):
        config_file = self.tool.config_file
        global_tool_logs(self._build_config_files, config_file, "Building Config Files", self.tool)
        global_tool_logs(self._build_param_file, config_file, "Building Param File", self.tool)
        global_tool_logs(self._build_command_line, config_file, "Building Command Line", self.tool)
        global_tool_logs(self._build_version_command, config_file, "Building Version Command Line", self.tool)
        return (
            self.command_line,
            self.version_command_line,
            self.extra_filenames,
            self.environment_variables,
            self.interactivetools,
        )
