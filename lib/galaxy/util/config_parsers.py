import ipaddress

from galaxy.util import unicodify

IpAddressT = ipaddress.IPv4Address | ipaddress.IPv6Address
IpNetworkT = ipaddress.IPv4Network | ipaddress.IPv6Network
IpAllowedListEntryT = IpAddressT | IpNetworkT


def parse_allowlist_ips(fetch_url_allowlist: list[str]) -> list[IpAllowedListEntryT]:
    return [
        (
            ipaddress.ip_network(unicodify(ip.strip()))  # If it has a slash, assume 127.0.0.1/24 notation
            if "/" in ip
            else ipaddress.ip_address(unicodify(ip.strip()))
        )  # Otherwise interpret it as an ip address.
        for ip in fetch_url_allowlist
        if len(ip.strip()) > 0
    ]
