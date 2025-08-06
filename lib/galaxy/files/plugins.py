from typing import (
    cast,
    TYPE_CHECKING,
)

from galaxy.files.models import FileSourcePluginsConfig
from galaxy.util.plugin_config import (
    load_plugins,
    PluginConfigSource,
    plugins_dict,
)

if TYPE_CHECKING:
    from galaxy.files.sources import BaseFilesSource


class FileSourcePluginLoader:

    def __init__(self):
        self._plugin_classes = self._file_source_plugins_dict()

    def _file_source_plugins_dict(self):
        import galaxy.files.sources

        return plugins_dict(galaxy.files.sources, "plugin_type")

    def get_plugin_type_class(self, plugin_type: str) -> type["BaseFilesSource"]:
        return cast(type["BaseFilesSource"], self._plugin_classes[plugin_type])

    def load_plugins(
        self, plugin_source: PluginConfigSource, file_source_plugin_config: FileSourcePluginsConfig
    ) -> list["BaseFilesSource"]:
        extra_kwds = {
            "file_sources_config": file_source_plugin_config,
        }
        return load_plugins(
            self._plugin_classes,
            plugin_source,
            extra_kwds,
            dict_to_list_key="id",
        )


__all__ = (
    "FileSourcePluginLoader",
    "FileSourcePluginsConfig",
)
