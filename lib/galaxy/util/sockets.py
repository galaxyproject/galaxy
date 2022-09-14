import random
import socket
import sys

from galaxy.util import commands


def get_ip():
    if sys.platform == "darwin":
        # If we're on OSX it is likely that the docker host is localhost.
        return socket.gethostbyname(socket.gethostname())
    # This method assumes that the ip with default route is the ip we want to return
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = None
    finally:
        s.close()
    return ip


def unused_port(range=None):
    if range:
        return __unused_port_on_range(range)
    else:
        return __unused_port_rangeless()


def __unused_port_rangeless():
    # TODO: Allow ranges (though then need to guess and check)...
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("localhost", 0))
    addr, port = s.getsockname()
    s.close()
    return port


def __unused_port_on_range(range):
    assert range[0] and range[1]

    # Find all ports that are already occupied
    cmd_netstat = ["netstat", "tuln"]
    stdout = commands.execute(cmd_netstat)

    occupied_ports = set()
    for line in stdout.split("\n"):
        if line.startswith("tcp") or line.startswith("tcp6"):
            col = line.split()
            local_address = col[3]
            local_port = local_address.split(":")[1]
            occupied_ports.add(int(local_port))

    # Generate random free port number.
    while True:
        port = random.randrange(range[0], range[1])
        if port not in occupied_ports:
            break
    return port
