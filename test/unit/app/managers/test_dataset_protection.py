import base64
import hashlib
import json
import os
import struct
import uuid
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import cast
from unittest import mock

import pytest
from sqlalchemy.exc import IntegrityError

from galaxy.config import GalaxyAppConfiguration
from galaxy.datatypes.crypt4gh import Crypt4GH
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.job_execution.protection.outputs import SIDECAR_FILE
from galaxy.job_execution.protection.stage import CLEANUP_FAILURE_FILE
from galaxy.managers.dataset_protection import (
    _extra_files_expire,
    Crypt4GHProtectionScheme,
    DatasetProtectionManager,
)
from galaxy.model import (
    DatasetInstance,
    DatasetProtectionGrant,
    User,
)
from galaxy.schema.dataset_protection import Crypt4GHGrantPayload
from galaxy.util.bunch import Bunch


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


class _FakeDataset:
    def __init__(self, path, size=1):
        self.uuid = uuid.uuid4()
        self.id = 1
        self.path = path
        self.purged = False
        self.state = "ok"
        self.file_size = size

    def get_file_name(self, sync_cache=True):
        return self.path

    def full_delete(self):
        self.purged = True


class _FakeOutput:
    def __init__(self, path, extension="fastqsanger.c4gh", header=None):
        self.id = 1
        self.name = "output"
        self.extension = extension
        self.dataset = _FakeDataset(path)
        self.datatype = Crypt4GH()
        self.metadata = Bunch(crypt4gh_header=base64.b64encode(header).decode() if header else None)
        self.state = "ok"
        self.purged = False
        self.deleted = False


def _manager():
    manager = DatasetProtectionManager(cast(GalaxyAppConfiguration, Bunch(crypt4gh_enabled=True)), mock.MagicMock())
    manager.get_grant = mock.MagicMock(return_value=None)  # type: ignore[method-assign]
    return manager


def _job(*outputs):
    return Bunch(
        id=5,
        user=Bunch(id=1),
        output_datasets=[Bunch(dataset=output) for output in outputs],
        output_library_datasets=[],
        output_dataset_collection_instances=[],
        output_dataset_collections=[],
    )


