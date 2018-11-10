import collections
import tempfile

from Crypto.PublicKey import RSA


def generate_ssh_keys():
    """Returns a named tuple with private and public key and their paths."""
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key(format='OpenSSH')
    ssh_keys = collections.namedtuple('SSHKeys', 'private_key public_key private_key_file public_key_file')
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(private_key)
        private_key_file = f.name
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(public_key)
        public_key_file = f.name
    return ssh_keys(private_key, public_key, private_key_file, public_key_file)
