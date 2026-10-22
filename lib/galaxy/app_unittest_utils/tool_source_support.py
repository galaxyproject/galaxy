import os
from typing import Any


class PopulateConfig:
    """Minimal config the tool source store populator reads, with a sqlite store under ``root``."""

    enable_beta_tool_formats = False
    tool_search_index_dir = None
    data_manager_config_file: str | None = None
    shed_data_manager_config_file: str | None = None
    biotools_content_directory = None
    biotools_use_api = False
    biotools_service_cache_type = "memory"
    biotools_service_cache_data_dir = None
    biotools_service_cache_lock_dir = None
    biotools_service_cache_url = None
    biotools_service_cache_table_name = None
    biotools_service_cache_schema_name = None

    def __init__(self, root: str | os.PathLike[str], tool_conf: str | os.PathLike[str]):
        self.root = str(root)
        self.tool_path = str(root)
        self.tool_source_database_connection = f"sqlite:///{root}/ts.sqlite"
        self.tool_source_stores: dict[str, Any] = {}
        self._tool_conf = str(tool_conf)

    def all_tool_config_files(self) -> list[str]:
        return [self._tool_conf]
