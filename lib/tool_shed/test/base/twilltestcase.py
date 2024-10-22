import abc
import contextlib
import logging
import os
import shutil
import string
import tarfile
import tempfile
import time
from json import loads
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)
from urllib.parse import (
    quote_plus,
    urlencode,
    urlparse,
)

import pytest
import requests
from mercurial import (
    commands,
    hg,
    ui,
)
from playwright.sync_api import Page
from sqlalchemy import (
    false,
    select,
)

import galaxy.model.tool_shed_install as galaxy_model
from galaxy.schema.schema import CheckForUpdatesResponse
from galaxy.security import idencoding
from galaxy.tool_shed.galaxy_install.install_manager import InstallRepositoryManager
from galaxy.tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from galaxy.tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import (
    InstalledRepositoryMetadataManager,
)
from galaxy.tool_shed.unittest_utils import (
    StandaloneInstallationTarget,
    ToolShedTarget,
)
from galaxy.tool_shed.util.dependency_display import build_manage_repository_dict
from galaxy.tool_shed.util.repository_util import check_for_updates
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    smart_str,
)
from galaxy_test.base.api_asserts import assert_status_code_is_ok
from galaxy_test.base.api_util import get_admin_api_key
from galaxy_test.base.populators import wait_on_assertion
from tool_shed.test.base.populators import TEST_DATA_REPO_FILES
from tool_shed.util import (
    hg_util,
    hgweb_config,
    xml_util,
)
from tool_shed.util.repository_content_util import tar_open
from tool_shed.webapp.model import Repository as DbRepository
from tool_shed_client.schema import (
    Category,
    Repository,
    RepositoryMetadata,
)
from . import (
    common,
    test_db_util,
)
from .api import ShedApiTestCase
from .browser import ShedBrowser
from .playwrightbrowser import PlaywrightShedBrowser
from .twillbrowser import (
    page_content,
    visit_url,
)

# Set a 10 minute timeout for repository installation.
repository_installation_timeout = 600

log = logging.getLogger(__name__)


