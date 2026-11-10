import pytest

from galaxy.tool_util.deps.image_references import (
    ContainerAllowlist,
    ImageReference,
    ImageReferenceError,
    parse_image_reference,
)

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


@pytest.mark.parametrize(
    "value, expected",
    [
        ("python:3.13", ImageReference("docker.io", "library/python", tag="3.13")),
        ("docker://python:3.13", ImageReference("docker.io", "library/python", tag="3.13")),
        ("index.docker.io/library/python", ImageReference("docker.io", "library/python")),
        ("registry-1.docker.io/library/python", ImageReference("docker.io", "library/python")),
        ("rocker/tidyverse:4.3.0", ImageReference("docker.io", "rocker/tidyverse", tag="4.3.0")),
        ("Quay.IO/biocontainers/samtools", ImageReference("quay.io", "biocontainers/samtools")),
        ("localhost/x", ImageReference("localhost", "x")),
        ("localhost:5000/x:1", ImageReference("localhost:5000", "x", tag="1")),
        ("quay.io:443/biocontainers/samtools", ImageReference("quay.io", "biocontainers/samtools")),
        ("docker.io:443/busybox", ImageReference("docker.io", "library/busybox")),
        (f"ghcr.io/org/img:1.2@{SHA_A}", ImageReference("ghcr.io", "org/img", tag="1.2", digest=SHA_A)),
    ],
)
def test_parse_image_reference(value, expected):
    assert parse_image_reference(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "foo bar",
        "python\n",
        "Python:3.13",
        "quay.io//x",
        "/cvmfs/singularity.galaxyproject.org/s/a/samtools:1.17",
        "-bad.example.org/x",
        "python:-bad",
        "python:１",
        "python@",
        "python@sha256:abc",
        "oras://ghcr.io/org/img:1",
    ],
)
def test_parse_image_reference_rejects(value):
    with pytest.raises(ImageReferenceError):
        parse_image_reference(value)


DEFAULT = ["quay.io/biocontainers/*"]


@pytest.mark.parametrize(
    "entries, identifier, allowed",
    [
        (DEFAULT, "quay.io/biocontainers/samtools:1.17", True),
        (DEFAULT, f"quay.io/biocontainers/samtools@{SHA_A}", True),
        (DEFAULT, "quay.io/biocontainers/a/b:1", True),
        (DEFAULT, "quay.io.evil.com/biocontainers/samtools:1.17", False),
        (DEFAULT, "quay.io/biocontainers-evil/samtools:1.17", False),
        (DEFAULT, "quay.io/biocontainers", False),
        (DEFAULT, "oras://quay.io/biocontainers/samtools:1.17", False),
        (["quay.io/*"], "quay.io/anyone/x:1", True),
        (["rocker/*"], "rocker/tidyverse:4.3.0", True),
        (["docker.io/library/python"], "python:3.13", True),
        (["python"], "pythonx:3.13", False),
        (["python"], "library/python/sub:3.13", False),
        (["ghcr.io/org/tool:1.2"], "ghcr.io/org/tool:1.2", True),
        (["ghcr.io/org/tool:1.2"], "ghcr.io/org/tool:1.3", False),
        (["ghcr.io/org/tool:1.2"], f"ghcr.io/org/tool:1.2@{SHA_A}", False),
        ([f"ghcr.io/org/tool@{SHA_A}"], f"ghcr.io/org/tool:anything@{SHA_A}", True),
        ([f"ghcr.io/org/tool@{SHA_A}"], f"ghcr.io/org/tool@{SHA_B}", False),
        ([f"ghcr.io/org/tool:1.2@{SHA_A}"], f"ghcr.io/org/tool@{SHA_A}", True),
        (["*"], "anything at all", True),
        ([], "quay.io/biocontainers/samtools:1.17", False),
    ],
)
def test_container_allowlist(entries, identifier, allowed):
    assert (ContainerAllowlist(entries).rejection(identifier) is None) is allowed


@pytest.mark.parametrize(
    "entry",
    ["/*", "quay.io/bio*", "quay.io/biocontainers/*:1.0", "quay.io\n/*", "oras://ghcr.io/org/*", "not an image", 1],
)
def test_container_allowlist_rejects_malformed_entries(entry):
    with pytest.raises(ImageReferenceError):
        ContainerAllowlist([entry])


@pytest.mark.parametrize(
    "entries, denied, identifier, allowed",
    [
        (["quay.io/org/*"], ["quay.io/org/bad"], "quay.io/org/bad:1", False),
        (["quay.io/org/*"], ["quay.io/org/bad"], f"quay.io/org/bad@{SHA_A}", False),
        (["quay.io/org/*"], ["quay.io/org/bad"], "quay.io/org/good:1", True),
        (["*"], ["quay.io/org/bad"], "quay.io:443/org/bad:1", False),
        (["quay.io/org/*"], ["quay.io/org/sub/*"], "quay.io/org/sub/x:1", False),
        (["*"], ["busybox"], "docker.io/library/busybox:1", False),
        (["*"], ["busybox"], "python:3.13", True),
        (["*"], ["busybox"], "oras://ghcr.io/org/img:1", False),
    ],
)
def test_container_allowlist_denied(entries, denied, identifier, allowed):
    assert (ContainerAllowlist(entries, denied).rejection(identifier) is None) is allowed


@pytest.mark.parametrize("entry", ["*", "quay.io/org/bad:1", f"quay.io/org/bad@{SHA_A}", "quay.io/bio*"])
def test_container_allowlist_rejects_malformed_denied_entries(entry):
    with pytest.raises(ImageReferenceError):
        ContainerAllowlist(["*"], [entry])


@pytest.mark.parametrize("entry", ["quay.io", "docker://quay.io", "localhost", "localhost:5000"])
def test_container_allowlist_rejects_registry_as_denied_entry(entry):
    with pytest.raises(ImageReferenceError, match="names a registry"):
        ContainerAllowlist(["*"], [entry])
