import errno
import logging
import os
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from typing_extensions import Protocol

from galaxy import util
from galaxy.structured_app import StructuredApp
from galaxy.tool_shed.galaxy_install.client import DataManagersInterface
from galaxy.tool_util.data import (
    BundleProcessingOptions,
    OutputDataset,
)
from galaxy.tool_util.data.bundles.models import (
    convert_data_tables_xml,
    RepoInfo,
)
from galaxy.util import Element

log = logging.getLogger(__name__)


class DataManagers(DataManagersInterface):
    data_managers: Dict[str, "DataManager"]
    managed_data_tables: Dict[str, "DataManager"]
    __reload_count: int

    def __init__(self, app: StructuredApp, xml_filename=None, reload_count: Optional[int] = None):
        self.app = app
        self.data_managers = {}
        self.managed_data_tables = {}
        self.tool_path: Optional[str] = None
        self.__reload_count = reload_count or 0
        self.filename = xml_filename or self.app.config.data_manager_config_file
        for filename in util.listify(self.filename):
            if not filename:
                continue
            self.load_from_xml(filename)
        if self.app.config.shed_data_manager_config_file:
            try:
                self.load_from_xml(self.app.config.shed_data_manager_config_file, store_tool_path=True)
            except OSError as exc:
                if exc.errno != errno.ENOENT or self.app.config.is_set("shed_data_manager_config_file"):
                    raise

    @property
    def _reload_count(self) -> int:
        return self.__reload_count

    def load_from_xml(self, xml_filename, store_tool_path=True) -> None:
        try:
            tree = util.parse_xml(xml_filename)
        except OSError as e:
            if e.errno != errno.ENOENT or self.app.config.is_set("data_manager_config_file"):
                raise
            return  # default config option and it doesn't exist, which is fine
        except Exception as e:
            log.error(f'There was an error parsing your Data Manager config file "{xml_filename}": {e}')
            return  # we are not able to load any data managers
        root = tree.getroot()
        if root.tag != "data_managers":
            log.error(
                f'A data managers configuration must have a "data_managers" tag as the root. "{root.tag}" is present'
            )
            return
        if store_tool_path:
            tool_path = root.get("tool_path", None)
            if tool_path is None:
                tool_path = self.app.config.tool_path
            if not tool_path:
                tool_path = "."
            self.tool_path = tool_path
        for data_manager_elem in root.findall("data_manager"):
            if not self.load_manager_from_elem(data_manager_elem, tool_path=self.tool_path):
                # Wasn't able to load manager, could happen when galaxy is managed by planemo.
                # Fall back to loading relative to the data_manager_conf.xml file
                tool_path = os.path.dirname(xml_filename)
                self.load_manager_from_elem(data_manager_elem, tool_path=tool_path)

    def load_manager_from_elem(self, data_manager_elem, tool_path=None, add_manager=True) -> Optional["DataManager"]:
        try:
            data_manager = DataManager(self, data_manager_elem, tool_path=tool_path)
        except OSError as e:
            if e.errno == errno.ENOENT:
                # File does not exist
                return None
        except Exception:
            log.exception("Error loading data_manager")
            return None
        if add_manager:
            self.add_manager(data_manager)
        log.debug(f"Loaded Data Manager: {data_manager.id}")
        return data_manager

    def add_manager(self, data_manager):
        if data_manager.id in self.data_managers:
            log.warning(f"A data manager has been defined twice: {data_manager.id} ")
        self.data_managers[data_manager.id] = data_manager
        for data_table_name in data_manager.data_table_names:
            if data_table_name not in self.managed_data_tables:
                self.managed_data_tables[data_table_name] = []
            self.managed_data_tables[data_table_name].append(data_manager)

    def get_manager(self, *args, **kwds):
        return self.data_managers.get(*args, **kwds)

    def remove_manager(self, manager_ids: Union[str, List[str]]) -> None:
        if not isinstance(manager_ids, list):
            manager_ids = [manager_ids]
        for manager_id in manager_ids:
            data_manager = self.get_manager(manager_id, None)
            if data_manager is not None:
                del self.data_managers[manager_id]
                # remove tool from toolbox
                if data_manager.tool:
                    self.app.toolbox.remove_tool_by_id(data_manager.tool.id)
                # determine if any data_tables are no longer tracked
                for data_table_name in data_manager.data_table_names:
                    remove_data_table_tracking = True
                    for other_data_manager in self.data_managers.values():
                        if data_table_name in other_data_manager.data_table_names:
                            remove_data_table_tracking = False
                            break
                    if remove_data_table_tracking and data_table_name in self.managed_data_tables:
                        del self.managed_data_tables[data_table_name]


class Tool(Protocol):
    name: str
    description: str
    version: str


