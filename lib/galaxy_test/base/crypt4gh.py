"""Crypt4GH test helpers: keys, encryption and a mock compute-side recryptor service.

``MockRecryptorService`` implements the HTTP contract of the compute mode of
``crypt4gh-recryptor-service`` (Service B): compute keypairs are bound to the user
public key they were issued for, expire, and the service records every request so
tests can assert that no request was made.
"""

import base64
import io
import json
import os
import threading
import uuid
from dataclasses import (
    dataclass,
    field,
)
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from typing import Any

from crypt4gh import (
    header as crypt4gh_header,
    lib as crypt4gh_lib,
    sodium,
)

from galaxy.util.crypt4gh import read_crypt4gh_header


@dataclass
class Keypair:
    secret: bytes
    public: bytes

    @property
    def public_pem(self) -> str:
        encoded = base64.b64encode(self.public).decode()
        return f"-----BEGIN CRYPT4GH PUBLIC KEY-----\n{encoded}\n-----END CRYPT4GH PUBLIC KEY-----\n"


def generate_keypair() -> Keypair:
    secret = os.urandom(32)
    return Keypair(secret=secret, public=sodium.derive_pk(secret))


def parse_public_pem(pem: str) -> bytes:
    lines = [line.strip() for line in pem.strip().splitlines() if line.strip()]
    return base64.b64decode("".join(lines[1:-1]))


def encrypt(plaintext: bytes, recipient: bytes, writer: Keypair | None = None) -> bytes:
    writer = writer or generate_keypair()
    output = io.BytesIO()
    crypt4gh_lib.encrypt([(0, writer.secret, recipient)], io.BytesIO(plaintext), output)
    return output.getvalue()


def decrypt(data: bytes, secret: bytes) -> bytes:
    output = io.BytesIO()
    crypt4gh_lib.decrypt([(0, secret, None)], io.BytesIO(data), output)
    return output.getvalue()


def split_header(data: bytes) -> tuple[bytes, bytes]:
    header = read_crypt4gh_header(io.BytesIO(data))
    return header, data[len(header) :]


def recrypt_header(header: bytes, secret: bytes, recipient: bytes) -> bytes:
    """Re-encrypt the packets of ``header`` that ``secret`` opens to ``recipient``.

    Like the recryptor, the opening key is reused as the writer key.
    """
    packets = list(crypt4gh_header.parse(io.BytesIO(header)))
    reencrypted = crypt4gh_header.reencrypt(packets, [(0, secret, None)], [(0, secret, recipient)], trim=True)
    return crypt4gh_header.serialize(reencrypted)


@dataclass
class ComputeKeypair:
    keypair: Keypair
    user_public: bytes
    expires_at: datetime


@dataclass
class MockRecryptorService:
    expiry_margin: timedelta = timedelta(days=1)
    keypairs: dict[str, ComputeKeypair] = field(default_factory=dict)
    requests: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    # Routes answering with an error status, as {route: [status, ...]} consumed in order.
    failures: dict[str, list[int]] = field(default_factory=dict)
    _server: ThreadingHTTPServer | None = None

    def get_compute_key_info(self, user_public: bytes, expires_in: timedelta = timedelta(days=7)) -> str:
        key_ref = f"cnk:{uuid.uuid4().hex}"
        self.keypairs[key_ref] = ComputeKeypair(
            keypair=generate_keypair(),
            user_public=user_public,
            expires_at=datetime.now(timezone.utc) + expires_in,
        )
        return key_ref

    def user_recrypt(self, encrypted: bytes, user: Keypair, key_ref: str) -> dict[str, str]:
        """What the user-side service (Service A) returns for a dataset encrypted to ``user``."""
        compute = self.keypairs[key_ref]
        user_header, _ = split_header(encrypted)
        compute_header = recrypt_header(user_header, user.secret, compute.keypair.public)
        return {
            "crypt4gh_header": base64.b64encode(compute_header).decode(),
            "crypt4gh_compute_keypair_id": key_ref,
            "crypt4gh_compute_keypair_expiration_date": compute.expires_at.isoformat(),
        }

    def handle(self, route: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        self.requests.append((route, payload))
        if self.failures.get(route):
            return self.failures[route].pop(0), {"detail": "injected failure"}
        compute = self.keypairs.get(payload.get("crypt4gh_compute_keypair_id", ""))
        if compute is None:
            return 404, {"detail": "Unknown crypt4gh_compute_keypair_id"}
        if compute.expires_at - datetime.now(timezone.utc) < self.expiry_margin:
            return 410, {"detail": "Expired crypt4gh_compute_keypair_id"}
        if route == "recrypt_header_to_job_key":
            recipient = parse_public_pem(payload["crypt4gh_job_public_key"])
        elif route == "recrypt_header_to_user_key":
            recipient = compute.user_public
        else:
            return 404, {"detail": "Not Found"}
        try:
            header = base64.b64decode(payload["crypt4gh_header"])
            recrypted = recrypt_header(header, compute.keypair.secret, recipient)
        except Exception:
            return 422, {"detail": "Malformed or undecryptable crypt4gh_header"}
        response = {
            "crypt4gh_header": base64.b64encode(recrypted).decode(),
            "crypt4gh_compute_keypair_id": payload["crypt4gh_compute_keypair_id"],
            "crypt4gh_compute_keypair_expiration_date": compute.expires_at.isoformat(),
        }
        if route == "recrypt_header_to_job_key":
            response["crypt4gh_compute_public_key"] = compute.keypair.public_pem
        return 200, response

    def routes_called(self) -> list[str]:
        return [route for route, _ in self.requests]

    @property
    def url(self) -> str:
        assert self._server, "service not started"
        host, port = self._server.server_address[:2]
        if isinstance(host, bytes):
            host = host.decode()
        return f"http://{host}:{port}"

    def start(self) -> "MockRecryptorService":
        service = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                status, body = service.handle(self.path.strip("/"), payload)
                encoded = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
