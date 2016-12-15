import random
import shlex
import socket
import subprocess


def unused_port(range=None):
    if range:
        return __unused_port_on_range(range)
    else:
        return __unused_port_rangeless()


def __unused_port_rangeless():
    # TODO: Allow ranges (though then need to guess and check)...
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def __unused_port_on_range(range):
    assert range[0] and range[1]

    # Find all ports that are already occupied
    cmd_netstat = shlex.split("netstat tuln")
    p1 = subprocess.Popen(cmd_netstat, stdout=subprocess.PIPE)

    occupied_ports = set()
    for line in p1.stdout.read().split('\n'):
        if line.startswith('tcp') or line.startswith('tcp6'):
            col = line.split()
            local_address = col[3]
            local_port = local_address.split(':')[1]
            occupied_ports.add( int(local_port) )

    # Generate random free port number.
    while True:
        port = random.randrange(range[0], range[1])
        if port not in occupied_ports:
            break
    return port
