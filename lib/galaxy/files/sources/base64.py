import base64
import logging

from . import BaseFilesSource

log = logging.getLogger(__name__)


class Base64FilesSource(BaseFilesSource):
    plugin_type = "base64"

    def __init__(self, label="Base64 encoded string", doc="Base64 string handler", **kwd):
        kwds = dict(
            id="_base64",
            label=label,
            doc=doc,
            writable=False,
        )
        kwds.update(kwd)
        props = self._parse_common_config_opts(kwds)
        self._props = props

    def _realize_to(self, source_path, native_path, user_context=None, extra_props=None):
        with open(native_path, "wb") as temp:
            temp.write(base64.b64decode(source_path[len("base64://"):]))
            temp.flush()

    def _write_from(self, target_path, native_path, user_context=None):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if url.startswith("base64://"):
            return len("base64://")
        else:
            return 0

__all__ = ("Base64FilesSource",)
