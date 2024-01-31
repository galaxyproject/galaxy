import threading
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from typing_extensions import Protocol

from galaxy.model.base import ModelMapping
from galaxy.model.tool_shed_install import HasToolBox
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tool_shed.cache import ToolShedRepositoryCache
from galaxy.tool_util.data import (
    OutputDataset,
    ToolDataTableManager,
)
from galaxy.tool_util.toolbox.base import AbstractToolBox

if TYPE_CHECKING:
    import galaxy.tool_shed.metadata.installed_repository_manger


class DataManagerInterface(Protocol):
    GUID_TYPE: str = "data_manager"
    DEFAULT_VERSION: str = "0.0.1"

    def process_result(self, out_data): ...

    def write_bundle(self, out: Dict[str, OutputDataset]) -> Dict[str, OutputDataset]: ...


class DataManagersInterface(Protocol):
    @property
    def _reload_count(self) -> int: ...

    def load_manager_from_elem(
        self, data_manager_elem, tool_path=None, add_manager=True
    ) -> Optional[DataManagerInterface]: ...

    def get_manager(self, data_manager_id: str) -> Optional[DataManagerInterface]: ...

    def remove_manager(self, manager_ids: Union[str, List[str]]) -> None: ...


ToolBoxType = TypeVar("ToolBoxType", bound="AbstractToolBox")


class InstallationTarget(HasToolBox, Generic[ToolBoxType]):
    data_managers: DataManagersInterface
    install_model: ModelMapping
    model: ModelMapping
    security: IdEncodingHelper
    config: Any
    installed_repository_manager: "galaxy.tool_shed.metadata.installed_repository_manger.InstalledRepositoryManager"
    watchers: Any  # TODO: interface...
    _toolbox_lock: threading.RLock
    tool_shed_repository_cache: Optional[ToolShedRepositoryCache]
    tool_data_tables: ToolDataTableManager

    def wait_for_toolbox_reload(self, old_toolbox: ToolBoxType) -> None: ...
