import os
from os import PathLike
from typing import (
    List,
    Literal,
    Optional,
    overload,
    TYPE_CHECKING,
    Union,
)
from uuid import UUID

from sqlalchemy import select

from galaxy.model import (
    DynamicTool,
    GalaxyToolSourceAssociation,
    ToolSource,
    User,
)
from galaxy.tool_util.deps import (
    build_dependency_manager,
    NullDependencyManager,
)
from galaxy.tool_util.toolbox import AbstractToolBox
from galaxy.tools import (
    create_tool_from_representation,
    Tool,
)


class DatabaseToolBox(AbstractToolBox):

    def __init__(
        self,
        config_filenames: List[str],
        tool_root_dir,
        app,
        view_sources=None,
        default_panel_view="default",
        save_integrated_tool_panel: bool = True,
    ) -> None:
        super().__init__(
            config_filenames, tool_root_dir, app, view_sources, default_panel_view, save_integrated_tool_panel
        )
        self._init_dependency_manager()

    def load_tool(
        self, config_file: str | PathLike[str], guid=None, tool_shed_repository=None, use_cached: bool = False, **kwds
    ) -> Tool:
        pass

    def register_tool(self, tool: Tool) -> None:
        pass

    def create_dynamic_tool(self, dynamic_tool: DynamicTool) -> Tool:
        return super().create_dynamic_tool(dynamic_tool)

    def _init_integrated_tool_panel(self, config):
        pass

    def _init_tools_from_configs(self, config):
        pass

    def tool_tag_manager(self):
        pass

    def _init_dependency_manager(self):
        use_tool_dependency_resolution = getattr(self.app, "use_tool_dependency_resolution", True)
        if not use_tool_dependency_resolution:
            self.dependency_manager = NullDependencyManager()
            return
        app_config_dict = self.app.config.config_dict
        conf_file = app_config_dict.get("dependency_resolvers_config_file")
        default_tool_dependency_dir = os.path.join(
            self.app.config.data_dir, self.app.config.schema.defaults["tool_dependency_dir"]
        )
        self.dependency_manager = build_dependency_manager(
            app_config_dict=app_config_dict,
            conf_file=conf_file,
            default_tool_dependency_dir=default_tool_dependency_dir,
        )

    @overload
    def get_tool(
        self,
        tool_id: Optional[str] = None,
        tool_version: Optional[str] = None,
        tool_uuid: Optional[Union[UUID, str]] = None,
        get_all_versions: Literal[False] = False,
        exact: Optional[bool] = False,
        user: Optional["User"] = None,
    ) -> Optional["Tool"]: ...

    @overload
    def get_tool(
        self,
        tool_id: Optional[str] = None,
        tool_version: Optional[str] = None,
        tool_uuid: Optional[Union[UUID, str]] = None,
        get_all_versions: Literal[True] = True,
        exact: Optional[bool] = False,
        user: Optional["User"] = None,
    ) -> list["Tool"]: ...

    def get_tool(
        self,
        tool_id: Optional[str] = None,
        tool_version: Optional[str] = None,
        tool_uuid: Optional[Union[UUID, str]] = None,
        get_all_versions: Optional[bool] = False,
        exact: Optional[bool] = False,
        user: Optional["User"] = None,
    ) -> Union[Optional["Tool"], list["Tool"]]:
        if tool_id:
            stmt = (
                select(ToolSource.source, ToolSource.tool_source_class, GalaxyToolSourceAssociation.tool_dir)
                .join(GalaxyToolSourceAssociation, ToolSource.id == GalaxyToolSourceAssociation.tool_source_id)
                .where(GalaxyToolSourceAssociation.tool_id == tool_id)
            )
            row = self.app.model.session.execute(stmt).one_or_none()
            if row:
                source, tool_source_class, tool_dir = row
                return create_tool_from_representation(
                    app=self.app, raw_tool_source=source, tool_dir=tool_dir, tool_source_class=tool_source_class
                )
        return
