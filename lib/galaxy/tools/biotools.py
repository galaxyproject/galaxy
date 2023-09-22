"""Adapt Galaxy-agnostic abstraction galaxy.tool_util.biotools to Galaxy config and dependencies."""

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from galaxy.tool_util.biotools import (
    BiotoolsMetadataSource,
    BiotoolsMetadataSourceConfig,
    get_biotools_metadata_source,
)


def get_galaxy_biotools_metadata_source(config) -> BiotoolsMetadataSource:
    """Build a BiotoolsMetadataSource from a Galaxy configuration object."""
    biotools_metadata_source_config = BiotoolsMetadataSourceConfig()
    biotools_metadata_source_config.content_directory = config.biotools_content_directory
    biotools_metadata_source_config.use_api = config.biotools_use_api
    cache_opts = {
        "cache.type": config.biotools_service_cache_type,
        "cache.data_dir": config.biotools_service_cache_data_dir,
        "cache.lock_dir": config.biotools_service_cache_lock_dir,
        "cache.url": config.biotools_service_cache_url,
        "cache.table_name": config.biotools_service_cache_table_name,
        "cache.schema_name": config.biotools_service_cache_schema_name,
    }
    cache = CacheManager(**parse_cache_config_options(cache_opts)).get_cache("doi")
    biotools_metadata_source_config.cache = cache
    return get_biotools_metadata_source(biotools_metadata_source_config)
