import json
import logging
from time import strftime
from typing import (
    List,
    Optional,
)

from fastapi import (
    Path,
    Query,
)
from paste.httpexceptions import (
    HTTPBadRequest,
    HTTPForbidden,
)

from galaxy import (
    exceptions,
    util,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    CheckForUpdatesResponse,
    InstalledToolShedRepositories,
    InstalledToolShedRepository,
)
from galaxy.tool_shed.galaxy_install.install_manager import InstallRepositoryManager
from galaxy.tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from galaxy.tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import (
    InstalledRepositoryMetadataManager,
)
from galaxy.tool_shed.util.repository_util import (
    get_installed_repository,
    get_installed_tool_shed_repository,
    get_tool_shed_repository_by_id,
)
from galaxy.tool_shed.util.shed_util_common import have_shed_tool_conf_for_install
from galaxy.tool_shed.util.tool_util import generate_message_for_invalid_tools
from galaxy.web import (
    expose_api,
    require_admin,
)
from galaxy.webapps.galaxy.api import (
    BaseGalaxyAPIController,
    depends,
    Router,
)
from galaxy.webapps.galaxy.services.tool_shed_repositories import (
    InstalledToolShedRepositoryIndexRequest,
    ToolShedRepositoriesService,
)

log = logging.getLogger(__name__)


router = Router(tags=["tool_shed_repositories"])


def get_message_for_no_shed_tool_config():
    # This Galaxy instance is not configured with a shed-related tool panel configuration file.
    message = "The tool_config_file setting in galaxy.ini must include at least one shed tool configuration file name with a <toolbox> "
    message += "tag that includes a tool_path attribute value which is a directory relative to the Galaxy installation directory in order to "
    message += "automatically install tools from a tool shed into Galaxy (e.g., the file name shed_tool_conf.xml whose <toolbox> tag is "
    message += '<toolbox tool_path="database/shed_tools">).  For details, see the "Installation of Galaxy tool shed repository tools into a '
    message += 'local Galaxy instance" section of the Galaxy tool shed wiki at https://galaxyproject.org/installing-repositories-to-galaxy/'
    return message


