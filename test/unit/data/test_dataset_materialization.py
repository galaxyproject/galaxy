from pkg_resources import resource_string

from galaxy.files.unittest_utils import TestPosixConfiguredFileSources
from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    LibraryDatasetDatasetAssociation,
    store,
)
from galaxy.model.deferred import (
    materialize_collection_instance,
    materializer_factory,
)
from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    one_ld_library_deferred_model_store_dict,
)
from .model.test_model_store import (
    perform_import_from_store_dict,
    setup_fixture_context_with_history,
    StoreFixtureContextWithHistory,
)
from .test_model_copy import _create_hda

CONTENTS_2_BED = resource_string(__name__, "model/2.bed").decode("UTF-8")


def test_undeferred_hdas_untouched(tmpdir):
    app, sa_session, user, history = setup_fixture_context_with_history()
    hda_fh = tmpdir.join("file.txt")
    hda_fh.write("Moo Cow")
    hda = _create_hda(sa_session, app.object_store, history, hda_fh, include_metadata_file=False)
    sa_session.flush()

    materializer = materializer_factory(True, object_store=app.object_store)
    assert materializer.ensure_materialized(hda) == hda


def test_deferred_hdas_basic_attached():
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict()
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(True, object_store=fixture_context.app.object_store)
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_hdas_basic_attached_store_by_uuid():
    # skip a flush here so this is a different path...
    fixture_context = setup_fixture_context_with_history(store_by="uuid")
    store_dict = deferred_hda_model_store_dict()
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(True, object_store=fixture_context.app.object_store)
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)


def test_deferred_hdas_basic_detached(tmpdir):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict()
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    _assert_2_bed_metadata(deferred_hda)
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(False, transient_directory=tmpdir)
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset.state == "ok"
    external_filename = materialized_dataset.external_filename
    assert external_filename
    assert external_filename.startswith(str(tmpdir))
    _assert_path_contains_2_bed(external_filename)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_hdas_basic_detached_from_detached_hda(tmpdir):
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict()
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda

    _ensure_relations_attached_and_expunge(deferred_hda, fixture_context)

    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(False, transient_directory=tmpdir)
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset.state == "ok"
    external_filename = materialized_dataset.external_filename
    assert external_filename
    assert external_filename.startswith(str(tmpdir))
    _assert_path_contains_2_bed(external_filename)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_hdas_basic_attached_from_detached_hda():
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict()
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda

    _ensure_relations_attached_and_expunge(deferred_hda, fixture_context)

    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(
        True, object_store=fixture_context.app.object_store, sa_session=fixture_context.sa_session
    )
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_ldda_basic_attached():
    import_options = store.ImportOptions(
        allow_library_creation=True,
    )
    fixture_context = setup_fixture_context_with_history()
    store_dict = one_ld_library_deferred_model_store_dict()
    perform_import_from_store_dict(fixture_context, store_dict, import_options=import_options)
    deferred_ldda = fixture_context.sa_session.query(LibraryDatasetDatasetAssociation).all()[0]
    assert deferred_ldda
    assert deferred_ldda.dataset.state == "deferred"

    materializer = materializer_factory(True, object_store=fixture_context.app.object_store)
    materialized_hda = materializer.ensure_materialized(deferred_ldda)
    assert materialized_hda.history is None
    materialized_dataset = materialized_hda.dataset
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
    file_sources = TestPosixConfiguredFileSources(root)
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(
        source_uri="gxfiles://test1/2.bed",
    )
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(True, object_store=fixture_context.app.object_store, file_sources=file_sources)
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)
    _assert_2_bed_metadata(materialized_hda)


def test_deferred_hdas_with_deferred_metadata():
    fixture_context = setup_fixture_context_with_history()
    store_dict = deferred_hda_model_store_dict(metadata_deferred=True)
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    assert deferred_hda
    assert deferred_hda.dataset.state == "deferred"
    materializer = materializer_factory(True, object_store=fixture_context.app.object_store)
    materialized_hda = materializer.ensure_materialized(deferred_hda)
    materialized_dataset = materialized_hda.dataset
    assert not materialized_hda.metadata_deferred
    assert materialized_dataset.state == "ok"
    # only detached datasets would be created with an external_filename
    assert not materialized_dataset.external_filename
    object_store = fixture_context.app.object_store
    path = object_store.get_filename(materialized_dataset)
    assert path
    _assert_path_contains_2_bed(path)
    _assert_2_bed_metadata(materialized_hda)


def test_materialize_attached_hdcas_unimplemented(tmpdir):
    fixture_context = setup_fixture_context_with_history()
    materializer = materializer_factory(True, object_store=fixture_context.app.object_store)
    hdca = _test_hdca(tmpdir, fixture_context)
    exception_found = False
    try:
        materialize_collection_instance(hdca, materializer)
    except NotImplementedError:
        exception_found = True
    assert exception_found


def test_materialize_unattached_undeferred_hdcas_noop(tmpdir):
    fixture_context = setup_fixture_context_with_history()
    materializer = materializer_factory(False, transient_directory=tmpdir)
    input_hdca = _test_hdca(tmpdir, fixture_context, include_element_deferred=False)
    materialized_hdca = materialize_collection_instance(input_hdca, materializer)
    assert input_hdca == materialized_hdca  # doesn't have deferred data so just assert it is input.


def test_materialize_unattached_deferred_hdcas(tmpdir):
    fixture_context = setup_fixture_context_with_history()
    materializer = materializer_factory(False, transient_directory=tmpdir)
    deferred_hdca = _test_hdca(tmpdir, fixture_context)
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
    include_element_deferred: bool = True,
    include_element_ok: bool = True,
) -> HistoryDatasetCollectionAssociation:
    app, sa_session, _, history = fixture_context
    store_dict = deferred_hda_model_store_dict()
    perform_import_from_store_dict(fixture_context, store_dict)
    deferred_hda = fixture_context.history.datasets[0]
    sa_session.add(deferred_hda)
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
    sa_session.flush()
    return hdca


def _deferred_element_count(dataset_collection: DatasetCollection) -> int:
    count = 0
    for element in dataset_collection.elements:
        if element.is_collection:
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
    [s.hashes for s in deferred_hda.dataset.sources]
    deferred_hda.dataset.hashes
    deferred_hda._metadata
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
    with open(path, "r") as f:
        contents = f.read()
    assert contents == CONTENTS_2_BED
