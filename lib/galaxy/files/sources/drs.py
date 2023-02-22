import logging
from typing import Optional

from typing_extensions import Unpack

from galaxy.util.drs import fetch_drs_to_file
from . import (
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
)

log = logging.getLogger(__name__)


class DRSFilesSource(BaseFilesSource):
    plugin_type = "drs"

    def __init__(self, **kwd: Unpack[FilesSourceProperties]):
        kwds: FilesSourceProperties = dict(
            id="_drs",
            label="DRS file",
            doc="DRS file handler",
            writable=False,
        )
        kwds.update(kwd)
        props = self._parse_common_config_opts(kwds)
        self._props = props

    def _realize_to(self, source_path, native_path, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        headers = props.pop("http_headers", {}) or {}
        fetch_drs_to_file(source_path, native_path, user_context, headers=headers)

    def _write_from(self, target_path, native_path, user_context=None, opts: Optional[FilesSourceOptions] = None):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if url.startswith("drs://"):
            return len("drs://")
        else:
            return 0

    def _serialization_props(self, user_context=None):
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return effective_props


__all__ = ("DRSFilesSource",)
