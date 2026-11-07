from dataclasses import (
    dataclass,
    replace,
)

import pytest

from galaxy.security.staging_signer import StagingUrlSigner

SECRET = "0123456789abcdef"


@dataclass(frozen=True)
class Transfer:
    job_id: int = 7
    kind: str = "dataset"
    object_id: int = 42
    path: str = ""
    expires: int = 2_000_000_000

    def sign(self, signer: StagingUrlSigner) -> str:
        return signer.sign(self.job_id, self.kind, self.object_id, self.path, self.expires)

    def verify(self, signer: StagingUrlSigner, signature: str, now: float) -> bool:
        return signer.verify(self.job_id, self.kind, self.object_id, self.path, self.expires, signature, now=now)


SIGNED = Transfer()
BEFORE_EXPIRY = SIGNED.expires - 1


def test_signature_verifies_for_the_signed_transfer():
    signer = StagingUrlSigner(SECRET)
    assert SIGNED.verify(signer, SIGNED.sign(signer), now=BEFORE_EXPIRY)


@pytest.mark.parametrize(
    "altered",
    [
        replace(SIGNED, job_id=8),
        replace(SIGNED, kind="metadata_file"),
        replace(SIGNED, object_id=43),
        replace(SIGNED, path="../dataset_43.dat"),
        replace(SIGNED, expires=SIGNED.expires + 3600),
    ],
)
def test_signature_does_not_verify_for_any_other_transfer(altered):
    signer = StagingUrlSigner(SECRET)
    assert not altered.verify(signer, SIGNED.sign(signer), now=BEFORE_EXPIRY)


def test_signature_does_not_verify_once_expired():
    signer = StagingUrlSigner(SECRET)
    assert not SIGNED.verify(signer, SIGNED.sign(signer), now=SIGNED.expires)


def test_signature_from_another_secret_does_not_verify():
    signature = SIGNED.sign(StagingUrlSigner("another secret"))
    assert not SIGNED.verify(StagingUrlSigner(SECRET), signature, now=BEFORE_EXPIRY)


@pytest.mark.parametrize("signature", ["", "not-hex", "é" * 64])
def test_malformed_signature_does_not_verify(signature):
    assert not SIGNED.verify(StagingUrlSigner(SECRET), signature, now=BEFORE_EXPIRY)
