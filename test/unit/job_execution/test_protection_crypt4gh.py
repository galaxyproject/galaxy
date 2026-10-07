import base64
import hashlib
import json
import logging
import os
import uuid
from datetime import timedelta

import pytest

from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.job_execution.protection import (
    ProtectedFile,
    ProtectedInput,
    ProtectionError,
    ProtectionPlan,
    RecryptorSettings,
    STATE_FILENAME,
)
from galaxy.job_execution.protection.crypt4gh import Crypt4GHJobRuntime
from galaxy.job_execution.protection.outputs import (
    OutputProtector,
    SIDECAR_FILE,
)
from galaxy.job_execution.protection.stage import (
    CLEANUP_FAILURE_FILE,
    PROTECTION_SETUP_FAILURE_FILE,
    run,
    SETUP_FAILURE_FILE,
)
from galaxy.util.bunch import Bunch
from galaxy_test.base.crypt4gh import (
    decrypt,
    encrypt,
    generate_keypair,
    MockRecryptorService,
    split_header,
)

PLAINTEXT = b"@read1\nACGT\n+\nIIII\n" * 1000


@pytest.fixture
def service():
    service = MockRecryptorService().start()
    yield service
    service.stop()


@pytest.fixture
def user():
    return generate_keypair()


def _protected_input(tmp_path, service, user, key_ref, dataset_id=1, plaintext=PLAINTEXT, extra_files=None):
    encrypted = encrypt(plaintext, user.public)
    source = tmp_path / f"dataset_{dataset_id}.dat"
    source.write_bytes(encrypted)
    staged = tmp_path / "job" / "_protected" / "inputs" / str(dataset_id) / "plaintext.fastqsanger"
    protected_extra_files = {}
    source_extra = tmp_path / f"dataset_{dataset_id}_files"
    for relpath, content in (extra_files or {}).items():
        encrypted_extra = encrypt(content, user.public)
        (source_extra / relpath).parent.mkdir(parents=True, exist_ok=True)
        (source_extra / relpath).write_bytes(encrypted_extra)
        protected_extra_files[relpath] = ProtectedFile(
            source_path=str(source_extra / relpath),
            staged_path=str(staged.parent / "plaintext_files" / relpath),
            compute_header=service.user_recrypt(encrypted_extra, user, key_ref)["crypt4gh_header"],
        )
    return ProtectedInput(
        dataset_id=dataset_id,
        key_ref=key_ref,
        primary=ProtectedFile(
            source_path=str(source),
            staged_path=str(staged),
            compute_header=service.user_recrypt(encrypted, user, key_ref)["crypt4gh_header"],
        ),
        staged_extra_files_path=str(staged.parent / "plaintext_files"),
        source_extra_files_path=str(source_extra),
        extra_files=protected_extra_files,
    )


def _plan(tmp_path, service, key_ref, inputs, **recryptor) -> ProtectionPlan:
    (tmp_path / "job").mkdir(exist_ok=True)
    return ProtectionPlan(
        scheme="crypt4gh",
        job_directory=str(tmp_path / "job"),
        output_key_ref=key_ref,
        recryptor=RecryptorSettings(url=service.url, **recryptor),
        inputs=inputs,
    )


def test_stage_inputs_decrypts_with_a_job_key(tmp_path, service, user):
    key_ref = service.get_compute_key_info(user.public)
    inputs = [
        _protected_input(tmp_path, service, user, key_ref, dataset_id=1),
        _protected_input(tmp_path, service, user, key_ref, dataset_id=2, plaintext=b"second input"),
    ]
    plan = _plan(tmp_path, service, key_ref, inputs)

    Crypt4GHJobRuntime(plan).stage_inputs()

    assert open(inputs[0].primary.staged_path, "rb").read() == PLAINTEXT
    assert open(inputs[1].primary.staged_path, "rb").read() == b"second input"
    assert os.stat(inputs[0].primary.staged_path).st_mode & 0o077 == 0
    assert service.routes_called() == ["recrypt_header_to_job_key"] * 2
    # Only headers, never encrypted bodies, are sent to the service.
    for _, payload in service.requests:
        assert len(base64.b64decode(payload["crypt4gh_header"])) < 1024
    state = json.load(open(os.path.join(plan.protected_directory, STATE_FILENAME)))
    assert state["key_ref"] == key_ref
    assert "PUBLIC KEY" in state["compute_public_key"]


