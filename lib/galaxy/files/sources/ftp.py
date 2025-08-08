import urllib.parse
from typing import Union

try:
    from fs.ftpfs import FTPFS
except ImportError:
    FTPFS = None  # type: ignore[misc,assignment]


from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
)
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource


class FTPFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    host: Union[str, TemplateExpansion] = ""
    port: Union[int, TemplateExpansion] = 21
    user: Union[str, TemplateExpansion] = "anonymous"
    passwd: Union[str, TemplateExpansion] = ""
    acct: Union[str, TemplateExpansion] = ""
    timeout: Union[int, TemplateExpansion] = 10
    proxy: Union[str, TemplateExpansion, None] = None
    tls: Union[bool, TemplateExpansion] = False


class FTPFileSourceConfiguration(BaseFileSourceConfiguration):
    host: str = ""
    port: int = 21
    user: str = "anonymous"
    passwd: str = ""
    acct: str = ""
    timeout: int = 10
    proxy: Union[str, None] = None
    tls: bool = False


class FtpFilesSource(PyFilesystem2FilesSource[FTPFileSourceTemplateConfiguration, FTPFileSourceConfiguration]):
    plugin_type = "ftp"
    required_module = FTPFS
    required_package = "fs.ftpfs"

    template_config_class = FTPFileSourceTemplateConfiguration
    resolved_config_class = FTPFileSourceConfiguration

    def _open_fs(self):
        if FTPFS is None:
            raise self.required_package_exception

        return FTPFS(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            passwd=self.config.passwd,
            timeout=self.config.timeout,
            acct=self.config.acct,
            tls=self.config.tls,
            proxy=self.config.proxy,
        )

    def _realize_to(self, source_path: str, native_path: str):
        path = self._parse_url_and_get_path(source_path)
        super()._realize_to(path, native_path)

    def _write_from(self, target_path: str, native_path: str):
        path = self._parse_url_and_get_path(target_path)
        super()._write_from(path, native_path)

    def _parse_url_and_get_path(self, url: str) -> str:
        host = self.config.host
        port = self.config.port
        user = self.config.user
        passwd = self.config.passwd
        rel_path = url
        if url.startswith(f"ftp://{host or ''}"):
            props = self._extract_url_props(url)
            self.config.host = host or props["host"]
            self.config.port = port or props["port"]
            self.config.user = user or props["user"]
            self.config.passwd = passwd or props["passwd"]
            rel_path = props["path"] or url
        return rel_path

    def _extract_url_props(self, url: str):
        result = urllib.parse.urlparse(url)
        return {
            "host": result.hostname,
            "port": result.port or 21,
            "user": result.username,
            "passwd": result.password,
            "path": result.path,
        }

    def score_url_match(self, url: str):
        # We need to use template_config here because this is called before the template is expanded.
        host = self.template_config.host
        port = self.template_config.port
        if host and port and url.startswith(f"ftp://{host}:{port}"):
            return len(f"ftp://{host}:{port}")
        # For security, we need to ensure that a partial match doesn't work e.g. ftp://{host}something/myfiles
        elif host and (url.startswith(f"ftp://{host}/") or url == f"ftp://{host}"):
            return len(f"ftp://{host}")
        elif not host and url.startswith("ftp://"):
            return len("ftp://")
        else:
            return super().score_url_match(url)


__all__ = ("FtpFilesSource",)
