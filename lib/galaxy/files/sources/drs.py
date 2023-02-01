import logging

from galaxy.util.drs import fetch_drs_to_file

from . import BaseFilesSource

log = logging.getLogger(__name__)


class DRSFilesSource(BaseFilesSource):
    plugin_type = "drs"

    def __init__(self, label="DRS file", doc="DRS file handler", **kwd):
        kwds = dict(
            id="_drs",
            label=label,
            doc=doc,
            writable=False,
        )
        kwds.update(kwd)
        props = self._parse_common_config_opts(kwds)
        self._props = props

    def _realize_to(self, source_path, native_path, user_context=None):
        props = self._serialization_props(user_context)
        headers = props.pop("http_headers", {}) or {}
        fetch_drs_to_file(source_path, native_path, headers=headers)

    def _write_from(self, target_path, native_path, user_context=None):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if url.startswith("drs://"):
            return len("drs://")
        else:
            return 0

__all__ = ("DRSFilesSource",)
