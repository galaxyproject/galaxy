import logging
import os
from datetime import (
    datetime,
    timezone,
)
from json import loads
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
)

from fastapi import (
    Body,
    Depends,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from galaxy import (
    exceptions,
    util,
    web,
)
from galaxy.datatypes.data import get_params_and_input_name
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.hdas import HDAManager
from galaxy.managers.histories import HistoryManager
from galaxy.schema.fetch_data import (
    FetchDataFormPayload,
    FetchDataPayload,
)
from galaxy.tool_util.verify import ToolTestDescriptionDict
from galaxy.tool_util_models import UserToolSource
from galaxy.tools.evaluation import global_tool_errors
from galaxy.util.hash_util import (
    HashFunctionNameEnum,
    memory_bound_hexdigest,
)
from galaxy.util.zipstream import ZipstreamWrapper
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless,
)
from galaxy.webapps.base.controller import UsesVisualizationMixin
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from galaxy.webapps.galaxy.services.tools import ToolsService
from . import (
    APIContentTypeRoute,
    as_form,
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

# Do not allow these tools to be called directly - they (it) enforces extra security and
# provides access via a different API endpoint.
PROTECTED_TOOLS = ["__DATA_FETCH__"]
# Tool search bypasses the fulltext for the following list of terms
SEARCH_RESERVED_TERMS_FAVORITES = ["#favs", "#favorites", "#favourites"]

ICON_CACHE_MAX_AGE = 2592000  # 30 days


class FormDataApiRoute(APIContentTypeRoute):
    match_content_type = "multipart/form-data"


class JsonApiRoute(APIContentTypeRoute):
    match_content_type = "application/json"


class PNGIconResponse(FileResponse):
    media_type = "image/png"


router = Router(tags=["tools"])

FetchDataForm = as_form(FetchDataFormPayload)


async def get_files(request: Request, files: Optional[List[UploadFile]] = None):
    # FastAPI's UploadFile is a very light wrapper around starlette's UploadFile
    files2: List[StarletteUploadFile] = cast(List[StarletteUploadFile], files or [])
    if not files2:
        data = await request.form()
        for value in data.values():
            if isinstance(value, StarletteUploadFile):
                files2.append(value)
    return files2


@router.cbv
class FetchTools:
    service: ToolsService = depends(ToolsService)

    @router.post("/api/tools/fetch", summary="Upload files to Galaxy", route_class_override=JsonApiRoute)
    def fetch_json(self, payload: FetchDataPayload = Body(...), trans: ProvidesHistoryContext = DependsOnTrans):
        return self.service.create_fetch(trans, payload)

    @router.post(
        "/api/tools/fetch",
        summary="Upload files to Galaxy",
        route_class_override=FormDataApiRoute,
    )
    def fetch_form(
        self,
        payload: FetchDataFormPayload = Depends(FetchDataForm.as_form),
        trans: ProvidesHistoryContext = DependsOnTrans,
        files: List[StarletteUploadFile] = Depends(get_files),
    ):
        return self.service.create_fetch(trans, payload, files)

    @router.get(
        "/api/tools/{tool_id:path}/icon",
        summary="Get the icon image associated with a tool",
        response_class=PNGIconResponse,
        responses={
            200: {
                "content": {"image/png": {}},
                "description": "Tool icon image in PNG format",
            },
            304: {
                "description": "Tool icon image has not been modified since the last request",
            },
            404: {
                "description": "Tool icon file not found or not provided by the tool",
            },
        },
    )
    def get_icon(self, request: Request, tool_id: str, trans: ProvidesHistoryContext = DependsOnTrans):
        """Returns the icon image associated with a tool.

        The icon image is served with caching headers to allow for efficient
        client-side caching. The icon image is expected to be in PNG format.
        """
        tool_icon_path = self.service.get_tool_icon_path(trans=trans, tool_id=tool_id)
        if tool_icon_path is None:
            raise exceptions.ObjectNotFound(f"Tool icon file not found or not provided by the tool: {tool_id}")

        # Get file modification time
        file_stat = os.stat(tool_icon_path)
        last_modified = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

        # Check If-Modified-Since
        if_modified_since = request.headers.get("If-Modified-Since")
        if if_modified_since == last_modified:
            return Response(status_code=304)

        # Generate ETag based on file content
        file_hash = memory_bound_hexdigest(hash_func_name=HashFunctionNameEnum.md5, path=tool_icon_path)
        etag = f'"{file_hash}"'

        # Check If-None-Match (ETag)
        if_none_match = request.headers.get("If-None-Match", "").split(",")
        if any(etag.strip() == e.strip(' W/"') for e in if_none_match):  # Handle weak ETags
            return Response(status_code=304)

        # Serve the file with caching headers
        response = PNGIconResponse(tool_icon_path)
        response.headers["Cache-Control"] = f"public, max-age={ICON_CACHE_MAX_AGE}, immutable"
        response.headers["ETag"] = etag
        response.headers["Last-Modified"] = last_modified
        return response


class ToolsController(BaseGalaxyAPIController, UsesVisualizationMixin):
    """
    RESTful controller for interactions with tools.
    """

    history_manager: HistoryManager = depends(HistoryManager)
    hda_manager: HDAManager = depends(HDAManager)
    hdca_manager: DatasetCollectionManager = depends(DatasetCollectionManager)
    service: ToolsService = depends(ToolsService)

    @expose_api_anonymous_and_sessionless
    def index(self, trans: GalaxyWebTransaction, **kwds):
        """
        GET /api/tools

        returns a list of tools defined by parameters

        :param in_panel: if true, tools are returned in panel structure,
                         including sections and labels
        :param view: ToolBox view to apply (default is 'default')
        :param trackster: if true, only tools that are compatible with
                          Trackster are returned
        :param q: if present search on the given query will be performed
        :param tool_id: if present the given tool_id will be searched for
                        all installed versions
        """

        # Read params.
        in_panel = util.string_as_bool(kwds.get("in_panel", "True"))
        trackster = util.string_as_bool(kwds.get("trackster", "False"))
        q = kwds.get("q", "")
        tool_id = kwds.get("tool_id", "")
        tool_help = util.string_as_bool(kwds.get("tool_help", "False"))
        view = kwds.get("view", None)

        # Find whether to search.
        if q:
            if trans.user and q in SEARCH_RESERVED_TERMS_FAVORITES:
                if "favorites" in trans.user.preferences:
                    favorites = loads(trans.user.preferences["favorites"])
                    hits = favorites["tools"]
                else:
                    hits = None
            else:
                hits = self.service._search(q, view)
            results = []
            if hits:
                for hit in hits:
                    try:
                        tool = self.service._get_tool(trans, hit, user=trans.user)
                        if tool:
                            results.append(tool.id)
                    except exceptions.AuthenticationFailed:
                        pass
                    except exceptions.ObjectNotFound:
                        pass
            return results

        # Find whether to detect.
        if tool_id:
            detected_versions = self.service._detect(trans, tool_id)
            return detected_versions

        # Return everything.
        try:
            return self.app.toolbox.to_dict(
                trans, in_panel=in_panel, trackster=trackster, tool_help=tool_help, view=view
            )
        except exceptions.MessageException:
            raise
        except Exception:
            raise exceptions.InternalServerError("Error: Could not convert toolbox to dictionary")

    @expose_api_anonymous_and_sessionless
    def panel_views(self, trans: GalaxyWebTransaction, **kwds):
        """
        GET /api/tool_panels
        returns a dictionary of available tool panel views and default view
        """

        rval = {}
        rval["default_panel_view"] = self.app.toolbox._default_panel_view(trans)
        rval["views"] = self.app.toolbox.panel_view_dicts()
        return rval

    @expose_api_anonymous_and_sessionless
    def panel_view(self, trans: GalaxyWebTransaction, view, **kwds):
        """
        GET /api/tool_panels/{view}

        returns a dictionary of tools and tool sections for the given view

        :param trackster: if true, only tools that are compatible with
                          Trackster are returned
        """

        # Read param.
        trackster = util.string_as_bool(kwds.get("trackster", "False"))

        # Return panel view.
        try:
            return self.app.toolbox.to_panel_view(trans, trackster=trackster, view=view)
        except exceptions.MessageException:
            raise
        except Exception:
            raise exceptions.InternalServerError("Error: Could not convert toolbox to dictionary")

    @expose_api_anonymous_and_sessionless
    def show(self, trans: GalaxyWebTransaction, id, **kwd):
        """
        GET /api/tools/{tool_id}

        Returns tool information

            parameters:

                io_details   - if true, parameters and inputs are returned
                link_details - if true, hyperlink to the tool is returned
                tool_version - if provided return this tool version
        """
        io_details = util.string_as_bool(kwd.get("io_details", False))
        link_details = util.string_as_bool(kwd.get("link_details", False))
        tool_version = kwd.get("tool_version")
        tool = self.service._get_tool(trans, id, user=trans.user, tool_version=tool_version)
        return tool.to_dict(trans, io_details=io_details, link_details=link_details)

    @expose_api_anonymous
    def build(self, trans: GalaxyWebTransaction, id, **kwd):
        """
        GET /api/tools/{tool_id}/build
        Returns a tool model including dynamic parameters and updated values, repeats block etc.
        """
        kwd = _kwd_or_payload(kwd)
        tool_version = kwd.get("tool_version")
        tool_uuid = kwd.get("tool_uuid")
        history = None
        if history_id := kwd.pop("history_id", None):
            history = self.history_manager.get_owned(
                self.decode_id(history_id), trans.user, current_history=trans.history
            )
        tool = self.service._get_tool(trans, id, tool_version=tool_version, user=trans.user, tool_uuid=tool_uuid)
        return tool.to_json(trans, kwd.get("inputs", kwd), history=history)

    @web.require_admin
    @expose_api
    def test_data_path(self, trans: GalaxyWebTransaction, id, **kwd):
        """
        GET /api/tools/{tool_id}/test_data_path?tool_version={tool_version}
        """
        kwd = _kwd_or_payload(kwd)
        tool_version = kwd.get("tool_version", None)
        tool = self.service._get_tool(trans, id, tool_version=tool_version, user=trans.user)
        try:
            path = tool.test_data_path(kwd.get("filename"))
        except ValueError as e:
            raise exceptions.MessageException(str(e))
        if path:
            return path
        else:
            raise exceptions.ObjectNotFound("Specified test data path not found.")

    @expose_api_raw_anonymous_and_sessionless
    def test_data_download(self, trans: GalaxyWebTransaction, id, **kwd):
        """
        GET /api/tools/{tool_id}/test_data_download?tool_version={tool_version}&filename={filename}
        """
        tool_version = kwd.get("tool_version", None)
        tool = self.service._get_tool(trans, id, tool_version=tool_version, user=trans.user)
        filename = kwd.get("filename")
        if filename is None:
            raise exceptions.ObjectNotFound("Test data filename not specified.")
        if path := tool.test_data_path(filename):
            if os.path.isfile(path):
                trans.response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
                return open(path, mode="rb")
            elif os.path.isdir(path):
                # Set upstream_mod_zip to false, otherwise tool data must be among allowed internal routes
                archive = ZipstreamWrapper(
                    upstream_mod_zip=False,
                    upstream_gzip=self.app.config.upstream_gzip,
                    archive_name=filename,
                )
                archive.write(path)
                trans.response.headers.update(archive.get_headers())
                return archive.response()
        raise exceptions.ObjectNotFound("Specified test data path not found.")

    @expose_api_anonymous_and_sessionless
    def tests_summary(self, trans: GalaxyWebTransaction, **kwd):
        """
        GET /api/tools/tests_summary

        Fetch summary information for each tool and version combination with tool tests
        defined. This summary information currently includes tool name and a count of
        the tests.

        Fetch complete test data for each tool with /api/tools/{tool_id}/test_data?tool_version=<tool_version>
        """
        test_counts_by_tool: Dict[str, Dict] = {}
        for _id, tool in self.app.toolbox.tools():
            if not tool.is_datatype_converter:
                tests = tool.tests
                if tests:
                    if tool.id not in test_counts_by_tool:
                        test_counts_by_tool[tool.id] = {}
                    available_versions = test_counts_by_tool[tool.id]
                    available_versions[tool.version] = {
                        "tool_name": tool.name,
                        "count": len(tests),
                    }
        return test_counts_by_tool

    @expose_api_anonymous_and_sessionless
    def test_data(self, trans: GalaxyWebTransaction, id, **kwd) -> List[ToolTestDescriptionDict]:
        """
        GET /api/tools/{tool_id}/test_data?tool_version={tool_version}

        This API endpoint is unstable and experimental. In particular the format of the
        response has not been entirely nailed down (it exposes too many Galaxy
        internals/Pythonisms in a rough way). If this endpoint is being used from outside
        of scripts shipped with Galaxy let us know and please be prepared for the response
        from this API to change its format in some ways.

        If tool version is not passed, it is assumed to be latest. Tool version can be
        set as '*' to get tests for all configured versions.
        """
        kwd = _kwd_or_payload(kwd)
        tool_version = kwd.get("tool_version", None)
        if tool_version == "*":
            tools = self.app.toolbox.get_tool(id, get_all_versions=True)
            for tool in tools:
                if not tool.allow_user_access(trans.user):
                    raise exceptions.AuthenticationFailed(f"Access denied, please login for tool with id '{id}'.")
        else:
            tools = [self.service._get_tool(trans, id, tool_version=tool_version, user=trans.user)]

        test_defs = []
        for tool in tools:
            test_defs.extend([t.to_dict() for t in tool.tests])
        return test_defs

    @web.require_admin
    @expose_api
    def reload(self, trans: GalaxyWebTransaction, id, **kwd):
        """
        GET /api/tools/{tool_id}/reload
        Reload specified tool.
        """
        trans.app.queue_worker.send_control_task("reload_tool", noop_self=True, kwargs={"tool_id": id})
        message, status = trans.app.toolbox.reload_tool_by_id(id)
        if status == "error":
            raise exceptions.MessageException(message)
        return {"message": message}

    @web.require_admin
    @expose_api
    def all_requirements(self, trans: GalaxyWebTransaction, **kwds):
        """
        GET /api/tools/all_requirements
        Return list of unique requirements for all tools.
        """

        return trans.app.toolbox.all_requirements

    @web.require_admin
    @expose_api
    def requirements(self, trans: GalaxyWebTransaction, id, **kwds):
        """
        GET /api/tools/{tool_id}/requirements
        Return the resolver status for a specific tool id.
        [{"status": "installed", "name": "hisat2", "versionless": false, "resolver_type": "conda", "version": "2.0.3", "type": "package"}]
        """
        tool = self.service._get_tool(trans, id, user=trans.user)
        return tool.tool_requirements_status

    @web.require_admin
    @expose_api
    def install_dependencies(self, trans: GalaxyWebTransaction, id, **kwds):
        """
        POST /api/tools/{tool_id}/dependencies

        This endpoint is also available through POST /api/tools/{tool_id}/install_dependencies,
        but will be deprecated in the future.

        Attempts to install requirements via the dependency resolver

        parameters:
            index:
                index of dependency resolver to use when installing dependency.
                Defaults to using the highest ranking resolver

            resolver_type:           Use the dependency resolver of this resolver_type to install dependency.
            build_dependency_cache:  If true, attempts to cache dependencies for this tool
            force_rebuild:           If true and cache dir exists, attempts to delete cache dir
        """
        tool = self.service._get_tool(trans, id, user=trans.user)
        tool._view.install_dependencies(tool.requirements, **kwds)
        if kwds.get("build_dependency_cache"):
            tool.build_dependency_cache(**kwds)
        # TODO: rework resolver install system to log and report what has been done.
        # _view.install_dependencies should return a dict with stdout, stderr and success status
        return tool.tool_requirements_status

    @web.require_admin
    @expose_api
    def uninstall_dependencies(self, trans: GalaxyWebTransaction, id, **kwds):
        """
        DELETE /api/tools/{tool_id}/dependencies

        Attempts to uninstall requirements via the dependency resolver

        parameters:

            index:

                index of dependency resolver to use when installing dependency.
                Defaults to using the highest ranking resolver

            resolver_type: Use the dependency resolver of this resolver_type to install dependency
        """
        tool = self.service._get_tool(trans, id, user=trans.user)
        tool._view.uninstall_dependencies(requirements=tool.requirements, **kwds)
        # TODO: rework resolver install system to log and report what has been done.
        return tool.tool_requirements_status

    @web.require_admin
    @expose_api
    def build_dependency_cache(self, trans: GalaxyWebTransaction, id, **kwds):
        """
        POST /api/tools/{tool_id}/build_dependency_cache
        Attempts to cache installed dependencies.

        parameters:
            force_rebuild:           If true and chache dir exists, attempts to delete cache dir
        """
        tool = self.service._get_tool(trans, id)
        tool.build_dependency_cache(**kwds)
        # TODO: Should also have a more meaningful return.
        return tool.tool_requirements_status

    @web.require_admin
    @expose_api
    def diagnostics(self, trans: GalaxyWebTransaction, id, **kwd):
        """
        GET /api/tools/{tool_id}/diagnostics
        Return diagnostic information to help debug panel
        and dependency related problems.
        """

        # TODO: Move this into tool.
        def to_dict(x):
            return x.to_dict()

        tool = self.service._get_tool(trans, id, user=trans.user)
        if hasattr(tool, "lineage"):
            lineage_dict = tool.lineage.to_dict()
        else:
            lineage_dict = None
        tool_shed_dependencies_dict: Optional[list] = None
        if tool_shed_dependencies := tool.installed_tool_dependencies:
            tool_shed_dependencies_dict = list(map(to_dict, tool_shed_dependencies))
        return {
            "tool_id": tool.id,
            "tool_version": tool.version,
            "dependency_shell_commands": tool.build_dependency_shell_commands(),
            "lineage": lineage_dict,
            "requirements": list(map(to_dict, tool.requirements)),
            "installed_tool_shed_dependencies": tool_shed_dependencies_dict,
            "tool_dir": tool.tool_dir,
            "tool_shed": tool.tool_shed,
            "repository_name": tool.repository_name,
            "repository_owner": tool.repository_owner,
            "installed_changeset_revision": None,
            "guid": tool.guid,
        }

    @expose_api_anonymous_and_sessionless
    def citations(self, trans: GalaxyWebTransaction, id, **kwds):
        tool = self.service._get_tool(trans, id, user=trans.user)
        rval = []
        for citation in tool.citations:
            rval.append(citation.to_dict("bibtex"))
        return rval

    @expose_api
    def conversion(self, trans: GalaxyWebTransaction, tool_id, payload, **kwd):
        converter = self.service._get_tool(trans, tool_id, user=trans.user)
        target_type = payload.get("target_type")
        source_type = payload.get("source_type")
        input_src = payload.get("src")
        input_id = payload.get("id")
        # List of string of dependencies
        try:
            deps = trans.app.datatypes_registry.converter_deps[source_type][target_type]
        except KeyError:
            deps = {}
        # Generate parameter dictionary
        params, input_name = get_params_and_input_name(converter, deps)
        params = {}
        # determine input parameter name and add to params

        params[input_name] = {
            "values": [
                {
                    "id": input_id,
                    "src": input_src,
                }
            ],
            "batch": input_src == "hdca",
        }
        if history_id := payload.get("history_id"):
            decoded_id = self.decode_id(history_id)
            target_history = self.history_manager.get_owned(decoded_id, trans.user, current_history=trans.history)
        else:
            if input_src == "hdca":
                hdca = self.hdca_manager.get_dataset_collection_instance(trans, instance_type="history", id=input_id)
                assert hdca.history
                target_history = hdca.history
            elif input_src == "hda":
                decoded_id = trans.app.security.decode_id(input_id)
                hda = self.hda_manager.get_accessible(decoded_id, trans.user)
                assert hda.history
                target_history = hda.history
                self.history_manager.error_unless_owner(target_history, trans.user, current_history=trans.history)
            else:
                raise exceptions.RequestParameterInvalidException("Must run conversion on either hdca or hda.")

        self.history_manager.error_unless_mutable(target_history)

        # Make the target datatype available to the converter
        params["__target_datatype__"] = target_type
        vars = converter.handle_input(trans, params, history=target_history)
        return self.service._handle_inputs_output_to_api_response(trans, converter, target_history, vars)

    @expose_api_anonymous_and_sessionless
    def xrefs(self, trans: GalaxyWebTransaction, id, **kwds):
        tool = self.service._get_tool(trans, id, user=trans.user)
        return tool.xrefs

    @web.require_admin
    @web.legacy_expose_api_raw
    def download(self, trans: GalaxyWebTransaction, id, **kwds):
        tool_tarball = trans.app.toolbox.package_tool(trans, id)
        trans.response.set_content_type("application/x-gzip")
        download_file = open(tool_tarball, "rb")
        trans.response.headers["Content-Disposition"] = f'attachment; filename="{id}.tgz"'
        return download_file

    @expose_api_raw_anonymous_and_sessionless
    def raw_tool_source(self, trans: GalaxyWebTransaction, id, **kwds):
        """Returns tool source. ``language`` is included in the response header."""
        if not trans.app.config.enable_tool_source_display and not trans.user_is_admin:
            raise exceptions.InsufficientPermissionsException(
                "Only administrators may display tool sources on this Galaxy server."
            )
        tool = self.service._get_tool(trans, id, user=trans.user, tool_version=kwds.get("tool_version"), tool_uuid=id)
        trans.response.headers["language"] = tool.tool_source.language
        if dynamic_tool := getattr(tool, "dynamic_tool", None):
            if dynamic_tool.value.get("class") == "GalaxyUserTool":
                return UserToolSource(**dynamic_tool.value).model_dump_json(
                    by_alias=True,
                    exclude_defaults=True,
                    exclude_unset=True,
                )
        return tool.tool_source.to_string()

    @web.require_admin
    @expose_api
    def error_stack(self, trans: GalaxyWebTransaction, **kwd):
        """
        GET /api/tools/error_stack
        Returns global tool error stack
        """
        return global_tool_errors.error_stack

    @expose_api_anonymous
    def create(self, trans: GalaxyWebTransaction, payload, **kwd):
        """
        POST /api/tools
        Execute tool with a given parameter payload

        :param input_format: input format for the payload. Possible values are
          the default 'legacy' (where inputs nested inside conditionals or
          repeats are identified with e.g. '<conditional_name>|<input_name>') or
          '21.01' (where inputs inside conditionals or repeats are nested
          elements).
        :type input_format: str
        """
        tool_id = payload.get("tool_id")
        tool_uuid = payload.get("tool_uuid")
        if tool_id in PROTECTED_TOOLS:
            raise exceptions.RequestParameterInvalidException(
                f"Cannot execute tool [{tool_id}] directly, must use alternative endpoint."
            )
        if tool_id is None and tool_uuid is None:
            raise exceptions.RequestParameterInvalidException("Must specify a valid tool_id to use this endpoint.")
        return self.service._create(trans, payload, **kwd)


def _kwd_or_payload(kwd: Dict[str, Any]) -> Dict[str, Any]:
    if "payload" in kwd:
        kwd = cast(Dict[str, Any], kwd.get("payload"))
    return kwd
