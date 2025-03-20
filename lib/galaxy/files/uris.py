import ipaddress
import logging
import os
import socket
import tempfile
from typing import (
    List,
    Optional,
    Tuple,
)
from urllib.parse import urlparse

from galaxy.exceptions import (
    AdminRequiredException,
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
)
from galaxy.files import (
    ConfiguredFileSources,
    NoMatchingFileSource,
)
from galaxy.files.sources import FilesSourceOptions
from galaxy.util import (
    stream_to_open_named_file,
    unicodify,
)
from galaxy.util.config_parsers import IpAllowedListEntryT

log = logging.getLogger(__name__)


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
) -> str:
    file_sources = ensure_file_sources(file_sources)
    file_source, rel_path = file_sources.get_file_source_path(url)
    if file_source:
        if not target_path:
            with tempfile.NamedTemporaryFile(prefix=prefix, delete=False, dir=dir) as temp:
                target_path = temp.name
        file_source.realize_to(rel_path, target_path, user_context=user_context, opts=file_source_opts)
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


def validate_uri_access(uri: str, is_admin: bool, ip_allowlist: List[IpAllowedListEntryT]) -> None:
    """Perform uniform checks on supplied URIs.

    - Prevent access to local IPs not found in ip_allowlist.
    - Don't allow non-admins to access file:// URIs.
    """
    validate_non_local(uri, ip_allowlist)
    if not is_admin and uri.lstrip().startswith("file://"):
        raise AdminRequiredException()


def split_port(parsed_url: str, url: str) -> Tuple[str, int]:
    try:
        idx = parsed_url.rindex(":")
        # We parse as an int and let this fail ungracefully if parsing
        # fails because we desire to fail closed rather than open.
        port = int(parsed_url[idx + 1 :])
        parsed_url = parsed_url[:idx]
        return (parsed_url, port)
    except Exception:
        raise RequestParameterInvalidException(f"Could not verify url '{url}'.")


def validate_non_local(uri: str, ip_allowlist: List[IpAllowedListEntryT]) -> str:
    # If it doesn't look like a URL, ignore it.
    if not (uri.lstrip().startswith("http://") or uri.lstrip().startswith("https://")):
        return uri

    # Strip leading whitespace before passing url to urlparse()
    url = uri.lstrip()
    # Extract hostname component
    parsed_url = urlparse(url).netloc
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
    except socket.gaierror as e:
        log.debug("Could not resolve url '%': %'", url, e)
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
