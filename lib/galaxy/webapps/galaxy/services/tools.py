import logging
import os
import shutil
import tempfile
from json import dumps
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from fastapi.responses import FileResponse
from starlette.datastructures import UploadFile

from galaxy import (
    exceptions,
    util,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions.utils import api_error_to_dict
from galaxy.managers.collections_util import dictify_dataset_collection_instance
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.histories import HistoryManager
from galaxy.model import (
    LibraryDatasetDatasetAssociation,
    PostJobAction,
)
from galaxy.schema.fetch_data import (
    FetchDataFormPayload,
    FetchDataPayload,
    FilesPayload,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tools import Tool
from galaxy.tools.search import ToolBoxSearch
from galaxy.util.path import safe_contains
from galaxy.webapps.galaxy.services._fetch_util import validate_and_normalize_targets
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class ToolsService(ServiceBase):
    def __init__(
        self,
        config: GalaxyAppConfiguration,
        toolbox_search: ToolBoxSearch,
        security: IdEncodingHelper,
        history_manager: HistoryManager,
    ):
        super().__init__(security)
        self.config = config
        self.toolbox_search = toolbox_search
        self.history_manager = history_manager

    def create_fetch(
        self,
        trans: ProvidesHistoryContext,
        fetch_payload: Union[FetchDataFormPayload, FetchDataPayload],
        files: Optional[List[UploadFile]] = None,
    ):
        payload = fetch_payload.model_dump(exclude_unset=True)
        request_version = "1"
        history_id = payload.pop("history_id")
        clean_payload = {}
        files_payload = {}
        if files:
            for i, upload_file in enumerate(files):
                with tempfile.NamedTemporaryFile(
                    dir=trans.app.config.new_file_path, prefix="upload_file_data_", delete=False
                ) as dest:
                    shutil.copyfileobj(upload_file.file, dest)
                    util.umask_fix_perms(dest.name, trans.app.config.umask, 0o0666)
                upload_file.file.close()
                files_payload[f"files_{i}|file_data"] = FilesPayload(
                    filename=upload_file.filename, local_filename=dest.name
                )
        for key, value in payload.items():
            if key == "key":
                continue
            if key.startswith("files_") or key.startswith("__files_"):
                files_payload[key] = value
                continue
            clean_payload[key] = value
        clean_payload["check_content"] = self.config.check_upload_content
        validate_and_normalize_targets(trans, clean_payload)
        request = dumps(clean_payload)
        create_payload = {
            "tool_id": "__DATA_FETCH__",
            "history_id": history_id,
            "inputs": {
                "request_version": request_version,
                "request_json": request,
                "file_count": str(len(files_payload)),
            },
        }
        create_payload.update(files_payload)
        return self._create(trans, create_payload)

    def _create(self, trans: ProvidesHistoryContext, payload, **kwd):
        if trans.user_is_bootstrap_admin:
            raise exceptions.RealUserRequiredException("Only real users can execute tools or run jobs.")
        action = payload.get("action")
        if action == "rerun":
            raise Exception("'rerun' action has been deprecated")

        # Get tool.
        tool_version = payload.get("tool_version")
        tool_id = payload.get("tool_id")
        tool_uuid = payload.get("tool_uuid")
        get_kwds = dict(
            tool_id=tool_id,
            tool_uuid=tool_uuid,
            tool_version=tool_version,
        )
        if tool_id is None and tool_uuid is None:
            raise exceptions.RequestParameterMissingException("Must specify either a tool_id or a tool_uuid.")

        tool = trans.app.toolbox.get_tool(**get_kwds)
        if not tool:
            log.debug(f"Not found tool with kwds [{get_kwds}]")
            raise exceptions.ToolMissingException("Tool not found.")
        if not tool.allow_user_access(trans.user):
            raise exceptions.ItemAccessibilityException("Tool not accessible.")
        if self.config.user_activation_on:
            if not trans.user:
                log.warning("Anonymous user attempts to execute tool, but account activation is turned on.")
            elif not trans.user.active:
                log.warning(
                    f'User "{trans.user.email}" attempts to execute tool, but account activation is turned on and user account is not active.'
                )

        # Set running history from payload parameters.
        # History not set correctly as part of this API call for
        # dataset upload.
        if history_id := payload.get("history_id"):
            history_id = trans.security.decode_id(history_id) if isinstance(history_id, str) else history_id
            target_history = self.history_manager.get_mutable(history_id, trans.user, current_history=trans.history)
        else:
            target_history = None

        # Set up inputs.
        inputs = payload.get("inputs", {})
        if not isinstance(inputs, dict):
            raise exceptions.RequestParameterInvalidException(f"inputs invalid {inputs}")

        # Find files coming in as multipart file data and add to inputs.
        for k, v in payload.items():
            if k.startswith("files_") or k.startswith("__files_"):
                inputs[k] = v

        # for inputs that are coming from the Library, copy them into the history
        self._patch_library_inputs(trans, inputs, target_history)

        # TODO: encode data ids and decode ids.
        # TODO: handle dbkeys
        params = util.Params(inputs, sanitize=False)
        incoming = params.__dict__

        # use_cached_job can be passed in via the top-level payload or among the tool inputs.
        # I think it should be a top-level parameter, but because the selector is implemented
        # as a regular tool parameter we accept both.
        use_cached_job = payload.get("use_cached_job", False) or util.string_as_bool(
            inputs.get("use_cached_job", "false")
        )
        preferred_object_store_id = payload.get("preferred_object_store_id")
        input_format = str(payload.get("input_format", "legacy"))
        if "data_manager_mode" in payload:
            incoming["__data_manager_mode"] = payload["data_manager_mode"]
        vars = tool.handle_input(
            trans,
            incoming,
            history=target_history,
            use_cached_job=use_cached_job,
            input_format=input_format,
            preferred_object_store_id=preferred_object_store_id,
        )

        new_pja_flush = False
        for job in vars.get("jobs", []):
            if inputs.get("send_email_notification", False):
                # Unless an anonymous user is invoking this via the API it
                # should never be an option, but check and enforce that here
                if trans.user is None:
                    raise exceptions.ToolExecutionError("Anonymously run jobs cannot send an email notification.")
                else:
                    job_email_action = PostJobAction("EmailAction")
                    job.add_post_job_action(job_email_action)
                    new_pja_flush = True

        if new_pja_flush:
            trans.sa_session.commit()

        return self._handle_inputs_output_to_api_response(trans, tool, target_history, vars)

    def _handle_inputs_output_to_api_response(self, trans, tool, target_history, vars):
        # TODO: check for errors and ensure that output dataset(s) are available.
        output_datasets = vars.get("out_data", [])
        rval: Dict[str, Any] = {"outputs": [], "output_collections": [], "jobs": [], "implicit_collections": []}
        rval["produces_entry_points"] = tool.produces_entry_points
        if job_errors := vars.get("job_errors", []):
            # If we are here - some jobs were successfully executed but some failed.
            # TODO: We should probably alter the response status code and have a component that knows
            # how to template in things like src and id, so we don't have to rely just on a textual error message.
            execution_errors = [
                (
                    trans.security.encode_all_ids(api_error_to_dict(exception=e))
                    if isinstance(e, exceptions.MessageException)
                    else e
                )
                for e in job_errors
            ]
            rval["errors"] = execution_errors

        outputs = rval["outputs"]
        # TODO:?? poss. only return ids?
        for output_name, output in output_datasets:
            output_dict = output.to_dict()
            # add the output name back into the output data structure
            # so it's possible to figure out which newly created elements
            # correspond with which tool file outputs
            output_dict["output_name"] = output_name
            outputs.append(output_dict)

        for job in vars.get("jobs", []):
            rval["jobs"].append(job.to_dict(view="collection"))

        for output_name, collection_instance in vars.get("output_collections", []):
            history = target_history or trans.history
            output_dict = dictify_dataset_collection_instance(
                collection_instance,
                security=trans.security,
                url_builder=trans.url_builder,
                parent=history,
            )
            output_dict["output_name"] = output_name
            rval["output_collections"].append(output_dict)

        for output_name, collection_instance in vars.get("implicit_collections", {}).items():
            history = target_history or trans.history
            output_dict = dictify_dataset_collection_instance(
                collection_instance,
                security=trans.security,
                url_builder=trans.url_builder,
                parent=history,
            )
            output_dict["output_name"] = output_name
            rval["implicit_collections"].append(output_dict)

        trans.security.encode_all_ids(rval, recursive=True)
        return rval

    def _search(self, q, view):
        """
        Perform the search on the given query.
        Boosts and numer of results are configurable in galaxy.ini file.

        :param q: the query to search with
        :type  q: str

        :return:      Dictionary containing the tools' ids of the best hits.
        :return type: dict
        """
        panel_view = view or self.config.default_panel_view

        results = self.toolbox_search.search(
            q=q,
            panel_view=panel_view,
            config=self.config,
        )
        return results

    def _patch_library_inputs(self, trans: ProvidesHistoryContext, inputs, target_history):
        """
        Transform inputs from the data library to history items.
        """
        for k, v in inputs.items():
            new_value = self._patch_library_dataset(trans, v, target_history)
            if new_value:
                v = new_value
            elif isinstance(v, dict) and "values" in v:
                for index, value in enumerate(v["values"]):
                    patched = self._patch_library_dataset(trans, value, target_history)
                    if patched:
                        v["values"][index] = patched
            inputs[k] = v

    def _patch_library_dataset(self, trans: ProvidesHistoryContext, v, target_history):
        if isinstance(v, dict) and "id" in v and v.get("src") == "ldda":
            ldda = trans.sa_session.get(LibraryDatasetDatasetAssociation, self.decode_id(v["id"]))
            if not ldda:
                raise exceptions.ObjectNotFound("Could not find library dataset dataset association.")
            if trans.user_is_admin or trans.app.security_agent.can_access_dataset(
                trans.get_current_user_roles(), ldda.dataset
            ):
                return ldda.to_history_dataset_association(target_history, add_to_history=True)

    #
    # -- Helper methods --
    #
    def _get_tool(self, trans, id, tool_version=None, user=None) -> Tool:
        tool = trans.app.toolbox.get_tool(id, tool_version)
        if not tool:
            raise exceptions.ObjectNotFound(f"Could not find tool with id '{id}'.")
        if not tool.allow_user_access(user):
            raise exceptions.AuthenticationFailed(f"Access denied, please login for tool with id '{id}'.")
        return tool

    def _detect(self, trans: ProvidesUserContext, tool_id):
        """
        Detect whether the tool with the given id is installed.

        :param tool_id: exact id of the tool
        :type tool_id:  str

        :return:      list with available versions
        "return type: list
        """
        tools = trans.app.toolbox.get_tool(tool_id, get_all_versions=True)
        detected_versions = []
        if tools:
            for tool in tools:
                if tool and tool.allow_user_access(trans.user):
                    detected_versions.append(tool.version)
        return detected_versions

    def get_tool_icon(self, trans, tool_id, tool_version=None):
        tool = self._get_tool(trans, tool_id, tool_version)
        if tool and tool.icon:
            icon_src = tool.icon.get("src")
            if icon_src and tool.tool_dir:
                # Prevent any path traversal attacks. The icon_src must be in the tool's directory.
                if not safe_contains(tool.tool_dir, icon_src):
                    raise Exception(
                        f"Invalid icon path for tool '{tool_id}'. Path must be within the tool's directory."
                    )
                file_path = os.path.join(tool.tool_dir, icon_src)
                if not os.path.exists(file_path):
                    raise exceptions.ObjectNotFound(f"Could not find icon for tool '{tool_id}'.")
                return FileResponse(file_path)
        return None