class ToolShedRepositoriesController(BaseGalaxyAPIController):
    """RESTful controller for interactions with tool shed repositories."""

    service: ToolShedRepositoriesService = depends(ToolShedRepositoriesService)

    def __ensure_can_install_repos(self, trans):
        # Make sure this Galaxy instance is configured with a shed-related tool panel configuration file.
        if not have_shed_tool_conf_for_install(self.app):
            message = get_message_for_no_shed_tool_config()
            log.debug(message)
            return dict(status="error", error=message)
        # Make sure the current user's API key proves he is an admin user in this Galaxy instance.
        if not trans.user_is_admin:
            raise exceptions.AdminRequiredException(
                "You are not authorized to request the latest installable revision for a repository in this Galaxy instance."
            )

    @require_admin
    @expose_api
    def install_repository_revision(self, trans: ProvidesUserContext, payload, **kwd):
        """
        POST /api/tool_shed_repositories/install_repository_revision
        Install a specified repository revision from a specified tool shed into Galaxy.

        :param key: the current Galaxy admin user's API key

        The following parameters are included in the payload.
        :param tool_shed_url (required): the base URL of the Tool Shed from which to install the Repository
        :param name (required): the name of the Repository
        :param owner (required): the owner of the Repository
        :param changeset_revision (required): the changeset_revision of the RepositoryMetadata object associated with the Repository
        :param new_tool_panel_section_label (optional):

            label of a new section to be added to the Galaxy tool panel in which to load
            tools contained in the Repository.  Either this parameter must be an empty string or
            the tool_panel_section_id parameter must be an empty string or both must be an empty
            string (both cannot be used simultaneously).

        :param tool_panel_section_id (optional):

            id of the Galaxy tool panel section in which to load tools contained in the Repository.
            If this parameter is an empty string and the above new_tool_panel_section_label parameter is an
            empty string, tools will be loaded outside of any sections in the tool panel.  Either this
            parameter must be an empty string or the tool_panel_section_id parameter must be an empty string
            of both must be an empty string (both cannot be used simultaneously).

        :param install_repository_dependencies (optional):

            Set to True if you want to install repository dependencies defined for the specified
            repository being installed.  The default setting is False.

        :param install_tool_dependencies (optional):

            Set to True if you want to install tool dependencies defined for the specified repository being
            installed.  The default setting is False.

        :param shed_tool_conf (optional):

            The shed-related tool panel configuration file configured in the "tool_config_file" setting in the Galaxy config file
            (e.g., galaxy.ini).  At least one shed-related tool panel config file is required to be configured. Setting
            this parameter to a specific file enables you to choose where the specified repository will be installed because
            the tool_path attribute of the <toolbox> from the specified file is used as the installation location
            (e.g., <toolbox tool_path="database/shed_tools">).  If this parameter is not set, a shed-related tool panel
            configuration file will be selected automatically.

        """
        # Get the information about the repository to be installed from the payload.
        tool_shed_url, name, owner, changeset_revision = self.__parse_repository_from_payload(
            payload, include_changeset=True
        )
        self.__ensure_can_install_repos(trans)
        irm = InstallRepositoryManager(self.app)
        installed_tool_shed_repositories = irm.install(tool_shed_url, name, owner, changeset_revision, payload)
        if installed_tool_shed_repositories:
            return InstalledToolShedRepositories(
                __root__=list(map(self.service._show, installed_tool_shed_repositories))
            )
        message = "No repositories were installed, possibly because the selected repository has already been installed."
        return dict(status="ok", message=message)

    @require_admin
    @expose_api
    def install_repository_revisions(self, trans, payload, **kwd):
        """
        POST /api/tool_shed_repositories/install_repository_revisions
        Install one or more specified repository revisions from one or more specified tool sheds into Galaxy.  The received parameters
        must be ordered lists so that positional values in tool_shed_urls, names, owners and changeset_revisions are associated.

        It's questionable whether this method is needed as the above method for installing a single repository can probably cover all
        desired scenarios.  We'll keep this one around just in case...

        :param key: the current Galaxy admin user's API key

        The following parameters are included in the payload.
        :param tool_shed_urls: the base URLs of the Tool Sheds from which to install a specified Repository
        :param names: the names of the Repositories to be installed
        :param owners: the owners of the Repositories to be installed
        :param changeset_revisions: the changeset_revisions of each RepositoryMetadata object associated with each Repository to be installed
        :param new_tool_panel_section_label:

            optional label of a new section to be added to the Galaxy tool panel in which to load
            tools contained in the Repository.  Either this parameter must be an empty string or
            the tool_panel_section_id parameter must be an empty string, as both cannot be used.

        :param tool_panel_section_id:

            optional id of the Galaxy tool panel section in which to load tools contained in the Repository.
            If not set, tools will be loaded outside of any sections in the tool panel.  Either this
            parameter must be an empty string or the tool_panel_section_id parameter must be an empty string,
            as both cannot be used.

        :param install_repository_dependencies (optional):

            Set to True if you want to install repository dependencies defined for the specified
            repository being installed.  The default setting is False.

        :param install_tool_dependencies (optional):

            Set to True if you want to install tool dependencies defined for the specified repository being
            installed.  The default setting is False.

        :param shed_tool_conf (optional):

            The shed-related tool panel configuration file configured in the "tool_config_file" setting in the Galaxy config file
            (e.g., galaxy.ini).  At least one shed-related tool panel config file is required to be configured. Setting
            this parameter to a specific file enables you to choose where the specified repository will be installed because
            the tool_path attribute of the <toolbox> from the specified file is used as the installation location
            (e.g., <toolbox tool_path="database/shed_tools">).  If this parameter is not set, a shed-related tool panel
            configuration file will be selected automatically.

        """
        self.__ensure_can_install_repos(trans)
        # Get the information about all of the repositories to be installed.
        tool_shed_urls = util.listify(payload.get("tool_shed_urls", ""))
        names = util.listify(payload.get("names", ""))
        owners = util.listify(payload.get("owners", ""))
        changeset_revisions = util.listify(payload.get("changeset_revisions", ""))
        num_specified_repositories = len(tool_shed_urls)
        if (
            len(names) != num_specified_repositories
            or len(owners) != num_specified_repositories
            or len(changeset_revisions) != num_specified_repositories
        ):
            message = "Error in tool_shed_repositories API in install_repository_revisions: the received parameters must be ordered "
            message += "lists so that positional values in tool_shed_urls, names, owners and changeset_revisions are associated."
            log.debug(message)
            return dict(status="error", error=message)
        # Get the information about the Galaxy components (e.g., tool pane section, tool config file, etc) that will contain information
        # about each of the repositories being installed.
        # TODO: we may want to enhance this method to allow for each of the following to be associated with each repository instead of
        # forcing all repositories to use the same settings.
        install_repository_dependencies = payload.get("install_repository_dependencies", False)
        install_resolver_dependencies = payload.get("install_resolver_dependencies", False)
        install_tool_dependencies = payload.get("install_tool_dependencies", False)
        new_tool_panel_section_label = payload.get("new_tool_panel_section_label", "")
        shed_tool_conf = payload.get("shed_tool_conf", None)
        tool_panel_section_id = payload.get("tool_panel_section_id", "")
        all_installed_tool_shed_repositories = []
        for tool_shed_url, name, owner, changeset_revision in zip(tool_shed_urls, names, owners, changeset_revisions):
            current_payload = dict(
                tool_shed_url=tool_shed_url,
                name=name,
                owner=owner,
                changeset_revision=changeset_revision,
                new_tool_panel_section_label=new_tool_panel_section_label,
                tool_panel_section_id=tool_panel_section_id,
                install_repository_dependencies=install_repository_dependencies,
                install_resolver_dependencies=install_resolver_dependencies,
                install_tool_dependencies=install_tool_dependencies,
                shed_tool_conf=shed_tool_conf,
            )
            installed_tool_shed_repositories = self.install_repository_revision(trans, **current_payload)
            if isinstance(installed_tool_shed_repositories, dict):
                # We encountered an error.
                return installed_tool_shed_repositories
            elif isinstance(installed_tool_shed_repositories, InstalledToolShedRepositories):
                all_installed_tool_shed_repositories.extend(installed_tool_shed_repositories.__root__)
        return InstalledToolShedRepositories(__root__=all_installed_tool_shed_repositories)

    @require_admin
    @expose_api
    def uninstall_repository(self, trans, id=None, **kwd):
        """
        DELETE /api/tool_shed_repositories/id
        DELETE /api/tool_shed_repositories/

        :param id:  encoded repository id. Either id or name, owner, changeset_revision and tool_shed_url need to be supplied
        :param kwd:

            'remove_from_disk': Remove repository from disk or deactivate repository. Defaults to `True` (= remove repository from disk).
            'name': Repository name
            'owner': Repository owner
            'changeset_revision': Changeset revision to uninstall
            'tool_shed_url': Tool Shed URL

        """
        remove_from_disk = util.asbool(kwd.get("remove_from_disk", True))
        if id:
            try:
                repository = get_tool_shed_repository_by_id(self.app, id)
            except ValueError:
                raise HTTPBadRequest(detail=f"No repository with id '{id}' found")
        else:
            tsr_arguments = ["name", "owner", "changeset_revision", "tool_shed_url"]
            try:
                tsr_arguments = {key: kwd[key] for key in tsr_arguments}
            except KeyError as e:
                raise HTTPBadRequest(detail=f"Missing required parameter '{e.args[0]}'")
            repository = get_installed_repository(
                app=self.app,
                tool_shed=tsr_arguments["tool_shed_url"],
                name=tsr_arguments["name"],
                owner=tsr_arguments["owner"],
                changeset_revision=tsr_arguments["changeset_revision"],
            )
            if not repository:
                raise HTTPBadRequest(detail="Repository not found")
        irm = InstalledRepositoryManager(app=self.app)
        errors = irm.uninstall_repository(repository=repository, remove_from_disk=remove_from_disk)
        if not errors:
            action = "removed" if remove_from_disk else "deactivated"
            return {"message": f"The repository named {repository.name} has been {action}."}
        else:
            raise Exception(
                f"Attempting to uninstall tool dependencies for repository named {repository.name} resulted in errors: {errors}"
            )

    def __parse_repository_from_payload(self, payload, include_changeset=False):
        # Get the information about the repository to be installed from the payload.
        tool_shed_url = payload.get("tool_shed_url", "")
        if not tool_shed_url:
            raise exceptions.RequestParameterMissingException("Missing required parameter 'tool_shed_url'.")
        name = payload.get("name", "")
        if not name:
            raise exceptions.RequestParameterMissingException("Missing required parameter 'name'.")
        owner = payload.get("owner", "")
        if not owner:
            raise exceptions.RequestParameterMissingException("Missing required parameter 'owner'.")
        if not include_changeset:
            return tool_shed_url, name, owner

        changeset_revision = payload.get("changeset_revision", "")
        if not changeset_revision:
            raise HTTPBadRequest(detail="Missing required parameter 'changeset_revision'.")

        return tool_shed_url, name, owner, changeset_revision

    @require_admin
    @expose_api
    def reset_metadata_on_selected_installed_repositories(self, trans, **kwd):
        repository_ids = util.listify(kwd.get("repository_ids"))
        if repository_ids:
            irmm = InstalledRepositoryMetadataManager(self.app)
            failed = []
            successful = []
            for repository_id in repository_ids:
                try:
                    repository = get_installed_tool_shed_repository(self.app, repository_id)
                    irmm.set_repository(repository)
                    irmm.reset_all_metadata_on_installed_repository()
                    if irmm.invalid_file_tups:
                        failed.append(repository_id)
                    else:
                        successful.append(repository_id)
                except Exception:
                    failed.append(repository_id)
            if successful:
                message = f"Successful reset of metadata for {len(successful)}."
                if failed:
                    message += f" Failed for {len(failed)}."
            elif failed:
                message = f"Failed to reset metadata for {len(failed)}."
            return dict(message=message, successful=successful, failed=failed)
        else:
            raise exceptions.MessageException("Please specify repository ids [repository_ids].")

    @expose_api
    def reset_metadata_on_installed_repositories(self, trans, payload, **kwd):
        """
        PUT /api/tool_shed_repositories/reset_metadata_on_installed_repositories

        Resets all metadata on all repositories installed into Galaxy in an "orderly fashion".

        :param key: the API key of the Galaxy admin user.
        """
        start_time = strftime("%Y-%m-%d %H:%M:%S")
        results = dict(start_time=start_time, successful_count=0, unsuccessful_count=0, repository_status=[])
        # Make sure the current user's API key proves he is an admin user in this Galaxy instance.
        if not trans.user_is_admin:
            raise HTTPForbidden(
                detail="You are not authorized to reset metadata on repositories installed into this Galaxy instance."
            )
        irmm = InstalledRepositoryMetadataManager(self.app)
        query = irmm.get_query_for_setting_metadata_on_repositories(order=False)
        # Now reset metadata on all remaining repositories.
        for repository in query:
            try:
                irmm.set_repository(repository)
                irmm.reset_all_metadata_on_installed_repository()
                irmm_invalid_file_tups = irmm.get_invalid_file_tups()
                if irmm_invalid_file_tups:
                    message = generate_message_for_invalid_tools(
                        self.app, irmm_invalid_file_tups, repository, None, as_html=False
                    )
                    results["unsuccessful_count"] += 1
                else:
                    message = f"Successfully reset metadata on repository {repository.name} owned by {repository.owner}"
                    results["successful_count"] += 1
            except Exception as e:
                message = f"Error resetting metadata on repository {repository.name} owned by {repository.owner}: {e}"
                results["unsuccessful_count"] += 1
            results["repository_status"].append(message)
        stop_time = strftime("%Y-%m-%d %H:%M:%S")
        results["stop_time"] = stop_time
        return json.dumps(results, sort_keys=True, indent=4)


