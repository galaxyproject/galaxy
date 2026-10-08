import ipaddress
import logging
import os
import posixpath
import socket
import tempfile
import threading
import uuid
from collections.abc import (
    Iterable,
    Iterator,
)
from contextlib import contextmanager
from typing import Optional
from urllib.error import HTTPError
from urllib.parse import urlparse

import requests
from requests import HTTPError as RequestsHTTPError

from galaxy.exceptions import (
    AdminRequiredException,
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
)
from galaxy.files import (
    ConfiguredFileSources,
    NoMatchingFileSource,
)
from galaxy.files.models import (
    FilesSourceOptions,
    RealizedSourceMetadata,
    RemoteFile,
)
from galaxy.util import (
    stream_to_path,
    unicodify,
)
from galaxy.util.config_parsers import IpAllowedListEntryT

log = logging.getLogger(__name__)

# Concurrent requests used to fetch the files of a directory.
DIRECTORY_FETCH_WORKERS = 8

_thread_http_session = threading.local()


@contextmanager
def reuse_http_connections() -> Iterator[None]:
    """Reuse one HTTP session, and so its connections, for the downloads made by this thread in the block.

    The session is closed when the block ends, so it is never shared between users.
    """
    with requests.Session() as session:
        _thread_http_session.session = session
        try:
            yield
        finally:
            _thread_http_session.session = None


def get_reusable_http_session() -> requests.Session | None:
    """Return the session set by :func:`reuse_http_connections` for this thread, if any."""
    return getattr(_thread_http_session, "session", None)


def stream_url_to_str(
    path: str, file_sources: Optional["ConfiguredFileSources"] = None, prefix: str = "gx_file_stream"
) -> str:
    tmp_file = stream_url_to_file(path, file_sources=file_sources, prefix=prefix)
    try:
        with open(tmp_file) as f:
            return f.read()
    finally:
        os.remove(tmp_file)


def stream_url_to_file(
    url: str,
    file_sources: Optional["ConfiguredFileSources"] = None,
    prefix: str = "gx_file_stream",
    dir: str | None = None,
    user_context=None,
    target_path: str | None = None,
    file_source_opts: FilesSourceOptions | None = None,
    metadata_out: RealizedSourceMetadata | None = None,
) -> str:
    """Stream ``url`` to a local path and return that path.

    ``metadata_out``, if supplied, is populated by file sources that can report metadata
    about the source they realized. Only the DRS file source does so today, setting a
    ``name`` key from the DRS object's own name.
    """
    file_sources = ensure_file_sources(file_sources)
    file_source, rel_path = file_sources.get_file_source_path(url)
    if file_source:
        if not target_path:
            with tempfile.NamedTemporaryFile(prefix=prefix, delete=False, dir=dir) as temp:
                target_path = temp.name
        file_source.realize_to(
            rel_path, target_path, user_context=user_context, opts=file_source_opts, metadata_out=metadata_out
        )
        return target_path
    else:
        raise NoMatchingFileSource(f"Could not find a matching handler for: {url}")


def _listing_may_be_truncated(file_source, entries) -> bool:
    """Whether ``entries`` may be cut short; fsspec file sources cap listings meant for browsing."""
    try:
        from galaxy.files.sources._fsspec import (
            FsspecFilesSource,
            MAX_ITEMS_LIMIT,
        )
    except ImportError:  # fsspec is an optional dependency
        return False
    return isinstance(file_source, FsspecFilesSource) and len(entries) >= MAX_ITEMS_LIMIT


def _http_status(error: HTTPError | RequestsHTTPError) -> int | None:
    if isinstance(error, HTTPError):
        return error.code
    return error.response.status_code if error.response is not None else None


