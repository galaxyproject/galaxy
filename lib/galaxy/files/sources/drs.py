import logging
import re
from typing import Optional

from galaxy.files import OptionalUserContext
from . import (
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
    PluginKind,
)
from .util import fetch_drs_to_file

log = logging.getLogger(__name__)


class DRSFileSourceConfiguration(FilesSourceProperties):
    url_regex: str = r"^drs://"
    force_http: bool = False
    http_headers: dict[str, str] = {}


class DRSFilesSource(BaseFilesSource):
    plugin_type = "drs"
    plugin_kind = PluginKind.drs
    config_class = DRSFileSourceConfiguration
    config: DRSFileSourceConfiguration

    def __init__(self, config: FilesSourceProperties):
        overrides = dict(
            id="_drs",
            label="DRS file",
            doc="DRS file handler",
            writable=False,
        )
        self.config = self.config.model_copy(update=overrides)
        super().__init__(config)
        assert self.config.url_regex, "DRSFilesSource requires a url_regex to be set in the configuration"
        self._url_regex = re.compile(self.config.url_regex)

    @property
    def _allowlist(self):
        return self._file_sources_config.fetch_url_allowlist

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        self.update_config_from_options(opts, user_context)

        fetch_drs_to_file(
            source_path,
            native_path,
            user_context,
            fetch_url_allowlist=self._allowlist,
            headers=self.config.http_headers,
            force_http=self.config.force_http,
        )

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if match := self._url_regex.match(url):
            return match.span()[1]
        else:
            return 0


__all__ = ("DRSFilesSource",)