class DataManager:
    GUID_TYPE = "data_manager"
    DEFAULT_VERSION = "0.0.1"

    tool: Optional[Tool]

    def __init__(self, data_managers: DataManagers, elem: Optional[Element] = None, tool_path: Optional[str] = None):
        self.data_managers = data_managers
        self.declared_id: Optional[str] = None
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.version = self.DEFAULT_VERSION
        self.guid: Optional[str] = None
        self.tool = None
        self.tool_shed_repository_info: Optional[RepoInfo] = None
        self.undeclared_tables = False
        if elem is not None:
            self._load_from_element(elem, tool_path or self.data_managers.tool_path)

    def _load_from_element(self, elem: Element, tool_path: Optional[str]) -> None:
        assert (
            elem.tag == "data_manager"
        ), f'A data manager configuration must have a "data_manager" tag as the root. "{elem.tag}" is present'
        self.declared_id = elem.get("id")
        self.guid = elem.get("guid")
        path = elem.get("tool_file")
        tool_shed_repository = None
        tool_guid = None

        if path is None:
            tool_elem = elem.find("tool")
            assert (
                tool_elem is not None
            ), f"Error loading tool for data manager. Make sure that a tool_file attribute or a tool tag set has been defined:\n{util.xml_to_string(elem)}"
            path = tool_elem.get("file")
            tool_guid = tool_elem.get("guid")
            # need to determine repository info so that dependencies will work correctly
            tool_shed_repository = self.data_managers.app.toolbox.get_tool_repository_from_xml_item(tool_elem, path)
            self.tool_shed_repository_info = RepoInfo(
                tool_shed=tool_shed_repository.tool_shed,
                name=tool_shed_repository.name,
                owner=tool_shed_repository.owner,
                installed_changeset_revision=tool_shed_repository.installed_changeset_revision,
            )
            # use shed_conf_file to determine tool_path
            shed_conf_file = elem.get("shed_conf_file")
            if shed_conf_file:
                shed_conf = self.data_managers.app.toolbox.get_shed_config_dict_by_filename(shed_conf_file)
                if shed_conf:
                    tool_path = shed_conf.get("tool_path", tool_path)
        assert path is not None, f"A tool file path could not be determined:\n{util.xml_to_string(elem)}"
        assert tool_path, "A tool root path is required"
        self._load_tool(
            os.path.join(tool_path, path),
            guid=tool_guid,
            data_manager_id=self.id,
            tool_shed_repository=tool_shed_repository,
        )
        assert self.tool
        self.name = elem.get("name", self.tool.name)
        self.description = elem.get("description", self.tool.description)
        self.version = elem.get("version", self.tool.version)
        self.processor_description = convert_data_tables_xml(elem)

    @property
    def id(self):
        return self.guid or self.declared_id  # if we have a guid, we will use that as the data_manager id

    @property
    def data_table_names(self):
        return self.processor_description.data_table_names

    def _load_tool(
        self, tool_filename, guid=None, data_manager_id=None, tool_shed_repository_id=None, tool_shed_repository=None
    ):
        toolbox = self.data_managers.app.toolbox
        tool = toolbox.load_hidden_tool(
            tool_filename,
            guid=guid,
            data_manager_id=data_manager_id,
            repository_id=tool_shed_repository_id,
            tool_shed_repository=tool_shed_repository,
            use_cached=True,
        )
        self.data_managers.app.toolbox.data_manager_tools[tool.id] = tool
        self.tool = tool
        return tool

    def process_result(self, out_data: Dict[str, OutputDataset]) -> None:
        tool_data_tables = self.data_managers.app.tool_data_tables
        options = BundleProcessingOptions(
            what=f"data manager '{self.id}'",
            data_manager_path=self._data_manager_path,
            target_config_file=self.data_managers.filename,
        )
        updated_data_tables = tool_data_tables.process_bundle(
            out_data,
            self.processor_description,
            self.repo_info,
            options,
        )
        for data_table_name in updated_data_tables:
            self._reload(data_table_name)

    def write_bundle(
        self,
        out_data: Dict[str, OutputDataset],
    ) -> Dict[str, OutputDataset]:
        tool_data_tables = self.data_managers.app.tool_data_tables
        return tool_data_tables.write_bundle(
            out_data,
            self.processor_description,
            self.repo_info,
        )

    @property
    def _data_manager_path(self) -> str:
        return self.data_managers.app.config.galaxy_data_manager_data_path

    def _reload(self, data_table_name: str) -> None:
        self.data_managers.app.queue_worker.send_control_task(
            "reload_tool_data_tables", noop_self=True, kwargs={"table_name": data_table_name}
        )

    @property
    def repo_info(self) -> Optional[RepoInfo]:
        return self.tool_shed_repository_info

    # legacy stuff because tool shed code calls this...
    # data manager manual integration test provides coverage
    def get_tool_shed_repository_info_dict(self) -> Optional[dict]:
        repo_info = self.repo_info
        return repo_info.model_dump(mode="json") if repo_info else None
