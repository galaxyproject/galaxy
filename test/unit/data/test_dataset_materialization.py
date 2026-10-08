import functools
import gzip
import json
import os
import threading
from collections.abc import Iterator
from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import (
    Any,
    NamedTuple,
)

import pytest
from sqlalchemy import select

from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.files import ConfiguredFileSources
from galaxy.files.unittest_utils import (
    stock_file_sources_allowing_loopback,
    TestPosixConfiguredFileSources,
)
from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    LibraryDatasetDatasetAssociation,
    store,
)
from galaxy.model.deferred import (
    DatasetInstanceMaterializer,
    materialize_collection_instance,
    materializer_factory,
)
from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    deferred_hda_model_store_dict_space_to_tab,
    one_ld_library_deferred_model_store_dict,
    TEST_SOURCE_URI,
    TEST_SOURCE_URI_SIMPLE_LINE,
)
from galaxy.util.resources import resource_string
from .model.test_model_store import (
    perform_import_from_store_dict,
    setup_fixture_context_with_history,
    StoreFixtureContextWithHistory,
)
from .test_model_copy import _create_hda

CONTENTS_2_BED = resource_string(__name__, "model/2.bed")


@pytest.fixture
def bed_uri(test_http_server) -> str:
    return test_http_server.get_url(remote_url=TEST_SOURCE_URI, file_path="test-data/2.bed")


@pytest.fixture
def simple_line_uri(test_http_server) -> str:
    return test_http_server.get_url(remote_url=TEST_SOURCE_URI_SIMPLE_LINE, file_path="test-data/simple_line.txt")


def test_undeferred_hdas_untouched(tmpdir):
    app, sa_session, user, history = setup_fixture_context_with_history()
    hda_fh = tmpdir.join("file.txt")
    hda_fh.write("Moo Cow")
    hda = _create_hda(sa_session, app.object_store, history, hda_fh, include_metadata_file=False)
    sa_session.commit()

    materializer = materializer_factory(True, object_store=app.object_store, datatypes_registry=app.datatypes_registry)
    assert materializer.ensure_materialized(hda) == hda


def test_deferred_hdas_basic_attached(bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)
    _assert_2_bed_metadata(materialized_hda)