def _write_sidecar(job_directory, datasets, errors=()):
    path = os.path.join(job_directory, SIDECAR_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    expiration = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    with open(path, "w") as f:
        json.dump({"key_ref": "cnk:1", "key_expiration": expiration, "datasets": datasets, "errors": list(errors)}, f)


def _protected_output(tmp_path, name="out.dat"):
    header = _header(b"sealed to the user")
    path = tmp_path / name
    path.write_bytes(header + b"encrypted body")
    output = _FakeOutput(str(path), header=header)
    record = {
        "outcome": "protected",
        "ext": output.extension,
        "header_sha256": hashlib.sha256(header).hexdigest(),
        "compute_header": "compute",
        "extra_files": {},
    }
    return output, record


def test_finish_job_records_grants_for_protected_outputs(tmp_path):
    output, record = _protected_output(tmp_path)
    _write_sidecar(str(tmp_path), {str(output.dataset.uuid): record})
    manager = _manager()
    with mock.patch("galaxy.managers.dataset_protection.DatasetProtectionGrant", Bunch):
        assert manager.finish_job(_job(output), str(tmp_path)) is None
    grant = manager.sa_session.add.call_args.args[0]
    assert grant.dataset is output.dataset
    assert grant.grant_data == {"compute_header": "compute", "extra_files": {}}
    assert grant.source == "job:5"
    assert not output.dataset.purged


def test_finish_job_without_sidecar_purges_outputs(tmp_path):
    output, _ = _protected_output(tmp_path)
    error = _manager().finish_job(_job(output), str(tmp_path))
    assert error and "could not be verified" in error
    assert output.dataset.purged


def test_finish_job_purges_outputs_missing_from_sidecar(tmp_path):
    protected, record = _protected_output(tmp_path)
    bypassed, _ = _protected_output(tmp_path, "bypassed.dat")
    _write_sidecar(str(tmp_path), {str(protected.dataset.uuid): record})
    error = _manager().finish_job(_job(protected, bypassed), str(tmp_path))
    assert error
    assert bypassed.dataset.purged
    assert not protected.dataset.purged


def test_finish_job_detects_plaintext_behind_a_record(tmp_path):
    output, record = _protected_output(tmp_path)
    # The file stored for the output is not the one that was protected.
    (tmp_path / "out.dat").write_bytes(b"@read1\nACGT\n")
    _write_sidecar(str(tmp_path), {str(output.dataset.uuid): record})
    assert _manager().finish_job(_job(output), str(tmp_path))
    assert output.dataset.purged


def test_finish_job_detects_unprotected_datatype(tmp_path):
    output, record = _protected_output(tmp_path)
    output.extension = "fastqsanger"
    _write_sidecar(str(tmp_path), {str(output.dataset.uuid): record})
    assert _manager().finish_job(_job(output), str(tmp_path))
    assert output.dataset.purged


def test_finish_job_accepts_outputs_without_content(tmp_path):
    output = _FakeOutput(str(tmp_path / "missing.dat"))
    output.dataset.purged = True
    _write_sidecar(str(tmp_path), {str(output.dataset.uuid): {"outcome": "purged"}})
    assert _manager().finish_job(_job(output), str(tmp_path)) is None


def test_finish_job_fails_on_cleanup_failure_without_purging(tmp_path):
    output, record = _protected_output(tmp_path)
    _write_sidecar(str(tmp_path), {str(output.dataset.uuid): record})
    cleanup_failure = tmp_path / CLEANUP_FAILURE_FILE
    cleanup_failure.write_text("Could not remove the decrypted data of this job: boom")
    error = _manager().finish_job(_job(output), str(tmp_path))
    assert error and "boom" in error
    assert not output.dataset.purged


def test_renewing_a_grant_keeps_extra_files_of_job_outputs(tmp_path):
    manager = _manager()
    job_expiration = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=3)
    grant = DatasetProtectionGrant(
        key_ref="cnk:job",
        expires_at=job_expiration,
        grant_data={"compute_header": "job header", "extra_files": {"part.txt": "extra header"}},
    )
    manager.get_grant = mock.MagicMock(return_value=grant)
    output = _FakeOutput(str(tmp_path / "output.dat"))

    manager.register_user_grant(cast(User, Bunch(id=1)), cast(DatasetInstance, output), _payload())

    assert grant.key_ref == "cnk:0123456789abcdef"
    assert grant.grant_data["extra_files"] == {"part.txt": "extra header"}
    # Extra files stay encrypted to the job's compute keypair, the user only authorized the primary file again.
    assert grant.grant_data["extra_files_key"] == {"key_ref": "cnk:job", "expires_at": job_expiration.isoformat()}
    assert not _extra_files_expire(grant, timedelta(days=1))
    assert _extra_files_expire(grant, timedelta(days=4))


def test_concurrent_authorizations_replace_the_grant(tmp_path):
    manager = _manager()
    stored = DatasetProtectionGrant(key_ref="cnk:other-tab", expires_at=datetime(2099, 1, 1), grant_data={})
    # The other request stored its grant between our lookup and our commit.
    manager.get_grant = mock.MagicMock(side_effect=[None, stored, stored])
    manager.sa_session.commit.side_effect = [IntegrityError("INSERT", {}, Exception("unique")), None]
    output = _FakeOutput(str(tmp_path / "output.dat"))

    with mock.patch("galaxy.managers.dataset_protection.DatasetProtectionGrant", Bunch):
        manager.register_user_grant(cast(User, Bunch(id=1)), cast(DatasetInstance, output), _payload())

    manager.sa_session.rollback.assert_called_once()
    assert stored.key_ref == "cnk:0123456789abcdef"
