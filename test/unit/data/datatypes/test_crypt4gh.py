import base64
import struct
from xml.etree import ElementTree

import pytest

from galaxy.datatypes.crypt4gh import Crypt4GH
from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.datatypes.sniff import (
    FilePrefix,
    guess_ext_from_file_name,
    handle_uploaded_dataset_file_internal,
)
from galaxy.util.bunch import Bunch
from galaxy.util.crypt4gh import (
    check_crypt4gh,
    infer_crypt4gh_file_ext,
    is_crypt4gh_file_ext,
    preserve_crypt4gh_inner_file_ext,
    read_crypt4gh_header,
    unwrap_crypt4gh_file_ext,
    wrap_crypt4gh_file_ext,
)


def _crypt4gh_bytes(packets=(b"packet-one", b"packet-two"), body=b"encrypted body"):
    header = struct.pack("<8sII", b"crypt4gh", 1, len(packets))
    for packet in packets:
        header += struct.pack("<I", len(packet) + 4) + packet
    return header, header + body


@pytest.fixture(scope="module")
def enabled_registry():
    return example_datatype_registry_for_sample(crypt4gh_enabled=True)


@pytest.fixture(scope="module")
def disabled_registry():
    return example_datatype_registry_for_sample()


def test_read_header_returns_only_header_bytes(tmp_path):
    header, contents = _crypt4gh_bytes()
    path = tmp_path / "reads.fastqsanger.c4gh"
    path.write_bytes(contents)
    assert read_crypt4gh_header(str(path)) == header
    assert check_crypt4gh(str(path))


@pytest.mark.parametrize(
    "contents",
    [
        b"",
        b"crypt4gh",
        struct.pack("<8sII", b"notcrypt", 1, 0),
        struct.pack("<8sII", b"crypt4gh", 2, 0),
        struct.pack("<8sII", b"crypt4gh", 1, 1) + struct.pack("<I", 40) + b"short",
        struct.pack("<8sII", b"crypt4gh", 1, 1) + struct.pack("<I", 2),
    ],
)
def test_invalid_headers_are_rejected(tmp_path, contents):
    path = tmp_path / "invalid"
    path.write_bytes(contents)
    with pytest.raises(ValueError):
        read_crypt4gh_header(str(path))
    assert not check_crypt4gh(str(path))


def test_extension_helpers():
    assert is_crypt4gh_file_ext("c4gh")
    assert is_crypt4gh_file_ext("crypt4gh")
    assert is_crypt4gh_file_ext("fastqsanger.c4gh")
    assert not is_crypt4gh_file_ext("fastqsanger")
    assert wrap_crypt4gh_file_ext("fastqsanger") == "fastqsanger.c4gh"
    assert wrap_crypt4gh_file_ext("fastqsanger.c4gh") == "fastqsanger.c4gh"
    assert unwrap_crypt4gh_file_ext("fastqsanger.c4gh") == "fastqsanger"
    assert unwrap_crypt4gh_file_ext("c4gh") is None
    assert unwrap_crypt4gh_file_ext("fastqsanger") is None


def test_preserve_inner_ext_on_redetection():
    assert preserve_crypt4gh_inner_file_ext("c4gh", current_ext="vcf.c4gh") == "vcf.c4gh"
    assert preserve_crypt4gh_inner_file_ext("c4gh", current_ext="c4gh", metadata_inner_ext="vcf") == "vcf.c4gh"
    assert preserve_crypt4gh_inner_file_ext("c4gh", current_ext="c4gh", metadata_inner_ext="data") == "c4gh"
    # Anything else detected wins, the file is no longer encrypted.
    assert preserve_crypt4gh_inner_file_ext("txt", current_ext="vcf.c4gh") == "txt"


def test_disabled_registry_has_no_crypt4gh_datatypes(disabled_registry):
    assert not disabled_registry.crypt4gh_enabled
    assert not any(is_crypt4gh_file_ext(ext) for ext in disabled_registry.datatypes_by_extension)
    assert not any(isinstance(datatype, Crypt4GH) for datatype in disabled_registry.sniff_order)
    assert disabled_registry.get_datatype_from_filename("reads.fastqsanger.c4gh").file_ext == "data"
    assert guess_ext_from_file_name("reads.fastqsanger.c4gh", disabled_registry) == "data"


def test_enabled_registry_registers_wrappers(enabled_registry):
    fastqsanger = enabled_registry.get_datatype_by_extension("fastqsanger")
    wrapped = enabled_registry.get_datatype_by_extension("fastqsanger.c4gh")
    assert isinstance(wrapped, Crypt4GH)
    assert wrapped.crypt4gh_inner_datatype is fastqsanger
    assert isinstance(enabled_registry.get_datatype_by_extension("c4gh"), Crypt4GH)
    assert enabled_registry.get_datatype_from_filename("reads.fastqsanger.c4gh").file_ext == "fastqsanger.c4gh"
    assert enabled_registry.get_datatype_from_filename("reads.c4gh").file_ext == "c4gh"
    assert guess_ext_from_file_name("reads.fq.c4gh", enabled_registry) == "fastqsanger.c4gh"


