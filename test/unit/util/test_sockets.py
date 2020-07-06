import socket

from galaxy.util import sockets


def test_unused_free_port_unconstrained():
    port = sockets.unused_port()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # would throw exception if port was not free.
    s.bind(('localhost', port))
    s.close()
