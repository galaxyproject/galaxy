import ipaddress
import logging
import os
import socket
import tempfile
import urllib.request
from typing import Optional
from urllib.parse import (
    unquote,
    urlparse,
)

import requests

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
)
from galaxy.util import (
    stream_to_open_named_file,
    unicodify,
)
from galaxy.util.config_parsers import IpAllowedListEntryT

log = logging.getLogger(__name__)

HTTP_SCHEMES = ("http", "https")


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
    dir: Optional[str] = None,
    user_context=None,
    target_path: Optional[str] = None,
    file_source_opts: Optional[FilesSourceOptions] = None,
    metadata_out: Optional[RealizedSourceMetadata] = None,
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


def ensure_file_sources(file_sources: Optional["ConfiguredFileSources"]) -> "ConfiguredFileSources":
    if file_sources is None:
        file_sources = ConfiguredFileSources.from_dict(None, load_stock_plugins=True)
    return file_sources


def stream_to_file(stream, suffix="", prefix="", dir=None, text=False, **kwd):
    """Writes a stream to a temporary file, returns the temporary file's name"""
    fd, temp_name = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=text)
    return stream_to_open_named_file(stream, fd, temp_name, **kwd)


def validate_uri_access(uri: str, is_admin: bool, ip_allowlist: list[IpAllowedListEntryT]) -> None:
    """Perform uniform checks on supplied URIs.

    - Prevent access to local IPs not found in ip_allowlist.
    - Don't allow non-admins to access file:// URIs.
    """
    validate_non_local(uri, ip_allowlist)
    if not is_admin and uri.lstrip().lower().startswith("file://"):
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


def _host_matches_requests(host: str, url: str) -> bool:
    """Check DNS lookup of ``host`` names the host requests would connect to for ``url``."""
    try:
        prepared = requests.PreparedRequest()
        prepared.prepare_url(url, None)
        # getaddrinfo encodes str hosts with Python's idna (IDNA 2003) codec.
        return host.encode("idna").decode("ascii").lower() == urlparse(prepared.url).hostname
    except ValueError:
        return False


def validate_non_local(
    uri: str, ip_allowlist: list[IpAllowedListEntryT], schemes: tuple[str, ...] = HTTP_SCHEMES
) -> str:
    """Check the host of a URL with one of ``schemes`` against ``ip_allowlist``; return other strings unchanged."""
    # If it doesn't look like a URL, ignore it.
    scheme, sep, _ = uri.strip().partition("://")
    scheme = scheme.lower()
    if not sep or scheme not in schemes:
        return uri

    # Strip surrounding whitespace before passing url to urlparse()
    url = uri.strip()
    # Extract hostname component
    try:
        parsed_url = urlparse(url).netloc
    except ValueError:
        raise RequestParameterInvalidException(f"Could not verify url '{url}'.")
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

    # urllib percent-decodes hosts before resolving them; requests (http(s) only) may read some URLs differently.
    if unquote(parsed_url) != parsed_url or (scheme in HTTP_SCHEMES and not _host_matches_requests(parsed_url, url)):
        raise RequestParameterInvalidException(f"Could not verify url '{url}'.")

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


class ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """A urllib redirect handler that runs validate_non_local on each redirect target before following it."""

    def __init__(self, ip_allowlist: list[IpAllowedListEntryT], schemes: tuple[str, ...] = HTTP_SCHEMES):
        self.ip_allowlist = ip_allowlist
        self.schemes = schemes

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme.lower() not in self.schemes:
            raise RequestParameterInvalidException(f"Refusing to follow redirect to unchecked URL scheme '{newurl}'.")
        validate_non_local(newurl, self.ip_allowlist, schemes=self.schemes)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class ValidatingSession(requests.Session):
    """A requests session that runs validate_non_local on each URL before sending it, redirect hops included."""

    def __init__(self, ip_allowlist: list[IpAllowedListEntryT]):
        super().__init__()
        self.ip_allowlist = ip_allowlist

    def send(self, request, **kwargs):
        assert request.url
        validate_non_local(request.url, self.ip_allowlist)
        return super().send(request, **kwargs)