def test_stage_inputs_decrypts_extra_files(tmp_path, service, user):
    key_ref = service.get_compute_key_info(user.public)
    protected_input = _protected_input(
        tmp_path, service, user, key_ref, extra_files={"index.html": b"<html/>", "sub/part.txt": b"part"}
    )
    Crypt4GHJobRuntime(_plan(tmp_path, service, key_ref, [protected_input])).stage_inputs()
    staged_extra = protected_input.staged_extra_files_path
    assert open(os.path.join(staged_extra, "index.html"), "rb").read() == b"<html/>"
    assert open(os.path.join(staged_extra, "sub", "part.txt"), "rb").read() == b"part"


def test_extra_files_can_use_another_compute_key(tmp_path, service, user):
    # A renewed grant: the primary file was authorized again, extra files keep the key of the job that wrote them.
    job_key_ref = service.get_compute_key_info(user.public, expires_in=timedelta(days=3))
    protected_input = _protected_input(tmp_path, service, user, job_key_ref, extra_files={"part.txt": b"part"})
    renewed_key_ref = service.get_compute_key_info(user.public)
    encrypted = open(protected_input.primary.source_path, "rb").read()
    protected_input.primary.compute_header = service.user_recrypt(encrypted, user, renewed_key_ref)["crypt4gh_header"]
    protected_input.key_ref = renewed_key_ref
    protected_input.extra_files["part.txt"].key_ref = job_key_ref

    Crypt4GHJobRuntime(_plan(tmp_path, service, renewed_key_ref, [protected_input])).stage_inputs()

    assert open(protected_input.primary.staged_path, "rb").read() == PLAINTEXT
    assert open(os.path.join(protected_input.staged_extra_files_path, "part.txt"), "rb").read() == b"part"
    used_keys = sorted(payload["crypt4gh_compute_keypair_id"] for _, payload in service.requests)
    assert used_keys == sorted([renewed_key_ref, job_key_ref])


def test_missing_tls_files_are_reported_by_setting(tmp_path, service, user):
    key_ref = service.get_compute_key_info(user.public)
    plan = _plan(
        tmp_path,
        service,
        key_ref,
        [_protected_input(tmp_path, service, user, key_ref)],
        ca_cert=str(tmp_path / "missing-ca.pem"),
    )
    with pytest.raises(ProtectionError, match="crypt4gh_recryptor_ca_cert doesn't exist on the compute host"):
        Crypt4GHJobRuntime(plan).stage_inputs()
    assert service.requests == []


def test_stage_command_errors_dont_reveal_the_service_address(tmp_path, service, user, capsys):
    key_ref = service.get_compute_key_info(user.public)
    plan = _plan(tmp_path, service, key_ref, [_protected_input(tmp_path, service, user, key_ref)], retries=0)
    # Nothing listens there.
    plan.recryptor.url = "https://127.0.0.1:9"
    plan_path = str(tmp_path / "plan.json")
    plan.write(plan_path)

    assert run("stage-in", plan_path) == 1

    stderr = capsys.readouterr().err
    assert "Could not reach the key service" in stderr
    assert "127.0.0.1" not in stderr
    assert "Traceback" not in stderr


