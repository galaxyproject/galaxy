import logging
import re
from typing import Union

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
)
from galaxy.util.config_templates import TemplateExpansion
from . import (
    BaseFilesSource,
    PluginKind,
)
from .util import fetch_drs_to_file

log = logging.getLogger(__name__)


class DRSFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    # `url_regex` is not templated because it needs to be set at initialization with no RuntimeContext available.
    url_regex: str = r"^drs://"
    force_http: Union[bool, TemplateExpansion] = False
    http_headers: Union[dict[str, str], TemplateExpansion] = {}


class DRSFileSourceConfiguration(BaseFileSourceConfiguration):
    url_regex: str = r"^drs://"
    force_http: bool = False
    http_headers: dict[str, str] = {}


class DRSFilesSource(BaseFilesSource[DRSFileSourceTemplateConfiguration, DRSFileSourceConfiguration]):
    plugin_type = "drs"
    plugin_kind = PluginKind.drs

    template_config_class = DRSFileSourceTemplateConfiguration
    resolved_config_class = DRSFileSourceConfiguration

    def __init__(self, template_config: DRSFileSourceTemplateConfiguration):
        defaults = dict(
            id="_drs",
            label="DRS file",
            doc="DRS file handler",
            writable=False,
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        super().__init__(template_config)
        assert self.template_config.url_regex, "DRSFilesSource requires a url_regex to be set in the configuration"
        self._url_regex = re.compile(self.template_config.url_regex)

    @property
    def _allowlist(self):
        return self._file_sources_config.fetch_url_allowlist

    def _realize_to(self, source_path: str, native_path: str):
        fetch_drs_to_file(
            source_path,
            native_path,
            user_context=self.user_data.context if self.user_data.context else None,
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
