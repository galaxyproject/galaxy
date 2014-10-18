import socket


def unused_port():
    # TODO: Allow ranges (though then need to guess and check)...
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port