def test_verbose_errors_show_the_cause(tmp_path, service, user, capsys):
    key_ref = service.get_compute_key_info(user.public)
    plan = _plan(
        tmp_path,
        service,
        key_ref,
        [_protected_input(tmp_path, service, user, key_ref)],
        retries=0,
        verbose_errors=True,
    )
    plan.recryptor.url = "https://127.0.0.1:9"
    plan_path = str(tmp_path / "plan.json")
    plan.write(plan_path)

    assert run("stage-in", plan_path) == 1

    # For administrators setting up a destination: the cause, including the service's address.
    stderr = capsys.readouterr().err
    assert "Could not reach the key service (ConnectionError: " in stderr
    assert "127.0.0.1" in stderr


def test_unlisted_extra_files_are_refused(tmp_path, service, user):
    key_ref = service.get_compute_key_info(user.public)
    protected_input = _protected_input(tmp_path, service, user, key_ref, extra_files={"listed": b"a"})
    with open(os.path.join(protected_input.source_extra_files_path or "", "unlisted"), "wb") as f:
        f.write(b"cannot be decrypted")
    runtime = Crypt4GHJobRuntime(_plan(tmp_path, service, key_ref, [protected_input]))
    with pytest.raises(ProtectionError, match="extra files"):
        runtime.stage_inputs()
    assert service.requests == []


@pytest.mark.parametrize(
    "setup,message",
    [
        ("unknown_key", "does not know the compute key"),
        ("expired_key", "has expired"),
        ("other_users_header", "could not open the header"),
        ("server_error", "HTTP 500"),
    ],
)
def test_stage_inputs_failures_leave_no_plaintext(tmp_path, service, user, setup, message):
    key_ref = service.get_compute_key_info(user.public)
    good_input = _protected_input(tmp_path, service, user, key_ref, dataset_id=1)
    bad_input = _protected_input(tmp_path, service, user, key_ref, dataset_id=2)
    plan_key_ref = key_ref
    if setup == "unknown_key":
        bad_input.key_ref = "cnk:unknown"
    elif setup == "expired_key":
        service.keypairs[key_ref].expires_at -= timedelta(days=6, hours=12)
    elif setup == "other_users_header":
        # A header sealed to another compute key can't be opened with this one.
        other_key_ref = service.get_compute_key_info(generate_keypair().public)
        other = _protected_input(tmp_path, service, user, other_key_ref, dataset_id=3)
        bad_input.primary.compute_header = other.primary.compute_header
    else:
        service.failures["recrypt_header_to_job_key"] = [500] * 10
    plan = _plan(tmp_path, service, plan_key_ref, [good_input, bad_input], retries=1)

    with pytest.raises(ProtectionError, match=message):
        Crypt4GHJobRuntime(plan).stage_inputs()
    assert not os.path.exists(os.path.join(plan.protected_directory, "inputs"))


def test_inputs_can_use_different_compute_keys(tmp_path, service, user):
    # Compute keypairs rotate, datasets authorized a week apart use different ones.
    old_key_ref = service.get_compute_key_info(user.public, expires_in=timedelta(days=2))
    new_key_ref = service.get_compute_key_info(user.public)
    inputs = [
        _protected_input(tmp_path, service, user, old_key_ref, dataset_id=1),
        _protected_input(tmp_path, service, user, new_key_ref, dataset_id=2, plaintext=b"newer"),
    ]
    plan = _plan(tmp_path, service, new_key_ref, inputs)
    Crypt4GHJobRuntime(plan).stage_inputs()
    assert open(inputs[1].primary.staged_path, "rb").read() == b"newer"
    state = json.load(open(os.path.join(plan.protected_directory, STATE_FILENAME)))
    assert state["key_ref"] == new_key_ref
    assert state["compute_public_key"] == service.keypairs[new_key_ref].keypair.public_pem


def test_transient_errors_are_retried(tmp_path, service, user):
    key_ref = service.get_compute_key_info(user.public)
    protected_input = _protected_input(tmp_path, service, user, key_ref)
    service.failures["recrypt_header_to_job_key"] = [503, 502]
    Crypt4GHJobRuntime(_plan(tmp_path, service, key_ref, [protected_input], retries=2)).stage_inputs()
    assert open(protected_input.primary.staged_path, "rb").read() == PLAINTEXT
    assert len(service.requests) == 3