def test_only_generic_wrapper_sniffs(enabled_registry):
    crypt4gh_sniffers = [datatype for datatype in enabled_registry.sniff_order if isinstance(datatype, Crypt4GH)]
    assert [datatype.file_ext for datatype in crypt4gh_sniffers] == ["c4gh"]


def test_typed_wrapper_matches_inner_type(enabled_registry):
    fastqsanger = enabled_registry.get_datatype_by_extension("fastqsanger")
    fasta = enabled_registry.get_datatype_by_extension("fasta")
    wrapped = enabled_registry.get_datatype_by_extension("fastqsanger.c4gh")
    generic = enabled_registry.get_datatype_by_extension("c4gh")
    assert wrapped.matches_any([fastqsanger])
    assert wrapped.matches_any([wrapped])
    assert not wrapped.matches_any([fasta])
    assert not generic.matches_any([fastqsanger])
    assert generic.matches_any([generic])


def test_registry_xml_round_trips_flag(tmp_path, enabled_registry, disabled_registry):
    for registry in (enabled_registry, disabled_registry):
        path = tmp_path / f"registry_{registry.crypt4gh_enabled}.xml"
        registry.to_xml_file(str(path))
        registration = ElementTree.parse(path).find("registration")
        assert registration is not None
        assert registration.get("crypt4gh_enabled") == str(registry.crypt4gh_enabled).lower()


def test_set_meta_stores_public_header_only(tmp_path, enabled_registry):
    header, contents = _crypt4gh_bytes()
    path = tmp_path / "dataset.dat"
    path.write_bytes(contents)
    wrapped = enabled_registry.get_datatype_by_extension("vcf.c4gh")
    metadata = Bunch(element_is_set=lambda name: False)
    dataset = Bunch(
        extension="vcf.c4gh",
        metadata=metadata,
        get_file_name=lambda: str(path),
        dataset=Bunch(created_from_basename=None),
    )
    wrapped.set_meta(dataset)
    assert base64.b64decode(metadata.crypt4gh_header) == header
    assert metadata.crypt4gh_inner_ext == "vcf"


@pytest.mark.parametrize(
    "filename,requested_ext,expected",
    [
        ("reads.fastqsanger.c4gh", "auto", "fastqsanger.c4gh"),
        ("reads.c4gh", "auto", "c4gh"),
        ("reads.c4gh", "vcf", "vcf.c4gh"),
    ],
)
def test_upload_detects_crypt4gh(tmp_path, enabled_registry, filename, requested_ext, expected):
    _, contents = _crypt4gh_bytes(body=b"line one\r\nline two\r\n")
    path = tmp_path / "upload"
    path.write_bytes(contents)
    response = handle_uploaded_dataset_file_internal(
        FilePrefix(str(path)),
        enabled_registry,
        ext=requested_ext,
        tmp_dir=str(tmp_path),
        uploaded_filename=filename,
        convert_to_posix_lines=True,
    )
    assert response.ext == expected
    assert not response.converted_newlines
    with open(response.converted_path, "rb") as f:
        assert f.read() == contents


def test_upload_unchanged_when_disabled(tmp_path, disabled_registry):
    _, contents = _crypt4gh_bytes()
    path = tmp_path / "upload"
    path.write_bytes(contents)
    response = handle_uploaded_dataset_file_internal(
        FilePrefix(str(path)),
        disabled_registry,
        ext="auto",
        tmp_dir=str(tmp_path),
        uploaded_filename="reads.fastqsanger.c4gh",
    )
    assert not is_crypt4gh_file_ext(response.ext)


def test_infer_file_ext_falls_back_to_generic(enabled_registry):
    assert infer_crypt4gh_file_ext("unknown.c4gh", enabled_registry) == "c4gh"


def _redetect(tmp_path, enabled_registry, extension, crypt4gh_inner_ext):
    _, contents = _crypt4gh_bytes()
    path = tmp_path / "dataset.dat"
    path.write_bytes(contents)
    data = Bunch(
        extension=extension,
        metadata=Bunch(crypt4gh_inner_ext=crypt4gh_inner_ext),
        dataset=Bunch(get_file_name=lambda: str(path)),
    )
    return enabled_registry.redetect_ext(data)


def test_redetection_keeps_known_inner_ext(tmp_path, enabled_registry):
    assert _redetect(tmp_path, enabled_registry, "c4gh", "vcf") == "vcf.c4gh"


def test_redetection_ignores_unknown_inner_ext(tmp_path, enabled_registry):
    # Inferred from an uploaded file named 'sample.foo.c4gh'.
    assert _redetect(tmp_path, enabled_registry, "c4gh", "foo") == "c4gh"
