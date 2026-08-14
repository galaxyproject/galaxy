"""Mock Service B (recryptor) for Crypt4GH Selenium tests.

A small HTTP server that performs real crypt4gh header re-encryption using the
``crypt4gh`` library.  Galaxy sends reencryption requests to two endpoints:

- ``POST /recrypt_header_to_job_key`` — input staging: re-encrypts the compute
  header for a job's ephemeral public key.
- ``POST /recrypt_header_to_user_key`` — output finalization: re-encrypts the
  compute-encrypted header back for the user's public key.

The server uses ``ThreadingHTTPServer`` because Galaxy sends reencryption
requests in parallel via ``asyncio.gather``.
"""

import json
import logging
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from typing import Any

from .crypt4gh_test_utils import (
    Crypt4ghTestKeys,
    decode_header_b64,
    encode_header_b64,
    format_public_key_pem,
    parse_public_key_pem,
    reencrypt_header,
)

log = logging.getLogger(__name__)


class _RecryptorHandler(BaseHTTPRequestHandler):
    """Request handler for the mock recryptor server."""

    # Set by MockRecryptorServer before serving requests.
    keys: Crypt4ghTestKeys

    def do_POST(self) -> None:
        if self.path == "/recrypt_header_to_job_key":
            self._handle_recrypt_to_job_key()
        elif self.path == "/recrypt_header_to_user_key":
            self._handle_recrypt_to_user_key()
        else:
            self._send_json(404, {"error": "not found"})

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_recrypt_to_job_key(self) -> None:
        """Re-encrypt the compute header for the job's ephemeral public key."""
        try:
            req = self._read_body()
            header_bytes = decode_header_b64(req["crypt4gh_header"])
            job_public_key_pem = req["crypt4gh_job_public_key"]
            job_public_key = parse_public_key_pem(job_public_key_pem)

            # Re-encrypt header: decrypt with compute private key, encrypt for job key
            recrypted = reencrypt_header(
                header_bytes,
                self.keys.compute_private_key,
                [job_public_key],
            )

            response = {
                "crypt4gh_header": encode_header_b64(recrypted),
                "crypt4gh_compute_public_key": format_public_key_pem(self.keys.compute_public_key),
                "crypt4gh_compute_keypair_id": self.keys.compute_keypair_id,
                "crypt4gh_compute_keypair_expiration_date": self.keys.compute_keypair_expiration_date,
            }
            self._send_json(200, response)
        except Exception as exc:
            log.exception("Error in /recrypt_header_to_job_key")
            self._send_json(500, {"error": str(exc)})

    def _handle_recrypt_to_user_key(self) -> None:
        """Re-encrypt the compute-encrypted header back for the user's public key."""
        try:
            req = self._read_body()
            header_bytes = decode_header_b64(req["crypt4gh_header"])

            # Re-encrypt header: decrypt with compute private key, encrypt for user key
            recrypted = reencrypt_header(
                header_bytes,
                self.keys.compute_private_key,
                [self.keys.user_public_key],
            )

            response = {
                "crypt4gh_header": encode_header_b64(recrypted),
            }
            self._send_json(200, response)
        except Exception as exc:
            log.exception("Error in /recrypt_header_to_user_key")
            self._send_json(500, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("Mock recryptor: %s - %s", self.address_string(), format % args)


class MockRecryptorServer:
    """A threaded HTTP server that performs real crypt4gh header re-encryption."""

    def __init__(self, keys: Crypt4ghTestKeys, host: str = "127.0.0.1", port: int = 0) -> None:
        self.keys = keys
        # Attach keys to the handler class so all instances can access them
        _RecryptorHandler.keys = keys
        self._server = ThreadingHTTPServer((host, port), _RecryptorHandler)
        self._server.daemon_threads = True

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        if isinstance(host, bytes):
            host = host.decode("ascii")
        return f"http://{host}:{port}"

    def start(self) -> None:
        # ThreadingHTTPServer.serve_forever in a background thread
        import threading

        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
