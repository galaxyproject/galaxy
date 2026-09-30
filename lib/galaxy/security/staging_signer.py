"""Signatures for URLs that let a remote job runner stage a job's files.

A signature binds one transfer: a job, the kind and id of the object being
staged, a path within that object (empty for the object itself) and an expiry.
A URL carrying it authorizes exactly that transfer, so a job holding the URL
cannot alter it to reach any other object.
"""

import hashlib
import hmac
import time

from galaxy.util import smart_str

# Derive the signing key from id_secret with a purpose label, so signatures here
# never coincide with any other use of id_secret.
KEY_PURPOSE = b"galaxy-job-staging-v1"


class StagingUrlSigner:
    def __init__(self, id_secret: str) -> None:
        self._key = hmac.new(smart_str(id_secret), KEY_PURPOSE, hashlib.sha256).digest()

    def sign(self, job_id: int, kind: str, object_id: int, path: str, expires: int) -> str:
        message = f"v1|{job_id}|{kind}|{object_id}|{path}|{expires}"
        return hmac.new(self._key, message.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(
        self,
        job_id: int,
        kind: str,
        object_id: int,
        path: str,
        expires: int,
        signature: str,
        now: float | None = None,
    ) -> bool:
        if (time.time() if now is None else now) >= expires:
            return False
        expected = self.sign(job_id, kind, object_id, path, expires)
        # Compare bytes: compare_digest rejects non-ASCII str, and signatures arrive from URLs.
        return hmac.compare_digest(expected.encode("utf-8"), signature.encode("utf-8"))
