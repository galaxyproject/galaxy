import threading
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Union,
)

from galaxy.model.migrations import (
    DatabaseStateVerifier,
    TSI,
)
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.tool_shed_install import mapping as install_mapping
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tool_shed.cache import ToolShedRepositoryCache
from galaxy.tool_shed.galaxy_install.client import (
    DataManagerInterface,
    DataManagersInterface,
    InstallationTarget,
)
from galaxy.tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from galaxy.tool_shed.util.repository_util import get_installed_repository
from galaxy.tool_util.data import (
    OutputDataset,
    ToolDataTableManager,
)
from galaxy.tool_util.loader_directory import looks_like_a_tool
from galaxy.tool_util.toolbox.base import (
    AbstractToolBox,
    NullToolTagManager,
)
from galaxy.tool_util.toolbox.watcher import (
    get_tool_conf_watcher,
    get_tool_watcher,
)
from galaxy.util.tool_shed.tool_shed_registry import Registry


class ToolShedTarget(NamedTuple):
    url: str
    name: str

    @property
    def as_str(self) -> str:
        return f"""<?xml version="1.0"?>
<tool_sheds>
    <tool_shed name="{self.name}" url="{self.url}"/>
</tool_sheds>
"""


EMPTY_TOOL_DATA_TABLE_CONFIG = """<?xml version="1.0"?>
<tables>
</tables>
"""


class Config:
    tool_data_path: str
    install_database_connection: str
    install_database_engine_options: Dict[str, Any] = {}
    update_integrated_tool_panel: bool = True
    integrated_tool_panel_config: str
    shed_tool_config_file: str
    shed_tool_data_path: str
    migrated_tools_config: Optional[str] = None
    shed_tools_dir: str
    edam_panel_views: list = []
    tool_configs: list = []
    shed_tool_data_table_config: str
    shed_data_manager_config_file: str

    def get(self, key, default):
        return getattr(self, key, default)


class TestTool:
    _macro_paths: List[str] = []
    params_with_missing_data_table_entry: list = []
    params_with_missing_index_file: list = []

    def __init__(self, config_file, tool_shed_repository, guid):
        self.config_file = config_file
        self.tool_shed_repository = tool_shed_repository
        self.guid = guid
        self.id = guid
        self.old_id = guid
        self.version = "1.0.0"
        self.hidden = False
        self._lineage = None
        self.name = "test_tool"

    @property
    def lineage(self):
        return self._lineage


class TestToolBox(AbstractToolBox):
    def create_tool(self, config_file, tool_cache_data_dir=None, **kwds):
        tool = TestTool(config_file, kwds["tool_shed_repository"], kwds["guid"])
        tool._lineage = self._lineage_map.register(tool)  # cleanup?
        return tool

    def _get_tool_shed_repository(self, tool_shed, name, owner, installed_changeset_revision):
        return get_installed_repository(
            self.app,
            tool_shed=tool_shed,
            name=name,
            owner=owner,
            installed_changeset_revision=installed_changeset_revision,
            from_cache=True,
        )

    def _looks_like_a_tool(self, path):
        return looks_like_a_tool(path, enable_beta_formats=False)

    def tool_tag_manager(self):
        return NullToolTagManager()


class Watchers:
    def __init__(self, app):
        self.app = app
        self.tool_config_watcher = get_tool_conf_watcher(
            reload_callback=self.app.reload_toolbox,
            tool_cache=None,
        )
        self.tool_watcher = get_tool_watcher(self, app.config)


class DummyDataManager(DataManagerInterface):
    GUID_TYPE: str = "data_manager"
    DEFAULT_VERSION: str = "0.0.1"

    def process_result(self, out_data):
        return None

    def write_bundle(self, out) -> Dict[str, OutputDataset]:
        return {}


class StandaloneDataManagers(DataManagersInterface):
    __reload_count = 0

    def load_manager_from_elem(
        self, data_manager_elem, tool_path=None, add_manager=True
    ) -> Optional[DataManagerInterface]:
        return DummyDataManager()

    def get_manager(self, data_manager_id: str) -> Optional[DataManagerInterface]:
        return None

    def remove_manager(self, manager_ids: Union[str, List[str]]) -> None:
        return None

    @property
    def _reload_count(self) -> int:
        self.__reload_count += 1
        return self.__reload_count


class StandaloneInstallationTarget(InstallationTarget):
    name: str = "galaxy"
    tool_shed_registry: Registry
    security: IdEncodingHelper
    _toolbox: TestToolBox
    _toolbox_lock: threading.RLock = threading.RLock()
    tool_shed_repository_cache: Optional[ToolShedRepositoryCache] = None
    data_managers = StandaloneDataManagers()

    def __init__(
        self,
        target_directory: Path,
        tool_shed_target: Optional[ToolShedTarget] = None,
    ):
        tool_root_dir = target_directory / "tools"
        config: Config = Config()
        install_db_path = str(target_directory / "install.sqlite")
        config.tool_data_path = str(target_directory / "tool_data")
        config.shed_tool_data_path = config.tool_data_path
        config.install_database_connection = f"sqlite:///{install_db_path}?isolation_level=IMMEDIATE"
        config.integrated_tool_panel_config = str(target_directory / "integrated.xml")
        config.shed_tool_data_table_config = str(target_directory / "shed_tool_data_table_conf.xml")
        shed_conf = target_directory / "shed_conf.xml"
        shed_data_manager_config_file = target_directory / "shed_data_manager_conf.xml"
        config.shed_data_manager_config_file = str(shed_data_manager_config_file)
        config.shed_tool_config_file = str(shed_conf)
        shed_conf.write_text(f'<?xml version="1.0"?>\n<toolbox tool_path="{tool_root_dir}"></toolbox>')
        (target_directory / "shed_tool_data_table_conf.xml").write_text(EMPTY_TOOL_DATA_TABLE_CONFIG)
        self.config = config
        install_engine = build_engine(config.install_database_connection, config.install_database_engine_options)
        self.security = IdEncodingHelper(id_secret="notasecretfortests")
        DatabaseStateVerifier(
            install_engine,
            TSI,
            None,
            None,
            True,
            False,
        ).run()
        self.install_model = install_mapping.configure_model_mapping(install_engine)
        registry_config: Optional[Path] = None
        if tool_shed_target:
            registry_config = target_directory / "tool_sheds_conf.xml"
            with registry_config.open("w") as f:
                f.write(tool_shed_target.as_str)

        self.tool_shed_registry = Registry(registry_config)
        self.tool_root_dir = tool_root_dir
        self.tool_root_dir.mkdir()
        config.shed_tools_dir = str(tool_root_dir)
        self.watchers = Watchers(self)
        self.reload_toolbox()
        self.tool_data_tables = ToolDataTableManager(
            tool_data_path=self.config.tool_data_path,
            config_filename=self.config.shed_tool_data_table_config,
            other_config_dict=self.config,
        )
        dependency_dir = target_directory / "_dependencies"
        dependency_dir.mkdir()
        self.installed_repository_manager = InstalledRepositoryManager(self)

    @property
    def tool_dependency_dir(self) -> Optional[str]:
        return None

    def reload_toolbox(self):
        self._toolbox = TestToolBox(
            config_filenames=[self.config.shed_tool_config_file],
            tool_root_dir=self.tool_root_dir,
            app=self,
        )

    @property
    def toolbox(self) -> TestToolBox:
        return self._toolbox

    def wait_for_toolbox_reload(self, toolbox):
        return