def test_key_material_is_never_logged(tmp_path, service, user, caplog):
    key_ref = service.get_compute_key_info(user.public)
    protected_input = _protected_input(tmp_path, service, user, key_ref)
    with caplog.at_level(logging.DEBUG):
        logging.getLogger().setLevel(logging.DEBUG)
        Crypt4GHJobRuntime(_plan(tmp_path, service, key_ref, [protected_input])).stage_inputs()
    assert not [record for record in caplog.records if record.name.startswith("crypt4gh")]
    assert protected_input.primary.compute_header not in caplog.text


def test_stage_command_reports_failures(tmp_path, service, user):
    key_ref = service.get_compute_key_info(user.public)
    protected_input = _protected_input(tmp_path, service, user, key_ref)
    protected_input.key_ref = "cnk:unknown"
    plan = _plan(tmp_path, service, key_ref, [protected_input])
    plan_path = str(tmp_path / "plan.json")
    plan.write(plan_path)
    assert os.stat(plan_path).st_mode & 0o777 == 0o600

    assert run("stage-in", plan_path) == 1
    with open(os.path.join(plan.job_directory, SETUP_FAILURE_FILE)) as f:
        assert f.read().startswith("Could not decrypt the protected inputs of this job")


def test_stage_command_reports_missing_plan(tmp_path):
    job_directory = tmp_path / "job"
    (job_directory / "configs").mkdir(parents=True)

    assert run("stage-in", str(job_directory / "configs" / "protection_plan.json")) == 1

    for failure_file in (SETUP_FAILURE_FILE, PROTECTION_SETUP_FAILURE_FILE):
        with open(job_directory / failure_file) as f:
            assert f.read().startswith("Could not decrypt the protected inputs of this job")


def test_cleanup_removes_plaintext(tmp_path, service, user):
    key_ref = service.get_compute_key_info(user.public)
    plan = _plan(tmp_path, service, key_ref, [_protected_input(tmp_path, service, user, key_ref)])
    plan_path = str(tmp_path / "plan.json")
    plan.write(plan_path)

    assert run("stage-in", plan_path) == 0
    assert run("cleanup-inputs", plan_path) == 0
    assert not os.path.exists(os.path.join(plan.protected_directory, "inputs"))
    assert os.path.exists(os.path.join(plan.protected_directory, STATE_FILENAME))
    assert run("cleanup", plan_path) == 0
    assert not os.path.exists(plan.protected_directory)
    assert not os.path.exists(os.path.join(plan.job_directory, CLEANUP_FAILURE_FILE))


def _staged_runtime(tmp_path, service, user):
    key_ref = service.get_compute_key_info(user.public)
    plan = _plan(tmp_path, service, key_ref, [_protected_input(tmp_path, service, user, key_ref)])
    runtime = Crypt4GHJobRuntime(plan)
    runtime.stage_inputs()
    service.requests.clear()
    return runtime, key_ref


def test_protect_file_encrypts_for_the_user(tmp_path, service, user):
    runtime, key_ref = _staged_runtime(tmp_path, service, user)
    output = tmp_path / "job" / "outputs" / "dataset.dat"
    output.parent.mkdir()
    output.write_bytes(b"result computed from decrypted data")

    result = runtime.protect_file(str(output))

    encrypted = output.read_bytes()
    assert decrypt(encrypted, user.secret) == b"result computed from decrypted data"
    header, _ = split_header(encrypted)
    assert hashlib.sha256(header).hexdigest() == result.header_sha256
    assert service.routes_called() == ["recrypt_header_to_user_key"]
    # The compute header lets the user's further jobs decrypt the output again.
    compute_header = base64.b64decode(result.compute_header)
    compute = service.keypairs[key_ref].keypair
    assert decrypt(compute_header + encrypted[len(header) :], compute.secret) == b"result computed from decrypted data"
    assert sorted(os.listdir(output.parent)) == ["dataset.dat"]