class UriDirectoryReader:
    """Read the files under a directory URI through Galaxy's file sources.

    Each file is fetched through the file source matching its URI, so the usual
    access checks (e.g. the URL allowlist) apply to every request.
    """

    def __init__(
        self,
        uri: str,
        file_sources: Optional["ConfiguredFileSources"] = None,
        user_context=None,
    ):
        if "?" in uri or "#" in uri:
            raise RequestParameterInvalidException(
                f"Cannot read a directory from a URI with a query string or fragment [{uri}]"
            )
        self._uri = uri.rstrip("/")
        self._file_sources = ensure_file_sources(file_sources)
        self._user_context = user_context

    def list_files(self) -> list[str] | None:
        """Return the paths of all files under the directory, or ``None`` if they cannot all be listed."""
        file_source, root_path = self._file_sources.get_file_source_path(self._uri)
        if not file_source.get_browsable():
            return None
        try:
            entries, _ = file_source.list(root_path, recursive=True, user_context=self._user_context)
        except Exception as e:
            # e.g. a public bucket that allows reading objects but not listing them.
            log.warning("Could not list directory [%s]: %s", self._uri, unicodify(e))
            return None
        if _listing_may_be_truncated(file_source, entries):
            log.warning("Listing of directory [%s] may be incomplete, it reached the file source limit", self._uri)
            return None
        # File sources differ on leading slashes, so compare both as absolute paths.
        root = f"/{root_path.strip('/')}"
        return [
            posixpath.relpath(f"/{entry.path.lstrip('/')}", root) for entry in entries if isinstance(entry, RemoteFile)
        ]

    def missing_file_statuses(self) -> tuple[int, ...]:
        """Return the HTTP statuses this directory's server uses for files that do not exist.

        A file that cannot exist is requested once: public S3 buckets that do not allow
        listing answer 403 instead of 404, and only then is 403 taken to mean missing.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                self.fetch(f".galaxy-missing-file-probe-{uuid.uuid4().hex}", os.path.join(temp_dir, "probe"))
            except (HTTPError, RequestsHTTPError) as e:
                if _http_status(e) == 403:
                    return (403, 404)
                raise
        return (404,)

    def fetch(self, rel_path: str, target_path: str, missing_statuses: tuple[int, ...] = (404,)) -> bool:
        """Write the file at ``rel_path`` to ``target_path``; return ``False`` if it does not exist.

        ``missing_statuses`` are the HTTP statuses that mean the file does not exist.
        """
        try:
            stream_url_to_file(
                f"{self._uri}/{rel_path}",
                file_sources=self._file_sources,
                user_context=self._user_context,
                target_path=target_path,
            )
        except FileNotFoundError:
            return False
        except (HTTPError, RequestsHTTPError) as e:
            if _http_status(e) in missing_statuses:
                return False
            raise
        return True

    def fetch_all(
        self,
        files: Iterable[tuple[str, str]],
        missing_statuses: tuple[int, ...] = (404,),
        workers: int = DIRECTORY_FETCH_WORKERS,
    ) -> list[str]:
        """Fetch ``(rel_path, target_path)`` pairs concurrently; return the ``rel_path`` of files that do not exist.

        ``files`` is consumed lazily, and each worker reuses its HTTP connections. The first
        error stops all workers and is raised.
        """
        pending = iter(files)
        lock = threading.Lock()
        missing: list[str] = []
        errors: list[Exception] = []

        def work() -> None:
            with reuse_http_connections():
                while True:
                    with lock:
                        if errors:
                            return
                        try:
                            item = next(pending, None)
                        except Exception as e:
                            errors.append(e)
                            return
                    if item is None:
                        return
                    try:
                        found = self.fetch(item[0], item[1], missing_statuses)
                    except Exception as e:
                        with lock:
                            errors.append(e)
                        return
                    if not found:
                        with lock:
                            missing.append(item[0])

        threads = [threading.Thread(target=work, daemon=True) for _ in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if errors:
            raise errors[0]
        return missing


def ensure_file_sources(file_sources: Optional["ConfiguredFileSources"]) -> "ConfiguredFileSources":
    if file_sources is None:
        file_sources = ConfiguredFileSources.from_dict(None, load_stock_plugins=True)
    return file_sources


def stream_to_file(stream, suffix="", prefix="", dir=None, text=False, **kwd):
    """Writes a stream to a temporary file, returns the temporary file's name"""
    fd, temp_name = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=text)
    os.close(fd)
    return stream_to_path(stream, temp_name, **kwd)


def validate_uri_access(uri: str, is_admin: bool, ip_allowlist: list[IpAllowedListEntryT]) -> None:
    """Perform uniform checks on supplied URIs.

    - Prevent access to local IPs not found in ip_allowlist.
    - Don't allow non-admins to access file:// URIs.
    """
    validate_non_local(uri, ip_allowlist)
    if not is_admin and uri.lstrip().startswith("file://"):
        raise AdminRequiredException()


