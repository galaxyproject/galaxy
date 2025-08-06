try:
    from fs.onedatarestfs import OnedataRESTFS
except ImportError:
    OnedataRESTFS = None


from typing import Union

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
)
from galaxy.util import mapped_chars
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource


def remove_prefix(prefix: str, string: str) -> str:
    if string.startswith(prefix):
        string = string[len(prefix) :]
    return string


class OnedataFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    access_token: Union[str, TemplateExpansion]
    onezone_domain: Union[str, TemplateExpansion]
    disable_tls_certificate_validation: Union[bool, TemplateExpansion] = False


class OnedataFileSourceConfiguration(BaseFileSourceConfiguration):
    access_token: str
    onezone_domain: str
    disable_tls_certificate_validation: bool = False


class OnedataFilesSource(
    PyFilesystem2FilesSource[OnedataFileSourceTemplateConfiguration, OnedataFileSourceConfiguration]
):
    plugin_type = "onedata"
    required_module = OnedataRESTFS
    required_package = "fs.onedatarestfs"

    template_config_class = OnedataFileSourceTemplateConfiguration
    resolved_config_class = OnedataFileSourceConfiguration

    def _open_fs(self):
        if OnedataRESTFS is None:
            raise self.required_package_exception

        onezone_domain = remove_prefix("http://", remove_prefix("https://", self.config.onezone_domain))
        alt_space_fqn_separators = [mapped_chars["@"]] if "@" in mapped_chars else None

        handle = OnedataRESTFS(
            onezone_host=onezone_domain,
            token=self.config.access_token,
            alt_space_fqn_separators=alt_space_fqn_separators,
            verify_ssl=not self.config.disable_tls_certificate_validation,
        )
        return handle


__all__ = ("OnedataFilesSource",)
