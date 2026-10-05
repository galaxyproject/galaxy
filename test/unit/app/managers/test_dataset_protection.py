import base64
import struct
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.managers.dataset_protection import Crypt4GHProtectionScheme
from galaxy.schema.dataset_protection import Crypt4GHGrantPayload


def _header(*packets: bytes) -> bytes:
    header = struct.pack("<8sII", b"crypt4gh", 1, len(packets))
    for packet in packets:
        header += struct.pack("<I", len(packet) + 4) + packet
    return header


def _payload(**overrides) -> Crypt4GHGrantPayload:
    values = {
        "scheme": "crypt4gh",
        "crypt4gh_compute_header": base64.b64encode(_header(b"compute packet")).decode(),
        "crypt4gh_compute_keypair_id": "cnk:0123456789abcdef",
        "crypt4gh_compute_keypair_expiration_date": datetime.now(timezone.utc) + timedelta(days=6),
    }
    values.update(overrides)
    return Crypt4GHGrantPayload(**values)


def test_valid_grant_is_stored_as_naive_utc():
    expiration = datetime.now(timezone(timedelta(hours=2))) + timedelta(days=6)
    record = Crypt4GHProtectionScheme().validate_user_grant(
        _payload(crypt4gh_compute_keypair_expiration_date=expiration)
    )
    assert record.key_ref == "cnk:0123456789abcdef"
    assert record.expires_at.tzinfo is None
    assert record.expires_at == expiration.astimezone(timezone.utc).replace(tzinfo=None)
    assert base64.b64decode(record.grant_data["compute_header"]) == _header(b"compute packet")


@pytest.mark.parametrize(
    "overrides",
    [
        {"crypt4gh_compute_header": "not base64!"},
        {"crypt4gh_compute_header": base64.b64encode(b"not a header").decode()},
        {"crypt4gh_compute_header": base64.b64encode(_header(b"packet") + b"trailing body").decode()},
        {"crypt4gh_compute_keypair_expiration_date": datetime.now() + timedelta(days=6)},
        {"crypt4gh_compute_keypair_expiration_date": datetime.now(timezone.utc) - timedelta(minutes=1)},
        {"crypt4gh_compute_keypair_expiration_date": datetime.now(timezone.utc) + timedelta(days=60)},
    ],
)
def test_invalid_grants_are_rejected(overrides):
    with pytest.raises(RequestParameterInvalidException):
        Crypt4GHProtectionScheme().validate_user_grant(_payload(**overrides))