def test_hash_validate(bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"


def test_hash_invalid(bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    store_dict["datasets"][0]["file_metadata"]["hashes"][0]["hash_value"] = "invalidhash"
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "error"


def test_legacy_transform_actions_on_deferred_hdas_become_requested_actions(bed_uri):
    # pre 25.1 we didn't have the distinction between requested and applied transforms,
    # so we need to ensure that legacy transforms are converted to requested transforms for
    # deferred datasets. In 25.1 - deferred datasets should always have empty transforms as
    # no actions have been applied yet.
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    store_dict["datasets"][0]["file_metadata"]["sources"][0]["transform"] = [{"action": "spaces_to_tabs"}]
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    deferred_dataset = deferred_hda.dataset
    assert deferred_dataset is not None
    assert deferred_dataset.sources[0].transform is None
    assert deferred_dataset.sources[0].requested_transform == [{"action": "spaces_to_tabs"}]


def test_requested_transform_actions_on_deferred_hdas_preserved(bed_uri):
    # Continued from previous comment, in 25.1 - deferred datasets should have transforms saved
    # as requested transforms, so we need to ensure that these are preserved during store import.
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    store_dict["datasets"][0]["file_metadata"]["sources"][0]["requested_transform"] = [{"action": "spaces_to_tabs"}]
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    deferred_dataset = deferred_hda.dataset
    assert deferred_dataset is not None
    assert deferred_dataset.sources[0].transform is None
    assert deferred_dataset.sources[0].requested_transform == [{"action": "spaces_to_tabs"}]


def test_hash_validate_source_of_download(bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    store_dict["datasets"][0]["file_metadata"]["sources"][0]["hashes"] = [
        {"model_class": "DatasetSourceHash", "hash_function": "MD5", "hash_value": "f568c29421792b1b1df4474dafae01f1"}
    ]
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok", materialized_hda.info


def test_hash_invalid_source_of_download(bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    store_dict["datasets"][0]["file_metadata"]["sources"][0]["hashes"] = [
        {"model_class": "DatasetSourceHash", "hash_function": "MD5", "hash_value": "invalidhash"}
    ]
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "error", materialized_hda.info


def test_deferred_hdas_basic_attached_store_by_uuid(bed_uri):
    # skip a flush here so this is a different path...
    fixture_context = setup_fixture_context_with_history(store_by="uuid")
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)


def test_deferred_hdas_basic_detached(tmpdir, bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        False,
        transient_directory=tmpdir,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    assert materialized_hda.name == deferred_hda.name
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"
    external_filename = materialized_dataset.external_filename
    assert external_filename
    assert external_filename.startswith(str(tmpdir))
    _assert_path_contains_2_bed(external_filename)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_datasets_with_legacy_transforms_respect_transform(tmpdir, simple_line_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict_space_to_tab("legacy", source_uri=simple_line_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    assert deferred_hda.dataset.sources[0].transform is None
    assert deferred_hda.dataset.sources[0].requested_transform == [{"action": "spaces_to_tabs"}]
    materializer = materializer_factory(
        False,
        transient_directory=tmpdir,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.sources[0].transform == [{"action": "spaces_to_tabs"}]
    assert materialized_dataset.sources[0].requested_transform == [{"action": "spaces_to_tabs"}]
    assert materialized_dataset.state == "ok"
    external_filename = materialized_dataset.external_filename
    assert external_filename
    assert external_filename.startswith(str(tmpdir))
    _assert_path_contains_simple_lines_as_tsv(external_filename)


def test_deferred_datasets_with_requested_transforms_respect_transform(tmpdir, simple_line_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict_space_to_tab("25.1", source_uri=simple_line_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    assert deferred_hda.dataset.sources[0].transform is None
    assert deferred_hda.dataset.sources[0].requested_transform == [
        {"action": "datatype_groom"},
        {"action": "spaces_to_tabs"},
    ]
    materializer = materializer_factory(
        False,
        transient_directory=tmpdir,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.sources[0].transform == [{"action": "spaces_to_tabs"}]
    assert materialized_dataset.sources[0].requested_transform == [
        {"action": "datatype_groom"},
        {"action": "spaces_to_tabs"},
    ]
    assert materialized_dataset.state == "ok"
    external_filename = materialized_dataset.external_filename
    assert external_filename
    assert external_filename.startswith(str(tmpdir))
    _assert_path_contains_simple_lines_as_tsv(external_filename)


def test_deferred_datasets_do_not_apply_unspecified_transforms_legacy(tmpdir, simple_line_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict_space_to_tab("legacy", apply_transform=False, source_uri=simple_line_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    assert deferred_hda.dataset.sources[0].transform is None
    assert deferred_hda.dataset.sources[0].requested_transform == []
    materializer = materializer_factory(
        False,
        transient_directory=tmpdir,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.sources[0].transform == []
    assert materialized_dataset.sources[0].requested_transform == []
    assert materialized_dataset.state == "ok"
    external_filename = materialized_dataset.external_filename
    assert external_filename
    assert external_filename.startswith(str(tmpdir))
    _assert_path_contains_simple_lines_as_text(external_filename)


def test_deferred_datasets_do_not_apply_unspecified_transforms(tmpdir, simple_line_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict_space_to_tab("25.1", apply_transform=False, source_uri=simple_line_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    assert deferred_hda.dataset.sources[0].transform is None
    assert deferred_hda.dataset.sources[0].requested_transform == [{"action": "datatype_groom"}]
    materializer = materializer_factory(
        False,
        transient_directory=tmpdir,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.sources[0].transform == []
    assert materialized_dataset.sources[0].requested_transform == [{"action": "datatype_groom"}]
    assert materialized_dataset.state == "ok"
    external_filename = materialized_dataset.external_filename
    assert external_filename
    assert external_filename.startswith(str(tmpdir))
    _assert_path_contains_simple_lines_as_text(external_filename)


def test_deferred_hdas_basic_detached_from_detached_hda(tmpdir, bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda

    _ensure_relations_attached_and_expunge(deferred_hda, fixture_context)

    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        False,
        transient_directory=tmpdir,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"
    external_filename = materialized_dataset.external_filename
    assert external_filename
    assert external_filename.startswith(str(tmpdir))
    _assert_path_contains_2_bed(external_filename)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_hdas_basic_attached_from_detached_hda(bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda

    _ensure_relations_attached_and_expunge(deferred_hda, fixture_context)

    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        sa_session=fixture_context.sa_session(),
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_ldda_basic_attached(bed_uri):
    import_options = store.ImportOptions(
        allow_library_creation=True,
    )
    fixture_context = setup_fixture_context_with_history()
    store_dict = one_ld_library_deferred_model_store_dict(source_uri=bed_uri)
    perform_import_from_store_dict(fixture_context, store_dict, import_options=import_options)
    deferred_ldda = fixture_context.sa_session.scalars(select(LibraryDatasetDatasetAssociation)).all()[0]
    assert deferred_ldda
    assert deferred_ldda.dataset is not None
    assert deferred_ldda.dataset.state == "deferred"

    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_ldda)
    assert materialized_hda.history is None
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)


def test_deferred_hdas_basic_attached_file_sources(tmpdir):
    root = tmpdir / "root"
    root.mkdir()
    content_path = root / "2.bed"
    content_path.write_text(CONTENTS_2_BED, encoding="utf-8")
    file_sources = TestPosixConfiguredFileSources(str(root))
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(
        source_uri="gxfiles://test1/2.bed",
    )
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        file_sources=file_sources,
        datatypes_registry=fixture_context.app.datatypes_registry,
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)
    _assert_2_bed_metadata(materialized_hda)


class _StoreRequestHandler(SimpleHTTPRequestHandler):
    """Serve files like a static web server, optionally answering like a public S3 bucket."""

    # Public S3 buckets that do not allow listing answer 403 for objects that do not exist.
    missing_status: int = 404
    denied_paths: set[str] = set()

    def do_GET(self) -> None:
        if self.path in self.denied_paths:
            super().send_error(403)
            return
        super().do_GET()

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        super().send_error(self.missing_status if code == 404 else code, message, explain)

    def log_message(self, format: str, *args: Any) -> None:
        pass


class DirectoryHttpServer(NamedTuple):
    served: Path
    base_url: str
    handler: type[_StoreRequestHandler]


@pytest.fixture
def directory_http_server(tmp_path: Path) -> Iterator[DirectoryHttpServer]:
    """Serve ``tmp_path / "served"`` over HTTP, which cannot list directories through file sources."""
    served = tmp_path / "served"
    served.mkdir()

    class Handler(_StoreRequestHandler):
        denied_paths: set[str] = set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(served)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield DirectoryHttpServer(served, f"http://127.0.0.1:{server.server_address[1]}", Handler)
    finally:
        server.shutdown()


def _write_json_file(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content))


ZARR_V3_ARRAY_METADATA: dict[str, Any] = {
    "zarr_format": 3,
    "node_type": "array",
    "shape": [3],
    "data_type": "uint8",
    "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": [2]}},
    "chunk_key_encoding": {"name": "default", "configuration": {"separator": "/"}},
    "fill_value": 0,
    "codecs": [{"name": "bytes"}],
}


def _write_zarr_v3_store(root: Path, consolidated: bool) -> None:
    group: dict[str, Any] = {"zarr_format": 3, "node_type": "group", "attributes": {}}
    if consolidated:
        group["consolidated_metadata"] = {
            "kind": "inline",
            "must_understand": False,
            "metadata": {"arr": ZARR_V3_ARRAY_METADATA},
        }
    _write_json_file(root / "zarr.json", group)
    _write_json_file(root / "arr" / "zarr.json", ZARR_V3_ARRAY_METADATA)
    (root / "arr" / "c").mkdir()
    # Only the first chunk is stored, the second holds just the fill value.
    (root / "arr" / "c" / "0").write_bytes(b"\x01\x02")


def _write_zarr_v2_store(root: Path) -> None:
    array = {"zarr_format": 2, "shape": [3], "chunks": [2], "dtype": "|u1", "fill_value": 0, "compressor": None}
    _write_json_file(root / ".zgroup", {"zarr_format": 2})
    _write_json_file(root / "arr" / ".zarray", array)
    _write_json_file(
        root / ".zmetadata",
        {"zarr_consolidated_format": 1, "metadata": {".zgroup": {"zarr_format": 2}, "arr/.zarray": array}},
    )
    # Only the first chunk is stored, the second holds just the fill value.
    (root / "arr" / "0").write_bytes(b"\x01\x02")


def _write_directory(root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True)
    for rel_path, content in files.items():
        (root / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (root / rel_path).write_text(content, encoding="utf-8")


def _deferred_hda_with_extension(
    monkeypatch: pytest.MonkeyPatch, source_uri: str, extension: str
) -> tuple[StoreFixtureContextWithHistory, HistoryDatasetAssociation]:
    fixture_context = setup_fixture_context_with_history()
    perform_import_from_store_dict(fixture_context, deferred_hda_model_store_dict(source_uri=source_uri))
    # The fixture's registry has no directory datatypes.
    monkeypatch.setattr("galaxy.model._datatypes_registry", example_datatype_registry_for_sample())
    deferred_hda = fixture_context.history.datasets[0]
    deferred_hda.extension = extension
    return fixture_context, deferred_hda


def _unattached_materializer(
    transient_directory: Path, file_sources: ConfiguredFileSources
) -> DatasetInstanceMaterializer:
    return materializer_factory(
        False,
        transient_directory=str(transient_directory),
        file_sources=file_sources,
        datatypes_registry=example_datatype_registry_for_sample(),
    )


def _relative_files(root: str) -> list[str]:
    return sorted(
        os.path.relpath(os.path.join(dirpath, filename), root)
        for dirpath, _, filenames in os.walk(root)
        for filename in filenames
    )


def test_deferred_directory_materialized_from_listable_file_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_directory(tmp_path / "root" / "index", {"a.txt": "a", "nested/b.txt": "b"})
    fixture_context, deferred_hda = _deferred_hda_with_extension(monkeypatch, "gxfiles://test1/index", "directory")
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        file_sources=TestPosixConfiguredFileSources(str(tmp_path / "root")),
        datatypes_registry=fixture_context.app.datatypes_registry,
    )

    materialized_hda = materializer.ensure_materialized(deferred_hda)

    assert materialized_hda.dataset
    assert materialized_hda.dataset.state == "ok", materialized_hda.info
    assert _relative_files(materialized_hda.extra_files_path) == ["a.txt", os.path.join("nested", "b.txt")]


@pytest.mark.parametrize("missing_status", [404, 403])
def test_deferred_zarr_materialized_over_http_from_consolidated_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory_http_server: DirectoryHttpServer, missing_status: int
) -> None:
    directory_http_server.handler.missing_status = missing_status
    _write_zarr_v3_store(directory_http_server.served / "store.zarr", consolidated=True)
    _, deferred_hda = _deferred_hda_with_extension(monkeypatch, f"{directory_http_server.base_url}/store.zarr", "zarr")
    materializer = _unattached_materializer(tmp_path, stock_file_sources_allowing_loopback())

    materialized_hda = materializer.ensure_materialized(deferred_hda)

    assert materialized_hda.dataset
    assert materialized_hda.dataset.state == "ok", materialized_hda.info
    assert _relative_files(materialized_hda.extra_files_path) == [
        os.path.join("arr", "c", "0"),
        os.path.join("arr", "zarr.json"),
        "zarr.json",
    ]
    assert materialized_hda.metadata.zarr_format == 3
    assert materialized_hda.metadata.store_root == ""


@pytest.mark.parametrize("missing_status", [404, 403])
def test_deferred_zarr_v2_materialized_over_http_from_consolidated_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory_http_server: DirectoryHttpServer, missing_status: int
) -> None:
    directory_http_server.handler.missing_status = missing_status
    _write_zarr_v2_store(directory_http_server.served / "store.zarr")
    _, deferred_hda = _deferred_hda_with_extension(monkeypatch, f"{directory_http_server.base_url}/store.zarr", "zarr")
    materializer = _unattached_materializer(tmp_path, stock_file_sources_allowing_loopback())

    materialized_hda = materializer.ensure_materialized(deferred_hda)

    assert materialized_hda.dataset
    assert materialized_hda.dataset.state == "ok", materialized_hda.info
    assert _relative_files(materialized_hda.extra_files_path) == [
        ".zgroup",
        ".zmetadata",
        os.path.join("arr", ".zarray"),
        os.path.join("arr", "0"),
    ]
    assert materialized_hda.metadata.zarr_format == 2


def test_denied_zarr_chunk_is_an_error_when_the_server_reports_missing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory_http_server: DirectoryHttpServer
) -> None:
    _write_zarr_v3_store(directory_http_server.served / "store.zarr", consolidated=True)
    # The server answers 404 for missing files, so a 403 is a real denial, not an unwritten chunk.
    directory_http_server.handler.denied_paths = {"/store.zarr/arr/c/0"}
    _, deferred_hda = _deferred_hda_with_extension(monkeypatch, f"{directory_http_server.base_url}/store.zarr", "zarr")
    materializer = _unattached_materializer(tmp_path, stock_file_sources_allowing_loopback())

    materialized_hda = materializer.ensure_materialized(deferred_hda)

    assert materialized_hda.dataset
    assert materialized_hda.dataset.state == "error"
    assert "403" in materialized_hda.info


def test_deferred_empty_directory_is_not_materialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_directory(tmp_path / "root" / "index", {})
    _, deferred_hda = _deferred_hda_with_extension(monkeypatch, "gxfiles://test1/index", "directory")
    materializer = _unattached_materializer(
        tmp_path / "staging", TestPosixConfiguredFileSources(str(tmp_path / "root"))
    )

    materialized_hda = materializer.ensure_materialized(deferred_hda)

    assert materialized_hda.dataset
    assert materialized_hda.dataset.state == "error"
    assert "empty or does not exist" in materialized_hda.info


def test_deferred_zarr_over_http_needs_consolidated_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory_http_server: DirectoryHttpServer
) -> None:
    _write_zarr_v3_store(directory_http_server.served / "store.zarr", consolidated=False)
    _, deferred_hda = _deferred_hda_with_extension(monkeypatch, f"{directory_http_server.base_url}/store.zarr", "zarr")
    materializer = _unattached_materializer(tmp_path, stock_file_sources_allowing_loopback())

    materialized_hda = materializer.ensure_materialized(deferred_hda)

    assert materialized_hda.dataset
    assert materialized_hda.dataset.state == "error"
    assert "must have consolidated metadata" in materialized_hda.info


HDF5_CONTENTS = b"\x89HDF\r\n\x1a\n\x00\x00\x00\x00\x00\x08\x08\x00\x04\x00\x10\x00\r\x00\r\n"
GZIPPED_CRLF_CONTENTS = gzip.compress(b"a\tb\r\n" * 1000, mtime=0)


@pytest.mark.parametrize(
    "filename,extension,contents",
    [
        ("dataset.h5ad", "h5ad", HDF5_CONTENTS),
        ("dataset.txt.gz", "txt.gz", GZIPPED_CRLF_CONTENTS),
    ],
)
def test_deferred_binary_contents_not_converted(tmpdir, filename, extension, contents):
    assert b"\r" in contents
    root = tmpdir / "root"
    root.mkdir()
    (root / filename).write_binary(contents)
    file_sources = TestPosixConfiguredFileSources(str(root))
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=f"gxfiles://test1/{filename}", metadata_deferred=True)
    serialized_hda = store_dict["datasets"][0]
    serialized_hda["extension"] = extension
    serialized_hda["file_metadata"]["hashes"] = []
    serialized_hda["file_metadata"]["sources"][0]["requested_transform"] = [
        {"action": "datatype_groom"},
        {"action": "to_posix_lines"},
        {"action": "spaces_to_tabs"},
    ]
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=file_sources,
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert materialized_dataset.state == "ok"
    assert materialized_dataset.sources[0].transform == []
    path = fixture_context.app.object_store.get_filename(materialized_dataset)
    with open(path, "rb") as f:
        assert f.read() == contents


def test_deferred_hdas_with_deferred_metadata(bed_uri):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri, metadata_deferred=True)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset is not None
    assert not materialized_hda.metadata_deferred
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_hda_with_auto_extension_gets_sniffed_from_content(bed_uri):
    # Scenario: a deferred fetch/upload with no explicit ``ext`` is stored as
    # extension="auto" because the bytes aren't available to sniff at request time
    # (data_fetch.py: ``requested_ext = item.get("ext", "auto")``). When the dataset is
    # later materialized for a tool run, the real type is sniffed from the downloaded
    # content. Requires a datatypes_registry.
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(source_uri=bed_uri)
    store_dict["datasets"][0]["extension"] = "auto"
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda.extension == "auto"
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"

    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)

    assert materialized_hda.dataset is not None
    assert materialized_hda.dataset.state == "ok"
    # The fixture source is a .bed file; content sniffing must upgrade "auto" to "bed".
    assert materialized_hda.extension == "bed"


def test_materialize_attached_hdcas_unimplemented(tmpdir, bed_uri):
    fixture_context = setup_fixture_context_with_history()
    materializer = materializer_factory(
        True,
        object_store=fixture_context.app.object_store,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    hdca = _test_hdca(tmpdir, fixture_context, bed_uri)
    exception_found = False
    try:
        materialize_collection_instance(hdca, materializer)
    except NotImplementedError:
        exception_found = True
    assert exception_found


def test_materialize_unattached_undeferred_hdcas_noop(tmpdir, bed_uri):
    fixture_context = setup_fixture_context_with_history()
    materializer = materializer_factory(
        False,
        transient_directory=tmpdir,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    input_hdca = _test_hdca(tmpdir, fixture_context, bed_uri, include_element_deferred=False)
    materialized_hdca = materialize_collection_instance(input_hdca, materializer)
    assert input_hdca == materialized_hdca  # doesn't have deferred data so just assert it is input.


def test_materialize_unattached_deferred_hdcas(tmpdir, bed_uri):
    fixture_context = setup_fixture_context_with_history()
    materializer = materializer_factory(
        False,
        transient_directory=tmpdir,
        datatypes_registry=fixture_context.app.datatypes_registry,
        file_sources=stock_file_sources_allowing_loopback(),
    )
    deferred_hdca = _test_hdca(tmpdir, fixture_context, bed_uri)
    assert deferred_hdca.has_deferred_data
    assert len(deferred_hdca.collection.elements) == 2
    assert _deferred_element_count(deferred_hdca.collection) == 1
    materialized_hdca = materialize_collection_instance(deferred_hdca, materializer)
    assert not materialized_hdca.has_deferred_data
    assert materialized_hdca.name == deferred_hdca.name
    materialized_collection = materialized_hdca.collection
    assert materialized_collection
    materialized_elements = materialized_collection.elements
    assert len(materialized_elements) == 2
    assert _deferred_element_count(materialized_collection) == 0


def _test_hdca(
    tmpdir,
    fixture_context: StoreFixtureContextWithHistory,
    source_uri: str,
    include_element_deferred: bool = True,
    include_element_ok: bool = True,
) -> HistoryDatasetCollectionAssociation:
    app, sa_session, _, history = fixture_context
    store_dict = deferred_hda_model_store_dict(source_uri=source_uri)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    sa_session.add(deferred_hda)
    assert deferred_hda.dataset is not None
    assert deferred_hda.dataset.state == "deferred"
    hda_fh = tmpdir.join("file.txt")
    hda_fh.write("Moo Cow")
    hda = _create_hda(sa_session, app.object_store, history, hda_fh, include_metadata_file=False)
    elements = []
    element_index = 0
    if include_element_deferred:
        elements.append(
            DatasetCollectionElement(
                element=deferred_hda,
                element_identifier="deferred_hda",
                element_index=element_index,
            )
        )
        element_index += 1
    if include_element_ok:
        elements.append(
            DatasetCollectionElement(
                element=hda,
                element_identifier="ok_hda",
                element_index=element_index,
            )
        )
        element_index += 1
    collection = DatasetCollection(collection_type="list", populated=True)
    collection.elements = elements
    hdca = HistoryDatasetCollectionAssociation(
        history=history,
        hid=1,
        collection=collection,
        name="HistoryCollectionTest1",
    )
    sa_session.add(hdca)
    sa_session.add(collection)
    sa_session.commit()
    return hdca


def _deferred_element_count(dataset_collection: DatasetCollection) -> int:
    count = 0
    for element in dataset_collection.elements:
        if element.is_collection:
            assert element.child_collection
            count += _deferred_element_count(element.child_collection)
        else:
            dataset_instance = element.dataset_instance
            print(dataset_instance.dataset.state)
            if dataset_instance.dataset.state == "deferred":
                count += 1
    return count


def _ensure_relations_attached_and_expunge(deferred_hda: HistoryDatasetAssociation, fixture_context) -> None:
    # make sure everything needed is in session (sources, hashes, and metadata)...
    # point here is exercise deferred_hda.history throws a detached error.
    assert deferred_hda.dataset is not None
    [s.hashes for s in deferred_hda.dataset.sources]
    deferred_hda.dataset.hashes  # noqa: B018
    deferred_hda._metadata  # noqa: B018
    sa_session = fixture_context.sa_session
    sa_session.expunge_all()


def _assert_2_bed_metadata(hda: HistoryDatasetAssociation) -> None:
    assert hda.metadata.columns == 6
    assert hda.metadata.data_lines == 68
    assert hda.metadata.comment_lines == 0
    assert hda.metadata.chromCol == 1
    assert hda.metadata.startCol == 2
    assert hda.metadata.endCol == 3
    assert hda.metadata.viz_filter_cols == [4]


def _assert_path_contains_2_bed(path) -> None:
    with open(path) as f:
        contents = f.read()
    assert contents == CONTENTS_2_BED


def _assert_path_contains_simple_lines_as_tsv(path) -> None:
    with open(path) as f:
        contents = f.read()
    assert contents == "This\tis\ta\tline\tof\ttext.\n"  # simple lines as TSV


def _assert_path_contains_simple_lines_as_text(path) -> None:
    with open(path) as f:
        contents = f.read()
    assert contents == "This is a line of text.\n"  # simple lines as text