class ToolShedInstallationClient(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def check_galaxy_repository_tool_panel_section(
        self, repository: galaxy_model.ToolShedRepository, expected_tool_panel_section: str
    ) -> None:
        """ """

    @abc.abstractmethod
    def setup(self) -> None:
        """Setup client interaction."""

    @abc.abstractmethod
    def deactivate_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        """Deactivate the supplied repository."""

    @abc.abstractmethod
    def display_installed_jobs_list_page(
        self, installed_repository: galaxy_model.ToolShedRepository, data_manager_names=None, strings_displayed=None
    ) -> None:
        """If available, check data manager jobs for supplied strings."""

    @abc.abstractmethod
    def installed_repository_extended_info(
        self, installed_repository: galaxy_model.ToolShedRepository
    ) -> Dict[str, Any]:
        """"""

    @abc.abstractmethod
    def install_repository(
        self,
        name: str,
        owner: str,
        changeset_revision: str,
        install_tool_dependencies: bool,
        install_repository_dependencies: bool,
        new_tool_panel_section_label: Optional[str],
    ) -> None:
        """"""

    @abc.abstractmethod
    def reactivate_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        """"""

    @abc.abstractmethod
    def reset_metadata_on_installed_repositories(self, repositories: List[galaxy_model.ToolShedRepository]) -> None:
        """"""

    @abc.abstractmethod
    def reset_installed_repository_metadata(self, repository: galaxy_model.ToolShedRepository) -> None:
        """"""

    @abc.abstractmethod
    def uninstall_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        """"""

    @abc.abstractmethod
    def update_installed_repository(
        self, installed_repository: galaxy_model.ToolShedRepository, verify_no_updates: bool = False
    ) -> Dict[str, Any]:
        """"""

    @property
    @abc.abstractmethod
    def tool_data_path(self) -> str:
        """"""

    @property
    @abc.abstractmethod
    def shed_tool_data_table_conf(self) -> str:
        """"""

    @abc.abstractmethod
    def get_tool_names(self) -> List[str]:
        """"""

    @abc.abstractmethod
    def get_installed_repository_by_name_owner(
        self, repository_name: str, repository_owner: str
    ) -> galaxy_model.ToolShedRepository:
        """"""

    @abc.abstractmethod
    def get_installed_repositories_by_name_owner(
        self, repository_name: str, repository_owner: str
    ) -> List[galaxy_model.ToolShedRepository]:
        """"""

    @abc.abstractmethod
    def get_installed_repository_for(
        self, owner: Optional[str] = None, name: Optional[str] = None, changeset: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """"""

    @abc.abstractmethod
    def get_all_installed_repositories(self) -> List[galaxy_model.ToolShedRepository]:
        """"""

    @abc.abstractmethod
    def refresh_tool_shed_repository(self, repo: galaxy_model.ToolShedRepository) -> None:
        """"""


class GalaxyInteractorToolShedInstallationClient(ToolShedInstallationClient):
    """A Galaxy API + Database as a installation target for the tool shed."""

    def __init__(self, testcase):
        self.testcase = testcase

    def setup(self):
        self._galaxy_login()

    def check_galaxy_repository_tool_panel_section(
        self, repository: galaxy_model.ToolShedRepository, expected_tool_panel_section: str
    ) -> None:
        metadata = repository.metadata_
        assert "tools" in metadata, f"Tools not found in repository metadata: {metadata}"
        # If integrated_tool_panel.xml is to be tested, this test method will need to be enhanced to handle tools
        # from the same repository in different tool panel sections. Getting the first tool guid is ok, because
        # currently all tools contained in a single repository will be loaded into the same tool panel section.
        if repository.status in [
            galaxy_model.ToolShedRepository.installation_status.UNINSTALLED,
            galaxy_model.ToolShedRepository.installation_status.DEACTIVATED,
        ]:
            tool_panel_section = _get_tool_panel_section_from_repository_metadata(metadata)
        else:
            tool_panel_section = self._get_tool_panel_section_from_api(metadata)
        assert (
            tool_panel_section == expected_tool_panel_section
        ), f"Expected to find tool panel section *{expected_tool_panel_section}*, but instead found *{tool_panel_section}*\nMetadata: {metadata}\n"

    def deactivate_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        encoded_id = self.testcase.security.encode_id(installed_repository.id)
        api_key = get_admin_api_key()
        response = requests.delete(
            f"{self.testcase.galaxy_url}/api/tool_shed_repositories/{encoded_id}",
            data={"remove_from_disk": False, "key": api_key},
            timeout=DEFAULT_SOCKET_TIMEOUT,
        )
        assert response.status_code != 403, response.content

    def display_installed_jobs_list_page(
        self, installed_repository: galaxy_model.ToolShedRepository, data_manager_names=None, strings_displayed=None
    ) -> None:
        data_managers = installed_repository.metadata_.get("data_manager", {}).get("data_managers", {})
        if data_manager_names:
            if not isinstance(data_manager_names, list):
                data_manager_names = [data_manager_names]
            for data_manager_name in data_manager_names:
                assert (
                    data_manager_name in data_managers
                ), f"The requested Data Manager '{data_manager_name}' was not found in repository metadata."
        else:
            data_manager_name = list(data_managers.keys())
        for data_manager_name in data_manager_names:
            params = {"id": data_managers[data_manager_name]["guid"]}
            self._visit_galaxy_url("/data_manager/jobs_list", params=params)
            content = page_content()
            for expected in strings_displayed:
                if content.find(expected) == -1:
                    raise AssertionError(f"Failed to find pattern {expected} in {content}")

    def installed_repository_extended_info(
        self, installed_repository: galaxy_model.ToolShedRepository
    ) -> Dict[str, Any]:
        params = {"id": self.testcase.security.encode_id(installed_repository.id)}
        self._visit_galaxy_url("/admin_toolshed/manage_repository_json", params=params)
        json = page_content()
        return loads(json)

    def install_repository(
        self,
        name: str,
        owner: str,
        changeset_revision: str,
        install_tool_dependencies: bool,
        install_repository_dependencies: bool,
        new_tool_panel_section_label: Optional[str],
    ):
        payload = {
            "tool_shed_url": self.testcase.url,
            "name": name,
            "owner": owner,
            "changeset_revision": changeset_revision,
            "install_tool_dependencies": install_tool_dependencies,
            "install_repository_dependencies": install_repository_dependencies,
            "install_resolver_dependencies": False,
        }
        if new_tool_panel_section_label:
            payload["new_tool_panel_section_label"] = new_tool_panel_section_label
        create_response = self.testcase.galaxy_interactor._post(
            "tool_shed_repositories/new/install_repository_revision", data=payload, admin=True
        )
        assert_status_code_is_ok(create_response)
        create_response_object = create_response.json()
        if isinstance(create_response_object, dict):
            assert "status" in create_response_object
            assert "ok" == create_response_object["status"]  # repo already installed...
            return
        assert isinstance(create_response_object, list)
        repository_ids = [repo["id"] for repo in create_response.json()]
        log.debug(f"Waiting for the installation of repository IDs: {repository_ids}")
        self._wait_for_repository_installation(repository_ids)

    def reactivate_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        params = dict(id=self.testcase.security.encode_id(installed_repository.id))
        url = "/admin_toolshed/restore_repository"
        self._visit_galaxy_url(url, params=params)

    def reset_metadata_on_installed_repositories(self, repositories: List[galaxy_model.ToolShedRepository]) -> None:
        repository_ids = []
        for repository in repositories:
            repository_ids.append(self.testcase.security.encode_id(repository.id))
        api_key = get_admin_api_key()
        response = requests.post(
            f"{self.testcase.galaxy_url}/api/tool_shed_repositories/reset_metadata_on_selected_installed_repositories",
            data={"repository_ids": repository_ids, "key": api_key},
            timeout=DEFAULT_SOCKET_TIMEOUT,
        )
        assert response.status_code != 403, response.content

    def uninstall_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        encoded_id = self.testcase.security.encode_id(installed_repository.id)
        api_key = get_admin_api_key()
        response = requests.delete(
            f"{self.testcase.galaxy_url}/api/tool_shed_repositories/{encoded_id}",
            data={"remove_from_disk": True, "key": api_key},
            timeout=DEFAULT_SOCKET_TIMEOUT,
        )
        assert response.status_code != 403, response.content

    def update_installed_repository(
        self, installed_repository: galaxy_model.ToolShedRepository, verify_no_updates: bool = False
    ) -> Dict[str, Any]:
        repository_id = self.testcase.security.encode_id(installed_repository.id)
        params = {
            "id": repository_id,
        }
        api_key = get_admin_api_key()
        response = requests.get(
            f"{self.testcase.galaxy_url}/api/tool_shed_repositories/check_for_updates?key={api_key}",
            params=params,
            timeout=DEFAULT_SOCKET_TIMEOUT,
        )
        response.raise_for_status()
        response_dict = response.json()
        if verify_no_updates:
            assert "message" in response_dict
            message = response_dict["message"]
            assert "The status has not changed in the tool shed for repository" in message, str(response_dict)
        return response_dict

    def reset_installed_repository_metadata(self, repository: galaxy_model.ToolShedRepository) -> None:
        encoded_id = self.testcase.security.encode_id(repository.id)
        api_key = get_admin_api_key()
        response = requests.post(
            f"{self.testcase.galaxy_url}/api/tool_shed_repositories/reset_metadata_on_selected_installed_repositories",
            data={"repository_ids": [encoded_id], "key": api_key},
            timeout=DEFAULT_SOCKET_TIMEOUT,
        )
        assert response.status_code != 403, response.content

    @property
    def tool_data_path(self):
        return os.environ.get("GALAXY_TEST_TOOL_DATA_PATH")

    @property
    def shed_tool_data_table_conf(self):
        return os.environ.get("TOOL_SHED_TEST_TOOL_DATA_TABLE_CONF")

    def get_tool_names(self) -> List[str]:
        response = self.testcase.galaxy_interactor._get("tools?in_panel=false")
        response.raise_for_status()
        tool_list = response.json()
        return [t["name"] for t in tool_list]

    def get_installed_repository_by_name_owner(
        self, repository_name: str, repository_owner: str
    ) -> galaxy_model.ToolShedRepository:
        return test_db_util.get_installed_repository_by_name_owner(repository_name, repository_owner)

    def get_installed_repositories_by_name_owner(
        self, repository_name: str, repository_owner: str
    ) -> List[galaxy_model.ToolShedRepository]:
        return test_db_util.get_installed_repository_by_name_owner(
            repository_name, repository_owner, return_multiple=True
        )

    def get_installed_repository_for(
        self, owner: Optional[str] = None, name: Optional[str] = None, changeset: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        return self.testcase.get_installed_repository_for(owner=owner, name=name, changeset=changeset)

    def get_all_installed_repositories(self) -> List[galaxy_model.ToolShedRepository]:
        repositories = test_db_util.get_all_installed_repositories()
        for repository in repositories:
            test_db_util.ga_refresh(repository)
        return repositories

    def refresh_tool_shed_repository(self, repo: galaxy_model.ToolShedRepository) -> None:
        test_db_util.ga_refresh(repo)

    def _galaxy_login(self, email="test@bx.psu.edu", password="testuser", username="admin-user"):
        self._galaxy_logout()
        self._create_user_in_galaxy(email=email, password=password, username=username)
        params = {"login": email, "password": password, "session_csrf_token": self._galaxy_token()}
        self._visit_galaxy_url("/user/login", params=params)

    def _galaxy_logout(self):
        self._visit_galaxy_url("/user/logout", params=dict(session_csrf_token=self._galaxy_token()))

    def _create_user_in_galaxy(self, email="test@bx.psu.edu", password="testuser", username="admin-user"):
        params = {
            "username": username,
            "email": email,
            "password": password,
            "confirm": password,
            "session_csrf_token": self._galaxy_token(),
        }
        self._visit_galaxy_url("/user/create", params=params, allowed_codes=[200, 400])

    def _galaxy_token(self):
        self._visit_galaxy_url("/")
        html = page_content()
        token_def_index = html.find("session_csrf_token")
        token_sep_index = html.find(":", token_def_index)
        token_quote_start_index = html.find('"', token_sep_index)
        token_quote_end_index = html.find('"', token_quote_start_index + 1)
        token = html[(token_quote_start_index + 1) : token_quote_end_index]
        return token

    def _get_tool_panel_section_from_api(self, metadata):
        tool_metadata = metadata["tools"]
        tool_guid = quote_plus(tool_metadata[0]["guid"], safe="")
        api_url = f"/api/tools/{tool_guid}"
        self._visit_galaxy_url(api_url)
        tool_dict = loads(page_content())
        tool_panel_section = tool_dict["panel_section_name"]
        return tool_panel_section

    def _wait_for_repository_installation(self, repository_ids):
        # Wait until all repositories are in a final state before returning. This ensures that subsequent tests
        # are running against an installed repository, and not one that is still in the process of installing.
        if repository_ids:
            for repository_id in repository_ids:
                galaxy_repository = test_db_util.get_installed_repository_by_id(
                    self.testcase.security.decode_id(repository_id)
                )
                _wait_for_installation(galaxy_repository, test_db_util.ga_refresh)

    def _visit_galaxy_url(self, url, params=None, allowed_codes=None):
        if allowed_codes is None:
            allowed_codes = [200]
        url = f"{self.testcase.galaxy_url}{url}"
        url = self.testcase.join_url_and_params(url, params)
        return visit_url(url, allowed_codes)


class StandaloneToolShedInstallationClient(ToolShedInstallationClient):
    def __init__(self, testcase):
        self.testcase = testcase
        self.temp_directory = Path(tempfile.mkdtemp(prefix="toolshedtestinstalltarget"))
        tool_shed_target = ToolShedTarget(
            self.testcase.url,
            "Tool Shed for Testing",
        )
        self._installation_target = StandaloneInstallationTarget(self.temp_directory, tool_shed_target=tool_shed_target)

    def setup(self) -> None:
        pass

    def check_galaxy_repository_tool_panel_section(
        self, repository: galaxy_model.ToolShedRepository, expected_tool_panel_section: str
    ) -> None:
        metadata = repository.metadata_
        assert "tools" in metadata, f"Tools not found in repository metadata: {metadata}"
        # TODO: check actual toolbox if tool is already installed...
        tool_panel_section = _get_tool_panel_section_from_repository_metadata(metadata)
        assert (
            tool_panel_section == expected_tool_panel_section
        ), f"Expected to find tool panel section *{expected_tool_panel_section}*, but instead found *{tool_panel_section}*\nMetadata: {metadata}\n"

    def deactivate_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        irm = InstalledRepositoryManager(app=self._installation_target)
        errors = irm.uninstall_repository(repository=installed_repository, remove_from_disk=False)
        if errors:
            raise Exception(
                f"Attempting to uninstall tool dependencies for repository named {installed_repository.name} resulted in errors: {errors}"
            )

    def display_installed_jobs_list_page(
        self, installed_repository: galaxy_model.ToolShedRepository, data_manager_names=None, strings_displayed=None
    ) -> None:
        raise NotImplementedError()

    def installed_repository_extended_info(
        self, installed_repository: galaxy_model.ToolShedRepository
    ) -> Dict[str, Any]:
        self._installation_target.install_model.context.refresh(installed_repository)
        return build_manage_repository_dict(self._installation_target, "ok", installed_repository)

    def install_repository(
        self,
        name: str,
        owner: str,
        changeset_revision: str,
        install_tool_dependencies: bool,
        install_repository_dependencies: bool,
        new_tool_panel_section_label: Optional[str],
    ):
        tool_shed_url = self.testcase.url
        payload = {
            "tool_shed_url": tool_shed_url,
            "name": name,
            "owner": owner,
            "changeset_revision": changeset_revision,
            "install_tool_dependencies": install_tool_dependencies,
            "install_repository_dependencies": install_repository_dependencies,
            "install_resolver_dependencies": False,
        }
        if new_tool_panel_section_label:
            payload["new_tool_panel_section_label"] = new_tool_panel_section_label
        irm = InstallRepositoryManager(app=self._installation_target)
        installed_tool_shed_repositories = irm.install(str(tool_shed_url), name, owner, changeset_revision, payload)
        for installed_tool_shed_repository in installed_tool_shed_repositories or []:
            _wait_for_installation(
                installed_tool_shed_repository, self._installation_target.install_model.context.refresh
            )

    def reactivate_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        irm = InstalledRepositoryManager(app=self._installation_target)
        irm.activate_repository(installed_repository)

    def reset_metadata_on_installed_repositories(self, repositories: List[galaxy_model.ToolShedRepository]) -> None:
        for repository in repositories:
            irmm = InstalledRepositoryMetadataManager(self._installation_target)
            irmm.set_repository(repository)
            irmm.reset_all_metadata_on_installed_repository()

    def reset_installed_repository_metadata(self, repository: galaxy_model.ToolShedRepository) -> None:
        irmm = InstalledRepositoryMetadataManager(self._installation_target)
        irmm.set_repository(repository)
        irmm.reset_all_metadata_on_installed_repository()

    def uninstall_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        irm = InstalledRepositoryManager(app=self._installation_target)
        errors = irm.uninstall_repository(repository=installed_repository, remove_from_disk=True)
        if errors:
            raise Exception(
                f"Attempting to uninstall tool dependencies for repository named {installed_repository.name} resulted in errors: {errors}"
            )

    def update_installed_repository(
        self, installed_repository: galaxy_model.ToolShedRepository, verify_no_updates: bool = False
    ) -> Dict[str, Any]:
        message, status = check_for_updates(
            self._installation_target.tool_shed_registry,
            self._installation_target.install_model.context,
            installed_repository.id,
        )
        response = CheckForUpdatesResponse(message=message, status=status)
        response_dict = response.dict()
        if verify_no_updates:
            assert "message" in response_dict
            message = response_dict["message"]
            assert "The status has not changed in the tool shed for repository" in message, str(response_dict)
        return response_dict

    def get_installed_repository_by_name_owner(
        self, repository_name: str, repository_owner: str
    ) -> galaxy_model.ToolShedRepository:
        return test_db_util.get_installed_repository_by_name_owner(
            repository_name, repository_owner, session=self._installation_target.install_model.context
        )

    def get_installed_repositories_by_name_owner(
        self, repository_name: str, repository_owner: str
    ) -> List[galaxy_model.ToolShedRepository]:
        return test_db_util.get_installed_repository_by_name_owner(
            repository_name,
            repository_owner,
            return_multiple=True,
            session=self._installation_target.install_model.context,
        )

    def get_installed_repository_for(
        self, owner: Optional[str] = None, name: Optional[str] = None, changeset: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        repository = get_installed_repository(self._installation_target.install_model.context, name, owner, changeset)
        if repository:
            return repository.to_dict()
        else:
            return None

    def get_all_installed_repositories(self) -> List[galaxy_model.ToolShedRepository]:
        repositories = test_db_util.get_all_installed_repositories(
            session=self._installation_target.install_model.context
        )
        for repository in repositories:
            self._installation_target.install_model.context.refresh(repository)
        return repositories

    def refresh_tool_shed_repository(self, repo: galaxy_model.ToolShedRepository) -> None:
        self._installation_target.install_model.context.refresh(repo)

    @property
    def shed_tool_data_table_conf(self):
        return self._installation_target.config.shed_tool_data_table_config

    @property
    def tool_data_path(self):
        return self._installation_target.config.tool_data_path

    def get_tool_names(self) -> List[str]:
        tool_names = []
        for _, tool in self._installation_target.toolbox.tools():
            tool_names.append(tool.name)
        return tool_names


@pytest.mark.usefixtures("shed_browser")
class ShedTwillTestCase(ShedApiTestCase):
    """Class of FunctionalTestCase geared toward HTML interactions using the Twill library."""

    requires_galaxy: bool = False
    _installation_client: Optional[
        Union[StandaloneToolShedInstallationClient, GalaxyInteractorToolShedInstallationClient]
    ] = None
    __browser: Optional[ShedBrowser] = None

    def setUp(self):
        super().setUp()
        # Security helper
        self.security = idencoding.IdEncodingHelper(id_secret="changethisinproductiontoo")
        self.history_id = None
        self.hgweb_config_dir = os.environ.get("TEST_HG_WEB_CONFIG_DIR")
        self.hgweb_config_manager = hgweb_config.hgweb_config_manager
        self.hgweb_config_manager.hgweb_config_dir = self.hgweb_config_dir
        self.tool_shed_test_tmp_dir = os.environ.get("TOOL_SHED_TEST_TMP_DIR", None)
        self.file_dir = os.environ.get("TOOL_SHED_TEST_FILE_DIR", None)
        self.shed_tool_conf = os.environ.get("GALAXY_TEST_SHED_TOOL_CONF")
        self.test_db_util = test_db_util
        if os.environ.get("TOOL_SHED_TEST_INSTALL_CLIENT") == "standalone":
            # TODO: once nose is out of the way - try to get away without
            # instantiating the unused Galaxy server here.
            installation_client_class = StandaloneToolShedInstallationClient
            full_stack_galaxy = False
        else:
            installation_client_class = GalaxyInteractorToolShedInstallationClient
            full_stack_galaxy = True
        self.full_stack_galaxy = full_stack_galaxy
        if self.requires_galaxy and (self.__class__._installation_client is None):
            self.__class__._installation_client = installation_client_class(self)
            self.__class__._installation_client.setup()
        self._installation_client = self.__class__._installation_client

    @pytest.fixture(autouse=True)
    def inject_shed_browser(self, shed_browser: ShedBrowser):
        self.__browser = shed_browser

    @property
    def _browser(self) -> ShedBrowser:
        assert self.__browser
        return self.__browser

    def _escape_page_content_if_needed(self, content: str) -> str:
        # if twill browser is being used - replace spaces with "&nbsp;"
        if self._browser.is_twill:
            content = content.replace(" ", "&nbsp;")
        return content

    def check_for_strings(self, strings_displayed=None, strings_not_displayed=None):
        strings_displayed = strings_displayed or []
        strings_not_displayed = strings_not_displayed or []
        if strings_displayed:
            for check_str in strings_displayed:
                self.check_page_for_string(check_str)
        if strings_not_displayed:
            for check_str in strings_not_displayed:
                self.check_string_not_in_page(check_str)

    def check_page(self, strings_displayed, strings_displayed_count, strings_not_displayed):
        """Checks a page for strings displayed, not displayed and number of occurrences of a string"""
        for check_str in strings_displayed:
            self.check_page_for_string(check_str)
        for check_str, count in strings_displayed_count:
            self.check_string_count_in_page(check_str, count)
        for check_str in strings_not_displayed:
            self.check_string_not_in_page(check_str)

    def check_page_for_string(self, patt):
        """Looks for 'patt' in the current browser page"""
        self._browser.check_page_for_string(patt)

    def check_string_not_in_page(self, patt):
        """Checks to make sure 'patt' is NOT in the page."""
        self._browser.check_string_not_in_page(patt)

    # Functions associated with user accounts
    def _submit_register_form(self, email: str, password: str, username: str, redirect: Optional[str] = None):
        self._browser.fill_form_value("registration", "email", email)
        if redirect is not None:
            self._browser.fill_form_value("registration", "redirect", redirect)
        self._browser.fill_form_value("registration", "password", password)
        self._browser.fill_form_value("registration", "confirm", password)
        self._browser.fill_form_value("registration", "username", username)
        self._browser.submit_form_with_name("registration", "create_user_button")

    @property
    def invalid_tools_labels(self) -> str:
        return "Invalid Tools" if self.is_v2 else "Invalid tools"

    def create(
        self,
        cntrller: str = "user",
        email: str = "test@bx.psu.edu",
        password: str = "testuser",
        username: str = "admin-user",
        redirect: Optional[str] = None,
    ) -> Tuple[bool, bool, bool]:
        # HACK: don't use panels because late_javascripts() messes up the twill browser and it
        # can't find form fields (and hence user can't be logged in).
        params = dict(cntrller=cntrller, use_panels=False)
        self.visit_url("/user/create", params)
        self._submit_register_form(
            email,
            password,
            username,
            redirect,
        )
        previously_created = False
        username_taken = False
        invalid_username = False
        if not self.is_v2:
            try:
                self.check_page_for_string("Created new user account")
            except AssertionError:
                try:
                    # May have created the account in a previous test run...
                    self.check_page_for_string(f"User with email '{email}' already exists.")
                    previously_created = True
                except AssertionError:
                    try:
                        self.check_page_for_string("Public name is taken; please choose another")
                        username_taken = True
                    except AssertionError:
                        # Note that we're only checking if the usr name is >< 4 chars here...
                        try:
                            self.check_page_for_string("Public name must be at least 4 characters in length")
                            invalid_username = True
                        except AssertionError:
                            pass
        return previously_created, username_taken, invalid_username

    def last_page(self):
        """
        Return the last visited page (usually HTML, but can binary data as
        well).
        """
        return self._browser.page_content()

    def user_api_interactor(self, email="test@bx.psu.edu", password="testuser"):
        return self._api_interactor_by_credentials(email, password)

    def user_populator(self, email="test@bx.psu.edu", password="testuser"):
        return self._get_populator(self.user_api_interactor(email=email, password=password))

    def login(
        self,
        email: str = "test@bx.psu.edu",
        password: str = "testuser",
        username: str = "admin-user",
        redirect: Optional[str] = None,
        logout_first: bool = True,
        explicit_logout: bool = False,
    ):
        if self.is_v2:
            # old version had a logout URL, this one needs to check
            # page if logged in
            self.visit_url("/")

        # Clear cookies.
        if logout_first:
            self.logout(explicit=explicit_logout)
        # test@bx.psu.edu is configured as an admin user
        previously_created, username_taken, invalid_username = self.create(
            email=email, password=password, username=username, redirect=redirect
        )
        # v2 doesn't log you in on account creation... so force a login here
        if previously_created or self.is_v2:
            # The account has previously been created, so just login.
            # HACK: don't use panels because late_javascripts() messes up the twill browser and it
            # can't find form fields (and hence user can't be logged in).
            params = {"use_panels": False}
            self.visit_url("/user/login", params=params)
            self.submit_form(button="login_button", login=email, redirect=redirect, password=password)

    @property
    def is_v2(self) -> bool:
        return self.api_interactor.api_version == "v2"

    @property
    def _playwright_browser(self) -> PlaywrightShedBrowser:
        # make sure self.is_v2
        browser = self._browser
        assert isinstance(browser, PlaywrightShedBrowser)
        return browser

    @property
    def _page(self) -> Page:
        return self._playwright_browser._page

    def logout(self, explicit: bool = False):
        """logout of the current tool shed session.

        By default this is a logout if logged in action,
        however if explicit is True - ensure there is a session
        and be explicit in logging out to provide extract test
        structure.
        """
        if self.is_v2:
            if explicit:
                self._playwright_browser.explicit_logout()
            else:
                self._playwright_browser.logout_if_logged_in()
        else:
            self.visit_url("/user/logout")
            self.check_page_for_string("You have been logged out")

    def submit_form(self, form_no=-1, button="runtool_btn", form=None, **kwd):
        """Populates and submits a form from the keyword arguments."""
        # An HTMLForm contains a sequence of Controls.  Supported control classes are:
        # TextControl, FileControl, ListControl, RadioControl, CheckboxControl, SelectControl,
        # SubmitControl, ImageControl
        self._browser.submit_form(form_no, button, form, **kwd)

    def join_url_and_params(self, url: str, params, query=None) -> str:
        if params is None:
            params = {}
        if query is None:
            query = urlparse(url).query
        if query:
            for query_parameter in query.split("&"):
                key, value = query_parameter.split("=")
                params[key] = value
        if params:
            url += f"?{urlencode(params)}"
        return url

    def visit_url(self, url: str, params=None, allowed_codes: Optional[List[int]] = None) -> str:
        parsed_url = urlparse(url)
        if len(parsed_url.netloc) == 0:
            url = f"http://{self.host}:{self.port}{parsed_url.path}"
        else:
            url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        url = self.join_url_and_params(url, params, query=parsed_url.query)
        if allowed_codes is None:
            allowed_codes = [200]

        return self._browser.visit_url(url, allowed_codes=allowed_codes)

    def write_temp_file(self, content, suffix=".html"):
        with tempfile.NamedTemporaryFile(suffix=suffix, prefix="twilltestcase-", delete=False) as fh:
            fh.write(smart_str(content))
        return fh.name

    def assign_admin_role(self, repository: Repository, user):
        # As elsewhere, twill limits the possibility of submitting the form, this time due to not executing the javascript
        # attached to the role selection form. Visit the action url directly with the necessary parameters.
        params = {
            "id": repository.id,
            "in_users": user.id,
            "manage_role_associations_button": "Save",
        }
        self.visit_url("/repository/manage_repository_admins", params=params)
        self.check_for_strings(strings_displayed=["Role", "has been associated"])

    def browse_category(self, category: Category, strings_displayed=None, strings_not_displayed=None):
        if self.is_v2:
            self.visit_url(f"/repositories_by_category/{category.id}")
        else:
            params = {
                "sort": "name",
                "operation": "valid_repositories_by_category",
                "id": category.id,
            }
            self.visit_url("/repository/browse_valid_categories", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def browse_repository(self, repository: Repository, strings_displayed=None, strings_not_displayed=None):
        params = {"id": repository.id}
        self.visit_url("/repository/browse_repository", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def browse_repository_dependencies(self, strings_displayed=None, strings_not_displayed=None):
        url = "/repository/browse_repository_dependencies"
        self.visit_url(url)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def browse_tool_shed(self, url, strings_displayed=None, strings_not_displayed=None):
        if self.is_v2:
            url = "/repositories_by_category"
        else:
            url = "/repository/browse_valid_categories"
        self.visit_url(url)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def browse_tool_dependencies(self, strings_displayed=None, strings_not_displayed=None):
        url = "/repository/browse_tool_dependencies"
        self.visit_url(url)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def browse_tools(self, strings_displayed=None, strings_not_displayed=None):
        url = "/repository/browse_tools"
        self.visit_url(url)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def check_count_of_metadata_revisions_associated_with_repository(self, repository: Repository, metadata_count):
        self.check_repository_changelog(repository)
        self.check_string_count_in_page("Repository metadata is associated with this change set.", metadata_count)

    def check_for_valid_tools(self, repository, strings_displayed=None, strings_not_displayed=None):
        if strings_displayed is None:
            strings_displayed = ["Valid tools"]
        else:
            strings_displayed.append("Valid tools")
        self.display_manage_repository_page(repository, strings_displayed, strings_not_displayed)

    def check_galaxy_repository_db_status(self, repository_name, owner, expected_status):
        installed_repository = self._get_installed_repository_by_name_owner(repository_name, owner)
        self._refresh_tool_shed_repository(installed_repository)
        assert (
            installed_repository.status == expected_status
        ), f"Status in database is {installed_repository.status}, expected {expected_status}"

    def check_repository_changelog(self, repository: Repository, strings_displayed=None, strings_not_displayed=None):
        params = {"id": repository.id}
        self.visit_url("/repository/view_changelog", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def check_repository_dependency(
        self,
        repository: Repository,
        depends_on_repository: Repository,
        depends_on_changeset_revision=None,
        changeset_revision=None,
    ):
        if not self.is_v2:
            # v2 doesn't display repository repository dependencies, they are deprecated
            strings_displayed = [depends_on_repository.name, depends_on_repository.owner]
            if depends_on_changeset_revision:
                strings_displayed.append(depends_on_changeset_revision)
            self.display_manage_repository_page(
                repository, changeset_revision=changeset_revision, strings_displayed=strings_displayed
            )

    def check_repository_metadata(self, repository: Repository, tip_only=True):
        if tip_only:
            assert (
                self.tip_has_metadata(repository) and len(self.get_repository_metadata_revisions(repository)) == 1
            ), "Repository tip is not a metadata revision: Repository tip - %s, metadata revisions - %s."
        else:
            assert (
                len(self.get_repository_metadata_revisions(repository)) > 0
            ), "Repository tip is not a metadata revision: Repository tip - {}, metadata revisions - {}.".format(
                self.get_repository_tip(repository),
                ", ".join(self.get_repository_metadata_revisions(repository)),
            )

    def check_repository_tools_for_changeset_revision(
        self,
        repository: Repository,
        changeset_revision,
        tool_metadata_strings_displayed=None,
        tool_page_strings_displayed=None,
    ):
        """
        Loop through each tool dictionary in the repository metadata associated with the received changeset_revision.
        For each of these, check for a tools attribute, and load the tool metadata page if it exists, then display that tool's page.
        """
        db_repository = self._db_repository(repository)
        test_db_util.refresh(db_repository)
        repository_metadata = self.get_repository_metadata_by_changeset_revision(db_repository.id, changeset_revision)
        metadata = repository_metadata.metadata
        if "tools" not in metadata:
            raise AssertionError(f"No tools in {repository.name} revision {changeset_revision}.")
        for tool_dict in metadata["tools"]:
            tool_id = tool_dict["id"]
            tool_xml = tool_dict["tool_config"]
            params = {
                "repository_id": repository.id,
                "changeset_revision": changeset_revision,
                "tool_id": tool_id,
            }
            self.visit_url("/repository/view_tool_metadata", params=params)
            self.check_for_strings(tool_metadata_strings_displayed)
            self.load_display_tool_page(
                repository,
                tool_xml_path=tool_xml,
                changeset_revision=changeset_revision,
                strings_displayed=tool_page_strings_displayed,
                strings_not_displayed=None,
            )

    def check_repository_invalid_tools_for_changeset_revision(
        self, repository: Repository, changeset_revision, strings_displayed=None, strings_not_displayed=None
    ):
        """Load the invalid tool page for each invalid tool associated with this changeset revision and verify the received error messages."""
        db_repository = self._db_repository(repository)
        repository_metadata = self.get_repository_metadata_by_changeset_revision(db_repository.id, changeset_revision)
        metadata = repository_metadata.metadata
        assert (
            "invalid_tools" in metadata
        ), f"Metadata for changeset revision {changeset_revision} does not define invalid tools"
        for tool_xml in metadata["invalid_tools"]:
            self.load_invalid_tool_page(
                repository,
                tool_xml=tool_xml,
                changeset_revision=changeset_revision,
                strings_displayed=strings_displayed,
                strings_not_displayed=strings_not_displayed,
            )

    def check_string_count_in_page(self, pattern, min_count, max_count=None):
        """Checks the number of 'pattern' occurrences in the current browser page"""
        page = self.last_page()
        pattern_count = page.count(pattern)
        if max_count is None:
            max_count = min_count
        # The number of occurrences of pattern in the page should be between min_count
        # and max_count, so show error if pattern_count is less than min_count or greater
        # than max_count.
        if pattern_count < min_count or pattern_count > max_count:
            fname = self.write_temp_file(page)
            errmsg = "%i occurrences of '%s' found (min. %i, max. %i).\npage content written to '%s' " % (
                pattern_count,
                pattern,
                min_count,
                max_count,
                fname,
            )
            raise AssertionError(errmsg)

    def check_galaxy_repository_tool_panel_section(
        self, repository: galaxy_model.ToolShedRepository, expected_tool_panel_section: str
    ) -> None:
        assert self._installation_client
        self._installation_client.check_galaxy_repository_tool_panel_section(repository, expected_tool_panel_section)

    def clone_repository(self, repository: Repository, destination_path: str) -> None:
        url = f"{self.url}/repos/{repository.owner}/{repository.name}"
        success, message = hg_util.clone_repository(url, destination_path, self.get_repository_tip(repository))
        assert success is True, message

    def commit_and_push(self, repository, hgrepo, options, username, password):
        url = f"http://{username}:{password}@{self.host}:{self.port}/repos/{repository.user.username}/{repository.name}"
        commands.commit(ui.ui(), hgrepo, **options)
        #  Try pushing multiple times as it transiently fails on Jenkins.
        #  TODO: Figure out why that happens
        for _ in range(5):
            try:
                commands.push(ui.ui(), hgrepo, dest=url)
            except Exception as e:
                if str(e).find("Pushing to Tool Shed is disabled") != -1:
                    return False
            else:
                return True
        raise

    def create_category(self, **kwd) -> Category:
        category_name = kwd["name"]
        try:
            category = self.populator.get_category_with_name(category_name)
        except ValueError:
            # not recreating this functionality in the UI I don't think?
            category = self.populator.new_category(category_name)
            return category
        return category

    def create_repository_dependency(
        self,
        repository: Repository,
        repository_tuples=None,
        filepath=None,
        prior_installation_required=False,
        complex=False,
        package=None,
        version=None,
        strings_displayed=None,
        strings_not_displayed=None,
    ):
        repository_tuples = repository_tuples or []
        repository_names = []
        if complex:
            filename = "tool_dependencies.xml"
            target = self.generate_complex_dependency_xml(
                filename=filename,
                filepath=filepath,
                repository_tuples=repository_tuples,
                package=package,
                version=version,
            )
        else:
            for _, name, _, _ in repository_tuples:
                repository_names.append(name)
            dependency_description = f"{repository.name} depends on {', '.join(repository_names)}."
            filename = "repository_dependencies.xml"
            target = self.generate_simple_dependency_xml(
                repository_tuples=repository_tuples,
                filename=filename,
                filepath=filepath,
                dependency_description=dependency_description,
                prior_installation_required=prior_installation_required,
            )
        self.add_file_to_repository(repository, target, filename, strings_displayed=strings_displayed)

    def deactivate_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        assert self._installation_client
        self._installation_client.deactivate_repository(installed_repository)

    @contextlib.contextmanager
    def cloned_repo(self, repository: Repository) -> Iterator[str]:
        temp_directory = tempfile.mkdtemp(prefix="toolshedrepowithoutfiles")
        try:
            self.clone_repository(repository, temp_directory)
            shutil.rmtree(os.path.join(temp_directory, ".hg"))
            contents = os.listdir(temp_directory)
            if len(contents) == 1 and contents[0] == "repo":
                yield os.path.join(temp_directory, "repo")
            else:
                yield temp_directory
        finally:
            shutil.rmtree(temp_directory)

    def setup_freebayes_0010_repo(self, repository: Repository):
        strings_displayed = [
            "Metadata may have been defined",
            "This file requires an entry",
            "tool_data_table_conf",
        ]
        self.add_file_to_repository(repository, "freebayes/freebayes.xml", strings_displayed=strings_displayed)
        strings_displayed = ["Upload a file named <b>sam_fa_indices.loc.sample"]
        self.add_file_to_repository(
            repository, "freebayes/tool_data_table_conf.xml.sample", strings_displayed=strings_displayed
        )
        self.add_file_to_repository(repository, "freebayes/sam_fa_indices.loc.sample")
        target = os.path.join("freebayes", "malformed_tool_dependencies", "tool_dependencies.xml")
        self.add_file_to_repository(
            repository, target, strings_displayed=["Exception attempting to parse", "invalid element name"]
        )
        target = os.path.join("freebayes", "invalid_tool_dependencies", "tool_dependencies.xml")
        strings_displayed = [
            "The settings for <b>name</b>, <b>version</b> and <b>type</b> from a contained tool configuration"
        ]
        # , strings_displayed=strings_displayed
        self.add_file_to_repository(repository, target)
        target = os.path.join("freebayes", "tool_dependencies.xml")
        self.add_file_to_repository(repository, target)

    def add_file_to_repository(
        self,
        repository: Repository,
        source: str,
        target: Optional[str] = None,
        strings_displayed=None,
        commit_message: Optional[str] = None,
    ):
        with self.cloned_repo(repository) as temp_directory:
            if target is None:
                target = os.path.basename(source)
            full_target = os.path.join(temp_directory, target)
            full_source = TEST_DATA_REPO_FILES.joinpath(source)
            shutil.copyfile(str(full_source), full_target)
            commit_message = commit_message or "Uploaded revision with added file."
            self._upload_dir_to_repository(
                repository, temp_directory, commit_message=commit_message, strings_displayed=strings_displayed
            )

    def add_tar_to_repository(self, repository: Repository, source: str, strings_displayed=None):
        with self.cloned_repo(repository) as temp_directory:
            full_source = TEST_DATA_REPO_FILES.joinpath(source)
            tar = tar_open(full_source)
            tar.extractall(path=temp_directory)
            tar.close()
            commit_message = "Uploaded revision with added files from tar."
            self._upload_dir_to_repository(
                repository, temp_directory, commit_message=commit_message, strings_displayed=strings_displayed
            )

    def commit_tar_to_repository(
        self, repository: Repository, source: str, commit_message=None, strings_displayed=None
    ):
        full_source = TEST_DATA_REPO_FILES.joinpath(source)
        assert full_source.is_file(), f"Attempting to upload {full_source} as a tar which is not a file"
        populator = self.user_populator()
        if strings_displayed is None:
            # Just assume this is a valid upload...
            populator.upload_revision(repository, full_source, commit_message=commit_message)
        else:
            response = populator.upload_revision_raw(repository, full_source, commit_message=commit_message)
            try:
                text = response.json()["message"]
            except Exception:
                text = response.text
            for string_displayed in strings_displayed:
                if string_displayed not in text:
                    raise AssertionError(f"Failed to find {string_displayed} in JSON response {text}")

    def delete_files_from_repository(self, repository: Repository, filenames: List[str]):
        with self.cloned_repo(repository) as temp_directory:
            for filename in filenames:
                to_delete = os.path.join(temp_directory, filename)
                os.remove(to_delete)
            commit_message = "Uploaded revision with deleted files."
            self._upload_dir_to_repository(repository, temp_directory, commit_message=commit_message)

    def _upload_dir_to_repository(self, repository: Repository, target, commit_message, strings_displayed=None):
        tf = tempfile.NamedTemporaryFile()
        with tarfile.open(tf.name, "w:gz") as tar:
            tar.add(target, arcname=".")
        target = os.path.abspath(tf.name)
        self.commit_tar_to_repository(
            repository, target, commit_message=commit_message, strings_displayed=strings_displayed
        )

    def delete_repository(self, repository: Repository) -> None:
        repository_id = repository.id
        self.visit_url("/admin/browse_repositories")
        params = {"operation": "Delete", "id": repository_id}
        self.visit_url("/admin/browse_repositories", params=params)
        strings_displayed = ["Deleted 1 repository", repository.name]
        strings_not_displayed: List[str] = []
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def display_installed_jobs_list_page(self, installed_repository, data_manager_names=None, strings_displayed=None):
        assert self._installation_client
        self._installation_client.display_installed_jobs_list_page(
            installed_repository, data_manager_names, strings_displayed
        )

    def display_installed_repository_manage_json(self, installed_repository):
        assert self._installation_client
        return self._installation_client.installed_repository_extended_info(installed_repository)

    def display_manage_repository_page(
        self, repository: Repository, changeset_revision=None, strings_displayed=None, strings_not_displayed=None
    ):
        params = {"id": repository.id}
        if changeset_revision:
            params["changeset_revision"] = changeset_revision
        url = "/repository/manage_repository"
        if self.is_v2:
            url = f"/repositories/{repository.id}"
        self.visit_url(url, params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def display_repository_clone_page(
        self, owner_name, repository_name, strings_displayed=None, strings_not_displayed=None
    ):
        url = f"/repos/{owner_name}/{repository_name}"
        self.visit_url(url)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def display_repository_file_contents(
        self, repository: Repository, filename, filepath=None, strings_displayed=None, strings_not_displayed=None
    ):
        """Find a file in the repository and display the contents."""
        basepath = self.get_repo_path(repository)
        repository_file_list = []
        if filepath:
            relative_path = os.path.join(basepath, filepath)
        else:
            relative_path = basepath
        repository_file_list = self.get_repository_file_list(
            repository=repository, base_path=relative_path, current_path=None
        )
        assert filename in repository_file_list, f"File {filename} not found in the repository under {relative_path}."
        params = dict(file_path=os.path.join(relative_path, filename), repository_id=repository.id)
        url = "/repository/get_file_contents"
        self.visit_url(url, params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def edit_repository_categories(
        self,
        repository: Repository,
        categories_to_add: List[str],
        categories_to_remove: List[str],
        restore_original=True,
    ) -> None:
        params = {"id": repository.id}
        self.visit_url("/repository/manage_repository", params=params)
        self._browser.edit_repository_categories(categories_to_add, categories_to_remove)

    def edit_repository_information(self, repository: Repository, revert=True, **kwd):
        params = {"id": repository.id}
        self.visit_url("/repository/manage_repository", params=params)
        db_repository = self._db_repository(repository)
        original_information = dict(
            repo_name=db_repository.name,
            description=db_repository.description,
            long_description=db_repository.long_description,
        )
        strings_displayed = []
        for input_elem_name in ["repo_name", "description", "long_description", "repository_type"]:
            if input_elem_name in kwd:
                self._browser.fill_form_value("edit_repository", input_elem_name, kwd[input_elem_name])
                strings_displayed.append(self.escape_html(kwd[input_elem_name]))
        self._browser.submit_form_with_name("edit_repository", "edit_repository_button")
        # TODO: come back to this (and similar conditional below), the problem is check
        # for strings isn't working with with textboxes I think?
        if self._browser.is_twill:
            self.check_for_strings(strings_displayed)
        if revert:
            strings_displayed = []
            # assert original_information[input_elem_name]
            for input_elem_name in ["repo_name", "description", "long_description"]:
                self._browser.fill_form_value(
                    "edit_repository", input_elem_name, original_information[input_elem_name]  # type:ignore[arg-type]
                )
                strings_displayed.append(self.escape_html(original_information[input_elem_name]))
            self._browser.submit_form_with_name("edit_repository", "edit_repository_button")
            if self._browser.is_twill:
                self.check_for_strings(strings_displayed)

    def enable_email_alerts(self, repository: Repository, strings_displayed=None, strings_not_displayed=None) -> None:
        repository_id = repository.id
        params = dict(operation="Receive email alerts", id=repository_id)
        self.visit_url("/repository/browse_repositories", params)
        self.check_for_strings(strings_displayed)

    def escape_html(self, string, unescape=False):
        html_entities = [("&", "X"), ("'", "&#39;"), ('"', "&#34;")]
        for character, replacement in html_entities:
            if unescape:
                string = string.replace(replacement, character)
            else:
                string = string.replace(character, replacement)
        return string

    def expect_repo_created_strings(self, name):
        return [
            f"Repository <b>{name}</b>",
            f"Repository <b>{name}</b> has been created",
        ]

    def fetch_repository_metadata(self, repository: Repository, strings_displayed=None, strings_not_displayed=None):
        url = f"/api/repositories/{repository.id}/metadata"
        self.visit_url(url)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def generate_complex_dependency_xml(self, filename, filepath, repository_tuples, package, version):
        file_path = os.path.join(filepath, filename)
        dependency_entries = []
        template = string.Template(common.new_repository_dependencies_line)
        for toolshed_url, name, owner, changeset_revision in repository_tuples:
            dependency_entries.append(
                template.safe_substitute(
                    toolshed_url=toolshed_url,
                    owner=owner,
                    repository_name=name,
                    changeset_revision=changeset_revision,
                    prior_installation_required="",
                )
            )
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        dependency_template = string.Template(common.complex_repository_dependency_template)
        repository_dependency_xml = dependency_template.safe_substitute(
            package=package, version=version, dependency_lines="\n".join(dependency_entries)
        )
        # Save the generated xml to the specified location.
        open(file_path, "w").write(repository_dependency_xml)
        return file_path

    def generate_simple_dependency_xml(
        self,
        repository_tuples,
        filename,
        filepath,
        dependency_description="",
        complex=False,
        package=None,
        version=None,
        prior_installation_required=False,
    ):
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        dependency_entries = []
        if prior_installation_required:
            prior_installation_value = ' prior_installation_required="True"'
        else:
            prior_installation_value = ""
        for toolshed_url, name, owner, changeset_revision in repository_tuples:
            template = string.Template(common.new_repository_dependencies_line)
            dependency_entries.append(
                template.safe_substitute(
                    toolshed_url=toolshed_url,
                    owner=owner,
                    repository_name=name,
                    changeset_revision=changeset_revision,
                    prior_installation_required=prior_installation_value,
                )
            )
        if dependency_description:
            description = f' description="{dependency_description}"'
        else:
            description = dependency_description
        template_parser = string.Template(common.new_repository_dependencies_xml)
        repository_dependency_xml = template_parser.safe_substitute(
            description=description, dependency_lines="\n".join(dependency_entries)
        )
        # Save the generated xml to the specified location.
        full_path = os.path.join(filepath, filename)
        open(full_path, "w").write(repository_dependency_xml)
        return full_path

    def generate_temp_path(self, test_script_path, additional_paths=None):
        additional_paths = additional_paths or []
        temp_path = os.path.join(self.tool_shed_test_tmp_dir, test_script_path, os.sep.join(additional_paths))
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)
        return temp_path

    def get_all_installed_repositories(self) -> List[galaxy_model.ToolShedRepository]:
        assert self._installation_client
        return self._installation_client.get_all_installed_repositories()

    def get_filename(self, filename, filepath=None):
        if filepath is not None:
            return os.path.abspath(os.path.join(filepath, filename))
        else:
            return os.path.abspath(os.path.join(self.file_dir, filename))

    def get_hg_repo(self, path):
        return hg.repository(ui.ui(), path.encode("utf-8"))

    def get_repositories_category_api(
        self, categories: List[Category], strings_displayed=None, strings_not_displayed=None
    ):
        for category in categories:
            url = f"/api/categories/{category.id}/repositories"
            self.visit_url(url)
            self.check_for_strings(strings_displayed, strings_not_displayed)

    def get_or_create_repository(
        self, category: Category, owner: str, name: str, strings_displayed=None, strings_not_displayed=None, **kwd
    ) -> Repository:
        # If not checking for a specific string, it should be safe to assume that
        # we expect repository creation to be successful.
        if strings_displayed is None:
            strings_displayed = ["Repository", name, "has been created"]
        if strings_not_displayed is None:
            strings_not_displayed = []
        repository = self.populator.get_repository_for(owner, name)
        if repository is None:
            category_id = category.id
            assert category_id
            self.visit_url("/repository/create_repository")
            self.submit_form(button="create_repository_button", name=name, category_id=category_id, **kwd)
            self.check_for_strings(strings_displayed, strings_not_displayed)
            repository = self.populator.get_repository_for(owner, name)
        assert repository
        return repository

    def get_repo_path(self, repository: Repository) -> str:
        # An entry in the hgweb.config file looks something like: repos/test/mira_assembler = database/community_files/000/repo_123
        lhs = f"repos/{repository.owner}/{repository.name}"
        try:
            return self.hgweb_config_manager.get_entry(lhs)
        except Exception:
            raise Exception(
                f"Entry for repository {lhs} missing in hgweb config file {self.hgweb_config_manager.hgweb_config}."
            )

    def get_repository_changelog_tuples(self, repository):
        repo = self.get_hg_repo(self.get_repo_path(repository))
        changelog_tuples = []
        for changeset in repo.changelog:
            ctx = repo[changeset]
            changelog_tuples.append((ctx.rev(), ctx))
        return changelog_tuples

    def get_repository_file_list(self, repository: Repository, base_path: str, current_path=None) -> List[str]:
        """Recursively load repository folder contents and append them to a list. Similar to os.walk but via /repository/open_folder."""
        if current_path is None:
            request_param_path = base_path
        else:
            request_param_path = os.path.join(base_path, current_path)
        # Get the current folder's contents.
        params = dict(folder_path=request_param_path, repository_id=repository.id)
        url = "/repository/open_folder"
        self.visit_url(url, params=params)
        file_list = loads(self.last_page())
        returned_file_list = []
        if current_path is not None:
            returned_file_list.append(current_path)
        # Loop through the json dict returned by /repository/open_folder.
        for file_dict in file_list:
            if file_dict["isFolder"]:
                # This is a folder. Get the contents of the folder and append it to the list,
                # prefixed with the path relative to the repository root, if any.
                if current_path is None:
                    returned_file_list.extend(
                        self.get_repository_file_list(
                            repository=repository, base_path=base_path, current_path=file_dict["title"]
                        )
                    )
                else:
                    sub_path = os.path.join(current_path, file_dict["title"])
                    returned_file_list.extend(
                        self.get_repository_file_list(repository=repository, base_path=base_path, current_path=sub_path)
                    )
            else:
                # This is a regular file, prefix the filename with the current path and append it to the list.
                if current_path is not None:
                    returned_file_list.append(os.path.join(current_path, file_dict["title"]))
                else:
                    returned_file_list.append(file_dict["title"])
        return returned_file_list

    def _db_repository(self, repository: Repository) -> DbRepository:
        return self.test_db_util.get_repository_by_name_and_owner(repository.name, repository.owner)

    def get_repository_metadata(self, repository: Repository):
        return self.get_repository_metadata_for_db_object(self._db_repository(repository))

    def get_repository_metadata_for_db_object(self, repository: DbRepository):
        return list(repository.metadata_revisions)

    def get_repository_metadata_by_changeset_revision(self, repository_id: int, changeset_revision):
        return test_db_util.get_repository_metadata_by_repository_id_changeset_revision(
            repository_id, changeset_revision
        ) or test_db_util.get_repository_metadata_by_repository_id_changeset_revision(repository_id, None)

    def get_repository_metadata_revisions(self, repository: Repository) -> List[str]:
        return [
            str(repository_metadata.changeset_revision)
            for repository_metadata in self._db_repository(repository).metadata_revisions
        ]

    def _get_repository_by_name_and_owner(self, name: str, owner: str) -> Repository:
        repo = self.populator.get_repository_for(owner, name)
        if repo is None:
            repo = self.populator.get_repository_for(owner, name, deleted="true")
        assert repo
        return repo

    def get_repository_tip(self, repository: Repository) -> str:
        repo = self.get_hg_repo(self.get_repo_path(repository))
        return str(repo[repo.changelog.tip()])

    def get_repository_first_revision(self, repository: Repository) -> str:
        repo = self.get_hg_repo(self.get_repo_path(repository))
        return str(repo[0])

    def _get_metadata_revision_count(self, repository: Repository) -> int:
        repostiory_metadata: RepositoryMetadata = self.populator.get_metadata(repository, downloadable_only=False)
        return len(repostiory_metadata.root)

    def get_tools_from_repository_metadata(self, repository, include_invalid=False):
        """Get a list of valid and (optionally) invalid tool dicts from the repository metadata."""
        valid_tools = []
        invalid_tools = []
        for repository_metadata in repository.metadata_revisions:
            if "tools" in repository_metadata.metadata:
                valid_tools.append(
                    dict(
                        tools=repository_metadata.metadata["tools"],
                        changeset_revision=repository_metadata.changeset_revision,
                    )
                )
            if include_invalid and "invalid_tools" in repository_metadata.metadata:
                invalid_tools.append(
                    dict(
                        tools=repository_metadata.metadata["invalid_tools"],
                        changeset_revision=repository_metadata.changeset_revision,
                    )
                )
        return valid_tools, invalid_tools

    def grant_role_to_user(self, user, role):
        strings_displayed = [self.security.encode_id(role.id), role.name]
        strings_not_displayed = []
        self.visit_url("/admin/roles")
        self.check_for_strings(strings_displayed, strings_not_displayed)
        params = dict(operation="manage users and groups", id=self.security.encode_id(role.id))
        url = "/admin/roles"
        self.visit_url(url, params)
        strings_displayed = [common.test_user_1_email, common.test_user_2_email]
        self.check_for_strings(strings_displayed, strings_not_displayed)
        # As elsewhere, twill limits the possibility of submitting the form, this time due to not executing the javascript
        # attached to the role selection form. Visit the action url directly with the necessary parameters.
        params = dict(
            id=self.security.encode_id(role.id),
            in_users=user.id,
            operation="manage users and groups",
            role_members_edit_button="Save",
        )
        url = "/admin/manage_users_and_groups_for_role"
        self.visit_url(url, params)
        strings_displayed = [f"Role '{role.name}' has been updated"]
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def grant_write_access(
        self,
        repository: Repository,
        usernames=None,
        strings_displayed=None,
        strings_not_displayed=None,
        post_submit_strings_displayed=None,
        post_submit_strings_not_displayed=None,
    ):
        usernames = usernames or []
        self.display_manage_repository_page(repository)
        self.check_for_strings(strings_displayed, strings_not_displayed)
        self._browser.grant_users_access(usernames)
        self.check_for_strings(post_submit_strings_displayed, post_submit_strings_not_displayed)

    def _install_repository(
        self,
        name: str,
        owner: str,
        category_name: str,
        install_tool_dependencies: bool = False,
        install_repository_dependencies: bool = True,
        changeset_revision: Optional[str] = None,
        preview_strings_displayed: Optional[List[str]] = None,
        new_tool_panel_section_label: Optional[str] = None,
    ) -> None:
        self.browse_tool_shed(url=self.url)
        category = self.populator.get_category_with_name(category_name)
        self.browse_category(category)
        self.preview_repository_in_tool_shed(name, owner, strings_displayed=preview_strings_displayed)
        repository = self._get_repository_by_name_and_owner(name, owner)
        assert repository
        # repository_id = repository.id
        if changeset_revision is None:
            changeset_revision = self.get_repository_tip(repository)
        assert self._installation_client
        self._installation_client.install_repository(
            name,
            owner,
            changeset_revision,
            install_tool_dependencies,
            install_repository_dependencies,
            new_tool_panel_section_label,
        )

    def load_citable_url(
        self,
        username,
        repository_name,
        changeset_revision,
        encoded_user_id,
        encoded_repository_id,
        strings_displayed=None,
        strings_not_displayed=None,
        strings_displayed_in_iframe=None,
        strings_not_displayed_in_iframe=None,
    ):
        strings_displayed_in_iframe = strings_displayed_in_iframe or []
        strings_not_displayed_in_iframe = strings_not_displayed_in_iframe or []
        url = f"{self.url}/view/{username}"
        # If repository name is passed in, append that to the url.
        if repository_name:
            url += f"/{repository_name}"
        if changeset_revision:
            # Changeset revision should never be provided unless repository name also is.
            assert repository_name is not None, "Changeset revision is present, but repository name is not - aborting."
            url += f"/{changeset_revision}"
        self.visit_url(url)
        self.check_for_strings(strings_displayed, strings_not_displayed)
        if self.is_v2:
            self.check_for_strings(strings_displayed_in_iframe, strings_not_displayed_in_iframe)
        else:
            # Now load the page that should be displayed inside the iframe and check for strings.
            if encoded_repository_id:
                params = {"id": encoded_repository_id, "operation": "view_or_manage_repository"}
                if changeset_revision:
                    params["changeset_revision"] = changeset_revision
                self.visit_url("/repository/view_repository", params=params)
                self.check_for_strings(strings_displayed_in_iframe, strings_not_displayed_in_iframe)
            elif encoded_user_id:
                params = {"user_id": encoded_user_id, "operation": "repositories_by_user"}
                self.visit_url("/repository/browse_repositories", params=params)
                self.check_for_strings(strings_displayed_in_iframe, strings_not_displayed_in_iframe)

    def load_changeset_in_tool_shed(
        self, repository_id, changeset_revision, strings_displayed=None, strings_not_displayed=None
    ):
        # Only used in 0000
        params = {"ctx_str": changeset_revision, "id": repository_id}
        self.visit_url("/repository/view_changeset", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def load_checkable_revisions(self, strings_displayed=None, strings_not_displayed=None):
        params = {
            "do_not_test": "false",
            "downloadable": "true",
            "includes_tools": "true",
            "malicious": "false",
            "missing_test_components": "false",
            "skip_tool_test": "false",
        }
        self.visit_url("/api/repository_revisions", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def load_display_tool_page(
        self,
        repository: Repository,
        tool_xml_path,
        changeset_revision,
        strings_displayed=None,
        strings_not_displayed=None,
    ):
        params = {
            "repository_id": repository.id,
            "tool_config": tool_xml_path,
            "changeset_revision": changeset_revision,
        }
        self.visit_url("/repository/display_tool", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def load_invalid_tool_page(
        self, repository: Repository, tool_xml, changeset_revision, strings_displayed=None, strings_not_displayed=None
    ):
        params = {
            "repository_id": repository.id,
            "tool_config": tool_xml,
            "changeset_revision": changeset_revision,
        }
        self.visit_url("/repository/load_invalid_tool", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def preview_repository_in_tool_shed(
        self,
        name: str,
        owner: str,
        changeset_revision: Optional[str] = None,
        strings_displayed=None,
        strings_not_displayed=None,
    ):
        repository = self._get_repository_by_name_and_owner(name, owner)
        assert repository
        if not changeset_revision:
            changeset_revision = self.get_repository_tip(repository)
        params = {"repository_id": repository.id, "changeset_revision": changeset_revision}
        self.visit_url("/repository/preview_tools_in_changeset", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def reactivate_repository(self, installed_repository):
        self._installation_client.reactivate_repository(installed_repository)

    def reinstall_repository_api(
        self,
        installed_repository,
        install_repository_dependencies=True,
        install_tool_dependencies=False,
        new_tool_panel_section_label="",
    ):
        name = installed_repository.name
        owner = installed_repository.owner
        self._installation_client.install_repository(
            name,
            owner,
            installed_repository.installed_changeset_revision,
            install_tool_dependencies,
            install_repository_dependencies,
            new_tool_panel_section_label,
        )

    def repository_is_new(self, repository: Repository) -> bool:
        repo = self.get_hg_repo(self.get_repo_path(repository))
        tip_ctx = repo[repo.changelog.tip()]
        return tip_ctx.rev() < 0

    def reset_metadata_on_selected_repositories(self, repository_ids):
        if self.is_v2:
            for repository_id in repository_ids:
                self.populator.reset_metadata(repository_id)
        else:
            self.visit_url("/admin/reset_metadata_on_selected_repositories_in_tool_shed")
            kwd = dict(repository_ids=repository_ids)
            self.submit_form(button="reset_metadata_on_selected_repositories_button", **kwd)

    def reset_metadata_on_installed_repositories(self, repositories):
        assert self._installation_client
        self._installation_client.reset_metadata_on_installed_repositories(repositories)

    def reset_repository_metadata(self, repository):
        params = {"id": repository.id}
        self.visit_url("/repository/reset_all_metadata", params=params)
        self.check_for_strings(["All repository metadata has been reset."])

    def revoke_write_access(self, repository, username):
        params = {"user_access_button": "Remove", "id": repository.id, "remove_auth": username}
        self.visit_url("/repository/manage_repository", params=params)

    def search_for_valid_tools(
        self,
        search_fields=None,
        exact_matches=False,
        strings_displayed=None,
        strings_not_displayed=None,
        from_galaxy=False,
    ):
        params = {}
        search_fields = search_fields or {}
        if from_galaxy:
            params["galaxy_url"] = self.galaxy_url
        for field_name, search_string in search_fields.items():
            self.visit_url("/repository/find_tools", params=params)
            self._browser.fill_form_value("find_tools", "exact_matches", exact_matches)
            self._browser.fill_form_value("find_tools", field_name, search_string)
            self._browser.submit_form_with_name("find_tools", "find_tools_submit")
            self.check_for_strings(strings_displayed, strings_not_displayed)

    def set_repository_deprecated(
        self, repository: Repository, set_deprecated=True, strings_displayed=None, strings_not_displayed=None
    ):
        params = {"id": repository.id, "mark_deprecated": set_deprecated}
        self.visit_url("/repository/deprecate", params=params)
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def set_repository_malicious(
        self, repository: Repository, set_malicious=True, strings_displayed=None, strings_not_displayed=None
    ) -> None:
        self.display_manage_repository_page(repository)
        self._browser.fill_form_value("malicious", "malicious", set_malicious)
        self._browser.submit_form_with_name("malicious", "malicious_button")
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def tip_has_metadata(self, repository: Repository) -> bool:
        tip = self.get_repository_tip(repository)
        db_repository = self._db_repository(repository)
        return test_db_util.get_repository_metadata_by_repository_id_changeset_revision(db_repository.id, tip)

    def undelete_repository(self, repository: Repository) -> None:
        params = {"operation": "Undelete", "id": repository.id}
        self.visit_url("/admin/browse_repositories", params=params)
        strings_displayed = ["Undeleted 1 repository", repository.name]
        strings_not_displayed: List[str] = []
        self.check_for_strings(strings_displayed, strings_not_displayed)

    def _uninstall_repository(self, installed_repository: galaxy_model.ToolShedRepository) -> None:
        assert self._installation_client
        self._installation_client.uninstall_repository(installed_repository)

    def update_installed_repository(
        self, installed_repository: galaxy_model.ToolShedRepository, verify_no_updates: bool = False
    ) -> Dict[str, Any]:
        assert self._installation_client
        return self._installation_client.update_installed_repository(installed_repository, verify_no_updates=False)

    def verify_installed_repositories(self, installed_repositories=None, uninstalled_repositories=None):
        installed_repositories = installed_repositories or []
        uninstalled_repositories = uninstalled_repositories or []
        for repository_name, repository_owner in installed_repositories:
            galaxy_repository = self._get_installed_repository_by_name_owner(repository_name, repository_owner)
            if galaxy_repository:
                assert (
                    galaxy_repository.status == "Installed"
                ), f"Repository {repository_name} should be installed, but is {galaxy_repository.status}"

    def verify_installed_repository_metadata_unchanged(self, name, owner):
        installed_repository = self._get_installed_repository_by_name_owner(name, owner)
        assert installed_repository
        metadata = installed_repository.metadata_
        assert self._installation_client
        self._installation_client.reset_installed_repository_metadata(installed_repository)
        new_metadata = installed_repository.metadata_
        assert metadata == new_metadata, f"Metadata for installed repository {name} differs after metadata reset."

    def verify_installed_repository_no_tool_panel_section(self, repository):
        """Verify that there is no 'tool_panel_section' entry in the repository metadata."""
        metadata = repository.metadata_
        assert "tool_panel_section" not in metadata, f"Tool panel section incorrectly found in metadata: {metadata}"

    @property
    def shed_tool_data_table_conf(self):
        return self._installation_client.shed_tool_data_table_conf

    @property
    def tool_data_path(self):
        return self._installation_client.tool_data_path

    def _refresh_tool_shed_repository(self, repo: galaxy_model.ToolShedRepository) -> None:
        assert self._installation_client
        self._installation_client.refresh_tool_shed_repository(repo)

    def verify_installed_repository_data_table_entries(self, required_data_table_entries):
        # The value of the received required_data_table_entries will be something like: [ 'sam_fa_indexes' ]
        shed_tool_data_table_conf = self.shed_tool_data_table_conf
        data_tables, error_message = xml_util.parse_xml(shed_tool_data_table_conf)
        with open(shed_tool_data_table_conf) as f:
            shed_tool_data_table_conf_contents = f.read()
        assert (
            not error_message
        ), f"Failed to parse {shed_tool_data_table_conf} properly. File contents [{shed_tool_data_table_conf_contents}]"
        found = False
        # With the tool shed, the "path" attribute that is hard-coded into the tool_data_tble_conf.xml
        # file is ignored.  This is because the tool shed requires the directory location to which this
        # path points to be empty except when a specific tool is loaded.  The default location for this
        # directory configured for the tool shed is <Galaxy root>/shed-tool-data.  When a tool is loaded
        # in the tool shed, all contained .loc.sample files are copied to this directory and the
        # ToolDataTableManager parses and loads the files in the same way that Galaxy does with a very
        # important exception.  When the tool shed loads a tool and parses and loads the copied ,loc.sample
        # files, the ToolDataTableManager is already instantiated, and so its add_new_entries_from_config_file()
        # method is called and the tool_data_path parameter is used to over-ride the hard-coded "tool-data"
        # directory that Galaxy always uses.
        #
        # Tool data table xml structure:
        # <tables>
        #     <table comment_char="#" name="sam_fa_indexes">
        #        <columns>line_type, value, path</columns>
        #        <file path="tool-data/sam_fa_indices.loc" />
        #     </table>
        # </tables>
        required_data_table_entry = None
        for table_elem in data_tables.findall("table"):
            # The value of table_elem will be something like: <table comment_char="#" name="sam_fa_indexes">
            for required_data_table_entry in required_data_table_entries:
                # The value of required_data_table_entry will be something like: 'sam_fa_indexes'
                if "name" in table_elem.attrib and table_elem.attrib["name"] == required_data_table_entry:
                    found = True
                    # We're processing something like: sam_fa_indexes
                    file_elem = table_elem.find("file")
                    # We have something like: <file path="tool-data/sam_fa_indices.loc" />
                    # The "path" attribute of the "file" tag is the location that Galaxy always uses because the
                    # Galaxy ToolDataTableManager was implemented in such a way that the hard-coded path is used
                    # rather than allowing the location to be a configurable setting like the tool shed requires.
                    file_path = file_elem.get("path", None)
                    # The value of file_path will be something like: "tool-data/all_fasta.loc"
                    assert (
                        file_path is not None
                    ), f'The "path" attribute is missing for the {required_data_table_entry} entry.'
                    # The following test is probably not necesary, but the tool-data directory should exist!
                    galaxy_tool_data_dir, loc_file_name = os.path.split(file_path)
                    assert (
                        galaxy_tool_data_dir is not None
                    ), f"The hard-coded Galaxy tool-data directory is missing for the {required_data_table_entry} entry."
                    assert os.path.exists(galaxy_tool_data_dir), "The Galaxy tool-data directory does not exist."
                    # Make sure the loc_file_name was correctly copied into the configured directory location.
                    configured_file_location = os.path.join(self.tool_data_path, loc_file_name)
                    assert os.path.isfile(
                        configured_file_location
                    ), f'The expected copied file "{configured_file_location}" is missing.'
                    # We've found the value of the required_data_table_entry in data_tables, which is the parsed
                    # shed_tool_data_table_conf.xml, so all is well!
                    break
            if found:
                break
        # We better have an entry like: <table comment_char="#" name="sam_fa_indexes"> in our parsed data_tables
        # or we know that the repository was not correctly installed!
        if not found:
            if required_data_table_entry is None:
                raise AssertionError(
                    f"No tables found in {shed_tool_data_table_conf}. File contents {shed_tool_data_table_conf_contents}"
                )
            else:
                raise AssertionError(
                    f"No entry for {required_data_table_entry} in {shed_tool_data_table_conf}. File contents {shed_tool_data_table_conf_contents}"
                )

    def _get_installed_repository_by_name_owner(
        self, repository_name: str, repository_owner: str
    ) -> galaxy_model.ToolShedRepository:
        assert self._installation_client
        return self._installation_client.get_installed_repository_by_name_owner(repository_name, repository_owner)

    def _get_installed_repositories_by_name_owner(
        self, repository_name: str, repository_owner: str
    ) -> List[galaxy_model.ToolShedRepository]:
        assert self._installation_client
        return self._installation_client.get_installed_repositories_by_name_owner(repository_name, repository_owner)

    def _get_installed_repository_for(
        self, owner: Optional[str] = None, name: Optional[str] = None, changeset: Optional[str] = None
    ):
        assert self._installation_client
        return self._installation_client.get_installed_repository_for(owner=owner, name=name, changeset=changeset)

    def _assert_has_installed_repos_with_names(self, *names):
        for name in names:
            assert self._get_installed_repository_for(name=name)

    def _assert_has_no_installed_repos_with_names(self, *names):
        for name in names:
            assert not self._get_installed_repository_for(name=name)

    def _assert_has_missing_dependency(
        self, installed_repository: galaxy_model.ToolShedRepository, repository_name: str
    ) -> None:
        json = self.display_installed_repository_manage_json(installed_repository)
        assert (
            "missing_repository_dependencies" in json
        ), f"Expecting missing dependency {repository_name} but no missing dependencies found."
        missing_repository_dependencies = json["missing_repository_dependencies"]
        folder = missing_repository_dependencies["folders"][0]
        assert "repository_dependencies" in folder
        rds = folder["repository_dependencies"]
        found_missing_repository_dependency = False
        missing_repos = set()
        for rd in rds:
            missing_repos.add(rd["repository_name"])
            if rd["repository_name"] == repository_name:
                found_missing_repository_dependency = True
        assert (
            found_missing_repository_dependency
        ), f"Expecting missing dependency {repository_name} but the missing repositories were {missing_repos}."

    def _assert_has_installed_repository_dependency(
        self,
        installed_repository: galaxy_model.ToolShedRepository,
        repository_name: str,
        changeset: Optional[str] = None,
    ) -> None:
        json = self.display_installed_repository_manage_json(installed_repository)
        if "repository_dependencies" not in json:
            name = installed_repository.name
            raise AssertionError(f"No repository dependencies were defined in {name}. manage json is {json}")
        repository_dependencies = json["repository_dependencies"]
        found = False
        for folder in repository_dependencies.get("folders"):
            for rd in folder["repository_dependencies"]:
                if rd["repository_name"] != repository_name:
                    continue
                if changeset and rd["changeset_revision"] != changeset:
                    continue
                found = True
                break
        assert found, f"Failed to find target repository dependency in {json}"

    def _assert_is_not_missing_dependency(
        self, installed_repository: galaxy_model.ToolShedRepository, repository_name: str
    ) -> None:
        json = self.display_installed_repository_manage_json(installed_repository)
        if "missing_repository_dependencies" not in json:
            return

        missing_repository_dependencies = json["missing_repository_dependencies"]
        folder = missing_repository_dependencies["folders"][0]
        assert "repository_dependencies" in folder
        rds = folder["repository_dependencies"]
        found_missing_repository_dependency = False
        for rd in rds:
            if rd["repository_name"] == repository_name:
                found_missing_repository_dependency = True
        assert not found_missing_repository_dependency

    def _assert_has_valid_tool_with_name(self, tool_name: str) -> None:
        def assert_has():
            assert self._installation_client
            tool_names = self._installation_client.get_tool_names()
            assert tool_name in tool_names

        # May need to wait on toolbox reload.
        wait_on_assertion(assert_has, f"toolbox to contain {tool_name}", 10)

    def _assert_repo_has_tool_with_id(
        self, installed_repository: galaxy_model.ToolShedRepository, tool_id: str
    ) -> None:
        assert "tools" in installed_repository.metadata_, f"No valid tools were defined in {installed_repository.name}."
        tools = installed_repository.metadata_["tools"]
        found_it = False
        for tool in tools:  # type:ignore[attr-defined]
            if "id" not in tool:
                continue
            if tool["id"] == tool_id:
                found_it = True
                break
        assert found_it, f"Did not find valid tool with name {tool_id} in {tools}"

    def _assert_repo_has_invalid_tool_in_file(
        self, installed_repository: galaxy_model.ToolShedRepository, name: str
    ) -> None:
        assert (
            "invalid_tools" in installed_repository.metadata_
        ), f"No invalid tools were defined in {installed_repository.name}."
        invalid_tools = installed_repository.metadata_["invalid_tools"]
        found_it = name in invalid_tools
        assert found_it, f"Did not find invalid tool file {name} in {invalid_tools}"

    def verify_unchanged_repository_metadata(self, repository: Repository):
        old_metadata = {}
        new_metadata = {}
        for metadata in self.get_repository_metadata(repository):
            old_metadata[metadata.changeset_revision] = metadata.metadata
        self.reset_repository_metadata(repository)
        for metadata in self.get_repository_metadata(repository):
            new_metadata[metadata.changeset_revision] = metadata.metadata
        # Python's dict comparison recursively compares sorted key => value pairs and returns true if any key or value differs,
        # or if the number of keys differs.
        assert old_metadata == new_metadata, f"Metadata changed after reset on repository {repository.name}."


def _wait_for_installation(repository: galaxy_model.ToolShedRepository, refresh):
    final_states = [
        galaxy_model.ToolShedRepository.installation_status.ERROR,
        galaxy_model.ToolShedRepository.installation_status.INSTALLED,
    ]
    # Wait until all repositories are in a final state before returning. This ensures that subsequent tests
    # are running against an installed repository, and not one that is still in the process of installing.
    timeout_counter = 0
    while repository.status not in final_states:
        refresh(repository)
        timeout_counter = timeout_counter + 1
        # This timeout currently defaults to 10 minutes.
        if timeout_counter > repository_installation_timeout:
            raise AssertionError(
                "Repository installation timed out, %d seconds elapsed, repository state is %s."
                % (timeout_counter, repository.status)
            )
        time.sleep(1)


def _get_tool_panel_section_from_repository_metadata(metadata):
    tool_metadata = metadata["tools"]
    tool_guid = tool_metadata[0]["guid"]
    assert "tool_panel_section" in metadata, f"Tool panel section not found in metadata: {metadata}"
    tool_panel_section_metadata = metadata["tool_panel_section"]
    tool_panel_section = tool_panel_section_metadata[tool_guid][0]["name"]
    return tool_panel_section


def get_installed_repository(session, name, owner, changeset):
    ToolShedRepository = galaxy_model.ToolShedRepository
    stmt = select(ToolShedRepository)
    if name is not None:
        stmt = stmt.where(ToolShedRepository.name == name)
    if owner is not None:
        stmt = stmt.where(ToolShedRepository.owner == owner)
    if changeset is not None:
        stmt = stmt.where(ToolShedRepository.changeset_revision == changeset)
    stmt = stmt.where(ToolShedRepository.deleted == false())
    stmt = stmt.where(ToolShedRepository.uninstalled == false())
    return session.scalars(stmt).one_or_none()
