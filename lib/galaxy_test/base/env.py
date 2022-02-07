"""Base utilities for working Galaxy test environments.
"""
import fcntl
import os
import socket
import struct
from typing import (
    Optional,
    Tuple,
)

DEFAULT_WEB_HOST = socket.gethostbyname("localhost")


def setup_keep_outdir() -> str:
    keep_outdir = os.environ.get("GALAXY_TEST_SAVE", "")
    if keep_outdir > "":
        try:
            os.makedirs(keep_outdir)
        except Exception:
            pass
    return keep_outdir


def target_url_parts() -> Tuple[str, Optional[str], str]:
    host = socket.gethostbyname(os.environ.get("GALAXY_TEST_HOST", DEFAULT_WEB_HOST))
    port = os.environ.get("GALAXY_TEST_PORT")
    if port:
        default_url = f"http://{host}:{port}"
    else:
        default_url = f"http://{host}"
    url = os.environ.get("GALAXY_TEST_EXTERNAL", default_url)
    return host, port, url


def get_ip_address(ifname: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(
        fcntl.ioctl(s.fileno(), 0x8915, struct.pack("256s", ifname[:15].encode("utf-8")))[20:24]  # SIOCGIFADDR
    )
