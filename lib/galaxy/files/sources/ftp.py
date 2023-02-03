import urllib.parse

try:
    from fs.ftpfs import FTPFS
except ImportError:
    FTPFS = None  # type: ignore[misc,assignment]

from ._pyfilesystem2 import PyFilesystem2FilesSource


class FtpFilesSource(PyFilesystem2FilesSource):
    plugin_type = "ftp"
    required_module = FTPFS
    required_package = "fs.ftpfs"

    def _open_fs(self, user_context, **kwargs):
        props = self._serialization_props(user_context)
        extra_props = kwargs.get("extra_props") or {}
        handle = FTPFS(**{**props, **extra_props})
        return handle

    def _realize_to(self, source_path, native_path, user_context=None, **kwargs):
        extra_props = kwargs.get("extra_props") or {}
        path, kwargs["extra_props"] = self._get_props_and_rel_path(extra_props, source_path)
        super()._realize_to(path, native_path, user_context=user_context, **kwargs)

    def _write_from(self, target_path, native_path, user_context=None, **kwargs):
        extra_props = kwargs.get("extra_props") or {}
        path, kwargs["extra_props"] = self._get_props_and_rel_path(extra_props, target_path)
        super()._write_from(path, native_path, user_context=user_context, **kwargs)

    def _get_props_and_rel_path(self, extra_props, url):
        host = self._props.get("host")
        port = self._props.get("port")
        user = self._props.get("user")
        passwd = self._props.get("passwd")
        rel_path = url
        if url.startswith(f"ftp://{host or ''}"):
            props = self._extract_url_props(url)
            extra_props["host"] = host or props["host"]
            extra_props["port"] = port or props["port"]
            extra_props["user"] = user or props["user"]
            extra_props["passwd"] = passwd or props["passwd"]
            rel_path = props["path"] or url
        return rel_path, extra_props

    def _extract_url_props(self, url):
        result = urllib.parse.urlparse(url)
        return {
            "host": result.hostname,
            "port": result.port or 21,
            "user": result.username,
            "passwd": result.password,
            "path": result.path,
        }

    def score_url_match(self, url: str, **kwargs):
        host = self._props.get("host")
        port = self._props.get("port")
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
