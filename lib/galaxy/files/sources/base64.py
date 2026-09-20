import base64
import logging

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
)
from . import (
    DefaultBaseFilesSource,
    PluginKind,
)

log = logging.getLogger(__name__)


class Base64FilesSource(DefaultBaseFilesSource):
    plugin_type = "base64"
    plugin_kind = PluginKind.stock

    def __init__(self, template_config: BaseFileSourceTemplateConfiguration):
        defaults = dict(
            id="_base64",
            label="Base64 encoded string",
            doc="Base64 string handler",
            writable=False,
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        super().__init__(template_config)

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[BaseFileSourceConfiguration]
    ):
        with open(native_path, "wb") as temp:
            temp.write(base64.b64decode(source_path[len("base64://") :]))
            temp.flush()

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[BaseFileSourceConfiguration]
    ):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if url.startswith("base64://"):
            return len("base64://")
        else:
            return 0


__all__ = ("Base64FilesSource",)
