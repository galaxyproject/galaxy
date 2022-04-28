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
        "cache.type": getattr(config, "biotools_service_cache_type", "file"),
        "cache.data_dir": getattr(config, "biotools_service_cache_data_dir", None),
        "cache.lock_dir": getattr(config, "biotools_service_cache_lock_dir", None),
    }
    cache = CacheManager(**parse_cache_config_options(cache_opts)).get_cache("doi")
    biotools_metadata_source_config.cache = cache
    return get_biotools_metadata_source(biotools_metadata_source_config)
