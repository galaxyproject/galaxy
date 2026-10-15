import pytest

from galaxy_test.driver.driver_util import (
    attempt_port,
    attempt_ports,
    reserve_port,
)


def test_attempt_ports():
    port = int(attempt_ports())
    assert port >= 8000 and port <= 10000


def test_reserved_port_stays_taken_until_closed():
    sock = reserve_port("127.0.0.1")
    port = sock.getsockname()[1]
    try:
        assert attempt_port(port) is None
    finally:
        sock.close()
    assert attempt_port(port) == port


def test_reserved_port_cannot_be_reserved_twice():
    sock = reserve_port("127.0.0.1")
    port = sock.getsockname()[1]
    try:
        with pytest.raises(Exception, match="bound to specified test server port"):
            reserve_port("127.0.0.1", str(port))
    finally:
        sock.close()