def split_port(parsed_url: str, url: str) -> tuple[str, int]:
    try:
        idx = parsed_url.rindex(":")
        # We parse as an int and let this fail ungracefully if parsing
        # fails because we desire to fail closed rather than open.
        port = int(parsed_url[idx + 1 :])
        parsed_url = parsed_url[:idx]
        return (parsed_url, port)
    except Exception:
        raise RequestParameterInvalidException(f"Could not verify url '{url}'.")


def validate_non_local(uri: str, ip_allowlist: list[IpAllowedListEntryT]) -> str:
    # If it doesn't look like a URL, ignore it.
    if not (uri.strip().startswith("http://") or uri.strip().startswith("https://")):
        return uri

    # Strip surrounding whitespace before passing url to urlparse()
    url = uri.strip()
    # Extract hostname component
    parsed_url = urlparse(url).netloc
    if not parsed_url:
        raise RequestParameterInvalidException(f"Could not verify url '{url}'.")
    # If credentials are in this URL, we need to strip those.
    if parsed_url.count("@") > 0:
        # credentials.
        parsed_url = parsed_url[parsed_url.rindex("@") + 1 :]
    # Percent encoded colons and other characters will not be resolved as such
    # so we don't have to either.

    # Sometimes the netloc will contain the port which is not desired, so we
    # need to extract that.
    port = None
    # However, it could ALSO be an IPv6 address they've supplied.
    if ":" in parsed_url:
        # IPv6 addresses have colons in them already (it seems like always more than two)
        if parsed_url.count(":") >= 2:
            # Since IPv6 already use colons extensively, they wrap it in
            # brackets when there is a port, e.g. http://[2001:db8:1f70::999:de8:7648:6e8]:100/
            # However if it ends with a ']' then there is no port after it and
            # they've wrapped it in brackets just for fun.
            if "]" in parsed_url and not parsed_url.endswith("]"):
                parsed_url, port = split_port(parsed_url=parsed_url, url=url)
            else:
                # Plain ipv6 without port
                pass
        else:
            # This should finally be ipv4 with port. It cannot be IPv6 as that
            # was caught by earlier cases, and it cannot be due to credentials.
            parsed_url, port = split_port(parsed_url=parsed_url, url=url)

    # safe to log out, no credentials/request path, just an IP + port
    log.debug("parsed url %s, port:  %s", parsed_url, port)
    # Call getaddrinfo to resolve hostname into tuples containing IPs.
    try:
        addrinfo = socket.getaddrinfo(parsed_url, port)
    except (socket.gaierror, UnicodeError) as e:
        # UnicodeError covers idna codec failures (e.g. empty DNS labels in hosts like '...' or '..example.com')
        # which are not wrapped as socket.gaierror.
        log.debug("Could not resolve url '%s': '%s'", url, e)
        raise RequestParameterInvalidException(f"Could not verify url '{url}'.")
    # Get the IP addresses that this entry resolves to (uniquely)
    # We drop:
    #   AF_* family: It will resolve to AF_INET or AF_INET6, getaddrinfo(3) doesn't even mention AF_UNIX,
    #   socktype: We don't care if a stream/dgram/raw protocol
    #   protocol: we don't care if it is tcp or udp.
    addrinfo_results = {info[4][0] for info in addrinfo}
    # There may be multiple (e.g. IPv4 + IPv6 or DNS round robin). Any one of these
    # could resolve to a local addresses (and could be returned by chance),
    # therefore we must check them all.
    for raw_ip in addrinfo_results:
        # Convert to an IP object so we can tell if it is in private space.
        ip = ipaddress.ip_address(unicodify(raw_ip))
        # If this is a private address
        if ip.is_private:
            results = []
            # If this IP is not anywhere in the allowlist
            for allowlisted in ip_allowlist:
                # If it's an IP address range (rather than a single one...)
                if isinstance(allowlisted, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                    results.append(ip in allowlisted)
                else:
                    results.append(ip == allowlisted)

            if any(results):
                # If we had any True, then THIS (and ONLY THIS) IP address that
                # that specific DNS entry resolved to is in allowlisted and
                # safe to access. But we cannot exit here, we must ensure that
                # all IPs that that DNS entry resolves to are likewise safe.
                pass
            else:
                # Otherwise, we deny access.
                raise ConfigDoesNotAllowException("Access to this address in not permitted by server configuration")
    return url