def test_protect_file_failure_raises(tmp_path, service, user):
    runtime, _ = _staged_runtime(tmp_path, service, user)
    service.failures["recrypt_header_to_user_key"] = [422]
    output = tmp_path / "out.dat"
    output.write_bytes(b"plaintext")
    with pytest.raises(ProtectionError, match="could not open the header"):
        runtime.protect_file(str(output))
    assert not {".out.dat.c4gh", ".out.dat.c4gh-body"} & set(os.listdir(tmp_path))


class _FakeDatasetInstance:
    def __init__(self, extension):
        self.extension = extension
        self.name = "output"
        self.dataset = Bunch(uuid=uuid.uuid4(), purged=False)


@pytest.fixture(scope="module")
def registry():
    return example_datatype_registry_for_sample(crypt4gh_enabled=True)


@pytest.mark.parametrize(
    "extension,content,expected",
    [
        ("txt", b"text\n", "txt.c4gh"),
        ("fastqsanger.c4gh", b"@r\nA\n+\nI\n", "fastqsanger.c4gh"),
        ("auto", b"@r\nACGT\n+\nIIII\n", "fastqsanger.c4gh"),
        ("not_a_datatype", b"x", "c4gh"),
    ],
)
def test_output_protector_wraps_extensions(tmp_path, service, user, registry, extension, content, expected):
    runtime, _ = _staged_runtime(tmp_path, service, user)
    protector = OutputProtector(runtime, registry)
    path = tmp_path / "out.dat"
    path.write_bytes(content)
    dataset_instance = _FakeDatasetInstance(extension)
    protector.protect(dataset_instance, str(path))  # type: ignore[arg-type]
    assert dataset_instance.extension == expected
    assert protector.protected_ext(dataset_instance) == expected  # type: ignore[arg-type]


def test_output_protector_protects_extra_files_and_reports_gaps(tmp_path, service, user, registry):
    runtime, _ = _staged_runtime(tmp_path, service, user)
    protector = OutputProtector(runtime, registry)
    path = tmp_path / "out.dat"
    path.write_bytes(b"<html/>")
    extra_files = tmp_path / "out_files"
    (extra_files / "sub").mkdir(parents=True)
    (extra_files / "sub" / "part.txt").write_bytes(b"part")
    protected = _FakeDatasetInstance("html")
    protector.protect(protected, str(path), str(extra_files))  # type: ignore[arg-type]
    assert decrypt((extra_files / "sub" / "part.txt").read_bytes(), user.secret) == b"part"

    bypassed = _FakeDatasetInstance("txt")
    protector.check_complete([protected, bypassed])  # type: ignore[list-item]
    protector.write_sidecar(str(tmp_path))
    sidecar = json.load(open(tmp_path / SIDECAR_FILE))
    assert sidecar["datasets"][str(protected.dataset.uuid)]["extra_files"].keys() == {"sub/part.txt"}
    assert sidecar["datasets"][str(bypassed.dataset.uuid)] == {"outcome": "failed"}
    assert sidecar["errors"] == ["Output 'output' was not protected."]
    assert os.stat(tmp_path / SIDECAR_FILE).st_mode & 0o777 == 0o600


def test_output_protector_discards_plaintext_on_failure(tmp_path, service, user, registry):
    runtime, _ = _staged_runtime(tmp_path, service, user)
    protector = OutputProtector(runtime, registry)
    service.failures["recrypt_header_to_user_key"] = [422]
    path = tmp_path / "out.dat"
    path.write_bytes(b"plaintext")
    with pytest.raises(ProtectionError):
        protector.protect(_FakeDatasetInstance("txt"), str(path))  # type: ignore[arg-type]
    assert not path.exists()
    assert protector.errors
