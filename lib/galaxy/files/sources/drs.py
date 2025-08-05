import logging
import re
from typing import ClassVar

from . import (
    BaseFilesSource,
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
    config_class: ClassVar[type[DRSFileSourceConfiguration]] = DRSFileSourceConfiguration
    config: DRSFileSourceConfiguration

    def __init__(self, config: FilesSourceProperties):
        super().__init__(config)
        overrides = dict(
            id="_drs",
            label="DRS file",
            doc="DRS file handler",
            writable=False,
        )
        self.config = self.config.model_copy(update=overrides)
        assert self.config.url_regex, "DRSFilesSource requires a url_regex to be set in the configuration"
        self._url_regex = re.compile(self.config.url_regex)

    @property
    def _allowlist(self):
        return self._file_sources_config.fetch_url_allowlist

    def _realize_to(self, source_path: str, native_path: str):
        fetch_drs_to_file(
            source_path,
            native_path,
            user_context=self.user_data.context if self.user_data else None,
            fetch_url_allowlist=self._allowlist,
            headers=self.config.http_headers,
            force_http=self.config.force_http,
        )

    def _write_from(self, target_path: str, native_path: str):
        raise NotImplementedError()

    def score_url_match(self, url: str):
        if match := self._url_regex.match(url):
            return match.span()[1]
        else:
            return 0


__all__ = ("DRSFilesSource",)
