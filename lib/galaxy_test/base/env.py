"""Base utilities for working Galaxy test environments.
"""
import fcntl
import os
import socket
import struct

DEFAULT_WEB_HOST = socket.gethostbyname('localhost')


def setup_keep_outdir():
    keep_outdir = os.environ.get('GALAXY_TEST_SAVE', '')
    if keep_outdir > '':
        try:
            os.makedirs(keep_outdir)
        except Exception:
            pass
    return keep_outdir


def target_url_parts():
    host = socket.gethostbyname(os.environ.get('GALAXY_TEST_HOST', DEFAULT_WEB_HOST))
    port = os.environ.get('GALAXY_TEST_PORT')
    default_url = "http://{}:{}".format(host, port)
    url = os.environ.get('GALAXY_TEST_EXTERNAL', default_url)
    return host, port, url


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15].encode('utf-8'))
    )[20:24])
