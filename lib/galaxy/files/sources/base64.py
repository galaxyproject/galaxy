import base64
import logging
from typing import Optional

from typing_extensions import Unpack

from galaxy.files import OptionalUserContext
from . import (
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
    PluginKind,
)

log = logging.getLogger(__name__)


class Base64FilesSource(BaseFilesSource):
    plugin_type = "base64"
    plugin_kind = PluginKind.stock

    def __init__(self, **kwd: Unpack[FilesSourceProperties]):
        kwds: FilesSourceProperties = dict(
            id="_base64",
            label="Base64 encoded string",
            doc="Base64 string handler",
            writable=False,
        )
        kwds.update(kwd)
        props = self._parse_common_config_opts(kwds)
        self._props = props

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        with open(native_path, "wb") as temp:
            temp.write(base64.b64decode(source_path[len("base64://") :]))
            temp.flush()

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> str:
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if url.startswith("base64://"):
            return len("base64://")
        else:
            return 0

    def _serialization_props(self, user_context: OptionalUserContext = None):
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return effective_props


__all__ = ("Base64FilesSource",)
