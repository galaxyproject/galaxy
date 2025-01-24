import ipaddress
from typing import (
    List,
    Union,
)

from galaxy.util import unicodify

IpAddressT = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IpNetworkT = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
IpAllowedListEntryT = Union[IpAddressT, IpNetworkT]


def parse_allowlist_ips(fetch_url_allowlist: List[str]) -> List[IpAllowedListEntryT]:
    return [
        (
            ipaddress.ip_network(unicodify(ip.strip()))  # If it has a slash, assume 127.0.0.1/24 notation
            if "/" in ip
            else ipaddress.ip_address(unicodify(ip.strip()))
        )  # Otherwise interpret it as an ip address.
        for ip in fetch_url_allowlist
        if len(ip.strip()) > 0
    ]
