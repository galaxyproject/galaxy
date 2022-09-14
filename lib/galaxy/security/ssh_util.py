import tempfile
from typing import NamedTuple

from Crypto.PublicKey import RSA


class SSHKeys(NamedTuple):
    private_key: bytes
    public_key: bytes
    private_key_file: str
    public_key_file: str


def generate_ssh_keys() -> SSHKeys:
    """Returns a named tuple with private and public key and their paths."""
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key(format="OpenSSH")
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(private_key)
        private_key_file = f.name
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(public_key)
        public_key_file = f.name
    return SSHKeys(private_key, public_key, private_key_file, public_key_file)
