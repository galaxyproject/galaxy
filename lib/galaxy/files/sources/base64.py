import base64
import logging
from typing import Optional

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

    def __init__(self, config: FilesSourceProperties):
        super().__init__(config)
        overrides = dict(
            id="_base64",
            label="Base64 encoded string",
            doc="Base64 string handler",
            writable=False,
        )
        self.config = self.config.model_copy(update=overrides)

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
    ):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if url.startswith("base64://"):
            return len("base64://")
        else:
            return 0


__all__ = ("Base64FilesSource",)