InstalledToolShedRepositoryIDPathParam: DecodedDatabaseIdField = Path(
    ...,
    title="Installed Tool Shed Repository ID",
    description="The encoded database identifier of the installed Tool Shed Repository.",
)

NameQueryParam: Optional[str] = Query(default=None, title="Name", description="Filter by repository name.")

OwnerQueryParam: Optional[str] = Query(default=None, title="Owner", description="Filter by repository owner.")

ChangesetQueryParam: Optional[str] = Query(default=None, title="Changeset", description="Filter by changeset revision.")

DeletedQueryParam: Optional[bool] = Query(
    default=None, title="Deleted?", description="Filter by whether the repository has been deleted."
)

UninstalledQueryParam: Optional[bool] = Query(
    default=None, title="Uninstalled?", description="Filter by whether the repository has been uninstalled."
)


@router.cbv
class FastAPIToolShedRepositories:
    service: ToolShedRepositoriesService = depends(ToolShedRepositoriesService)

    @router.get(
        "/api/tool_shed_repositories",
        summary="Lists installed tool shed repositories.",
        response_description="A list of installed tool shed repository objects.",
    )
    def index(
        self,
        name: Optional[str] = NameQueryParam,
        owner: Optional[str] = OwnerQueryParam,
        changeset: Optional[str] = ChangesetQueryParam,
        deleted: Optional[bool] = DeletedQueryParam,
        uninstalled: Optional[bool] = UninstalledQueryParam,
    ) -> List[InstalledToolShedRepository]:
        request = InstalledToolShedRepositoryIndexRequest(
            name=name,
            owner=owner,
            changeset=changeset,
            deleted=deleted,
            uninstalled=uninstalled,
        )
        return self.service.index(request)

    @router.get(
        "/api/tool_shed_repositories/check_for_updates",
        summary="Check for updates to the specified repository, or all installed repositories.",
        response_description="A description of the state and updates message.",
        require_admin=True,
    )
    def check_for_updates(self, id: Optional[DecodedDatabaseIdField] = None) -> CheckForUpdatesResponse:
        return self.service.check_for_updates(id and int(id))

    @router.get(
        "/api/tool_shed_repositories/{id}",
        summary="Show installed tool shed repository.",
    )
    def show(
        self,
        id: DecodedDatabaseIdField = InstalledToolShedRepositoryIDPathParam,
    ) -> InstalledToolShedRepository:
        return self.service.show(id)
