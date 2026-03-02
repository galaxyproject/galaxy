import os

from ._util import (
    assert_can_write_and_read_to_conf,
    assert_simple_file_realize,
)
from .conftest import SftpServerInfo


def _ssh_conf(srv: SftpServerInfo, path: str = "/") -> dict:
    return {
        "type": "ssh",
        "id": "test1",
        "writable": True,
        "host": srv.host,
        "port": srv.port,
        "user": srv.user,
        "passwd": srv.passwd,
        "path": path,
    }


def test_ssh_file_source(sftp_server: SftpServerInfo) -> None:
    conf = _ssh_conf(sftp_server)

    # Read: the fixture pre-seeds a file "a" with content "a\n"
    assert_simple_file_realize([conf], recursive=False, contains=False)

    # Write then read back
    assert_can_write_and_read_to_conf(conf)


def test_ssh_file_source_with_path(sftp_server: SftpServerInfo) -> None:
    # Create a subdirectory in the SFTP root and seed it with file "a"
    subdir = os.path.join(sftp_server.root, "data")
    os.makedirs(subdir)
    with open(os.path.join(subdir, "a"), "w") as fh:
        fh.write("a\n")

    # The Galaxy file source path points at /data on the SFTP server,
    # so gxfiles://test1/a maps to /data/a on the server.
    conf = _ssh_conf(sftp_server, path="/data")

    # Read from the subdirectory
    assert_simple_file_realize([conf], recursive=False, contains=False)

    # Write into the subdirectory then read back
    assert_can_write_and_read_to_conf(conf)
