"""Unit tests for importing and exporting data from model stores."""

import json
import os
import pathlib
import shutil
from tempfile import (
    mkdtemp,
    NamedTemporaryFile,
)
from typing import (
    Any,
    Dict,
    NamedTuple,
    Optional,
)

import pytest
from rocrate.rocrate import ROCrate
from sqlalchemy import select
from sqlalchemy.orm.scoping import scoped_session
from unittest.mock import Mock

from galaxy import model
from galaxy.model import store
from galaxy.model.metadata import MetadataTempFile
from galaxy.model.orm.now import now
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    one_hda_model_store_dict,
    one_ld_library_model_store_dict,
    TEST_HASH_FUNCTION,
    TEST_HASH_VALUE,
    TEST_SOURCE_URI,
)
from galaxy.objectstore.unittest_utils import Config as TestConfig
from galaxy.util.compression_utils import CompressedFile
from ..test_galaxy_mapping import (
    _invocation_for_workflow,
    _workflow_from_steps,
)

TESTCASE_DIRECTORY = pathlib.Path(__file__).parent
TEST_PATH_1 = TESTCASE_DIRECTORY / "1.txt"
TEST_PATH_2 = TESTCASE_DIRECTORY / "2.bed"
TEST_PATH_2_CONVERTED = TESTCASE_DIRECTORY / "2.txt"
DEFAULT_OBJECT_STORE_BY = "id"


def test_import_export_history():
    """Test a simple job import/export after decompressing an archive (like history import/export tool)."""
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    imported_history = _import_export_history(app, h, export_files="copy")

    _assert_simple_cat_job_imported(imported_history)


def test_import_export_history_failed_job():
    """Test a simple job import/export, make sure state is maintained correctly."""
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app, state="error")

    imported_history = _import_export_history(app, h, export_files="copy")

    _assert_simple_cat_job_imported(imported_history, state="error")


def test_import_export_history_hidden_false_with_hidden_dataset():
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)
    d2.visible = False
    app.commit()

    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=False)
    assert d1.dataset.get_size() == imported_history.datasets[0].get_size()
    assert imported_history.datasets[1].get_size() == 0


def test_import_export_history_hidden_true_with_hidden_dataset():
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)
    d2.visible = False
    app.commit()

    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=True)
    assert d1.dataset.get_size() == imported_history.datasets[0].get_size()
    assert d2.dataset.get_size() == imported_history.datasets[1].get_size()


def test_import_export_history_allow_discarded_data():
    """Test an export and import without exporting dataset file data.

    Experimental state that should result in 'discarded' datasets that are not
    deleted.
    """
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    import_options = store.ImportOptions(
        discarded_data=store.ImportDiscardedDataType.ALLOW,
    )
    imported_history = _import_export_history(app, h, export_files=None, import_options=import_options)
    assert imported_history.name == "imported from archive: Test History"

    datasets = imported_history.datasets
    assert len(datasets) == 2
    assert datasets[0].state == datasets[1].state == model.Dataset.states.DISCARDED
    assert datasets[0].deleted is False

    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.state == "ok"
    assert imported_job.output_datasets
    assert imported_job.output_datasets[0].dataset == datasets[1]


def setup_history_with_implicit_conversion():
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    intermediate_ext = "bam"
    intermediate_implicit_hda = model.HistoryDatasetAssociation(
        extension=intermediate_ext, create_dataset=True, flush=False, history=h
    )
    intermediate_implicit_hda.hid = d2.hid
    convert_ext = "fasta"
    implicit_hda = model.HistoryDatasetAssociation(extension=convert_ext, create_dataset=True, flush=False, history=h)
    implicit_hda.hid = d2.hid
    # this adds and flushes the result...
    intermediate_implicit_hda.attach_implicitly_converted_dataset(app.model.context, implicit_hda, convert_ext)
    d2.attach_implicitly_converted_dataset(app.model.context, intermediate_implicit_hda, intermediate_ext)

    app.object_store.update_from_file(intermediate_implicit_hda.dataset, file_name=TEST_PATH_2_CONVERTED, create=True)
    app.object_store.update_from_file(implicit_hda.dataset, file_name=TEST_PATH_2_CONVERTED, create=True)

    assert len(h.active_datasets) == 4
    return app, h, implicit_hda


def test_import_export_history_with_implicit_conversion():
    app, h, _ = setup_history_with_implicit_conversion()
    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=True)

    assert len(imported_history.active_datasets) == 4
    recovered_hda_2 = imported_history.active_datasets[1]
    assert recovered_hda_2.implicitly_converted_datasets
    intermediate_conversion = recovered_hda_2.implicitly_converted_datasets[0]
    assert intermediate_conversion.type == "bam"
    intermediate_hda = intermediate_conversion.dataset
    assert intermediate_hda.implicitly_converted_datasets
    final_conversion = intermediate_hda.implicitly_converted_datasets[0]

    assert final_conversion.type == "fasta"
    assert final_conversion.dataset == imported_history.active_datasets[-1]

    # implicit conversions have the same HID... ensure this property is recovered...
    assert imported_history.active_datasets[2].hid == imported_history.active_datasets[1].hid


def test_import_export_history_with_implicit_conversion_parents_purged():
    app, h, implicit_hda = setup_history_with_implicit_conversion()
    # Purge parents
    parent = implicit_hda.implicitly_converted_parent_datasets[0].parent_hda
    parent.dataset.purged = True
    grandparent = parent.implicitly_converted_parent_datasets[0].parent_hda
    grandparent.dataset.purged = True
    app.model.context.commit()
    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=True)

    assert len(imported_history.active_datasets) == 2
    assert len(imported_history.datasets) == 4
    imported_implicit_hda = imported_history.active_datasets[1]
    assert imported_implicit_hda.extension == "fasta"

    # implicit conversions have the same HID... ensure this property is recovered...
    assert imported_implicit_hda.hid == implicit_hda.hid
    assert imported_implicit_hda.implicitly_converted_parent_datasets
    intermediate_implicit_conversion = imported_implicit_hda.implicitly_converted_parent_datasets[0]
    intermediate_hda = intermediate_implicit_conversion.parent_hda
    assert intermediate_hda.hid == implicit_hda.hid
    assert intermediate_hda.extension == "bam"
    assert intermediate_hda.implicitly_converted_datasets
    assert intermediate_hda.implicitly_converted_parent_datasets
    first_implicit_conversion = intermediate_hda.implicitly_converted_parent_datasets[0]
    source_hda = first_implicit_conversion.parent_hda
    assert source_hda.hid == implicit_hda.hid
    assert source_hda.extension == "txt"


def test_import_export_history_with_implicit_conversion_and_extra_files():
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    convert_ext = "fasta"
    implicit_hda = model.HistoryDatasetAssociation(extension=convert_ext, create_dataset=True, flush=False, history=h)
    implicit_hda.hid = d2.hid
    # this adds and flushes the result...
    d2.attach_implicitly_converted_dataset(app.model.context, implicit_hda, convert_ext)
    app.object_store.update_from_file(implicit_hda.dataset, file_name=TEST_PATH_2_CONVERTED, create=True)

    d2.dataset.create_extra_files_path()
    implicit_hda.dataset.create_extra_files_path()

    app.write_primary_file(d2, "cool primary file 1")
    app.write_composite_file(d2, "cool composite file", "child_file")

    app.write_primary_file(implicit_hda, "cool primary file implicit")
    app.write_composite_file(implicit_hda, "cool composite file implicit", "child_file_converted")

    assert len(h.active_datasets) == 3
    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=True)

    assert len(imported_history.active_datasets) == 3
    recovered_hda_2 = imported_history.active_datasets[1]
    assert recovered_hda_2.implicitly_converted_datasets
    imported_conversion = recovered_hda_2.implicitly_converted_datasets[0]
    assert imported_conversion.type == "fasta"
    assert imported_conversion.dataset == imported_history.active_datasets[2]

    # implicit conversions have the same HID... ensure this property is recovered...
    assert imported_history.active_datasets[2].hid == imported_history.active_datasets[1].hid

    _assert_extra_files_has_parent_directory_with_single_file_containing(
        imported_history.active_datasets[1], "child_file", "cool composite file"
    )

    _assert_extra_files_has_parent_directory_with_single_file_containing(
        imported_history.active_datasets[2], "child_file_converted", "cool composite file implicit"
    )


def test_import_export_bag_archive():
    """Test a simple job import/export using a BagIt archive."""
    dest_parent = mkdtemp()
    dest_export = os.path.join(dest_parent, "moo.tgz")

    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    with store.BagArchiveModelExportStore(
        dest_export, app=app, bag_archiver="tgz", export_files="copy"
    ) as export_store:
        export_store.export_history(h)

    model_store = store.BagArchiveImportModelStore(dest_export, app=app, user=u)
    with model_store.target_history(default_history=None) as imported_history:
        model_store.perform_import(imported_history)

    _assert_simple_cat_job_imported(imported_history)


def test_import_export_datasets():
    """Test a simple job import/export using a directory."""
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": False})
    u = h.user

    _perform_import_from_directory(temp_directory, app, u, import_history)

    datasets = import_history.datasets
    assert len(datasets) == 2
    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.output_datasets
    assert imported_job.output_datasets[0].dataset == datasets[1]

    assert imported_job.input_datasets
    assert imported_job.input_datasets[0].dataset == datasets[0]


def test_import_from_dict():
    fixture_context = setup_fixture_context_with_history()
    import_dict = one_hda_model_store_dict()
    perform_import_from_store_dict(fixture_context, import_dict)
    import_history = fixture_context.history

    datasets = import_history.datasets
    assert len(datasets) == 1
    imported_hda = datasets[0]
    assert imported_hda.name == "my cool name"
    assert imported_hda.hid == 1
    # it wasn't deleted going in but we delete discarded datasets by default
    assert imported_hda.state == "deferred"
    assert not imported_hda.deleted

    assert len(imported_hda.dataset.hashes) == 1
    assert len(imported_hda.dataset.sources) == 1
    assert imported_hda.dataset.created_from_basename == "dataset.txt"
    imported_dataset_hash = imported_hda.dataset.hashes[0]
    imported_dataset_source = imported_hda.dataset.sources[0]
    assert imported_dataset_hash.hash_function == TEST_HASH_FUNCTION
    assert imported_dataset_hash.hash_value == TEST_HASH_VALUE
    assert imported_dataset_source.source_uri == TEST_SOURCE_URI


def test_import_library_from_dict():
    fixture_context = setup_fixture_context_with_history()
    import_dict = one_ld_library_model_store_dict()
    import_options = store.ImportOptions()
    import_options.allow_library_creation = True
    perform_import_from_store_dict(fixture_context, import_dict, import_options=import_options)

    sa_session = fixture_context.sa_session
    all_libraries = sa_session.scalars(select(model.Library)).all()
    assert len(all_libraries) == 1, len(all_libraries)
    all_lddas = sa_session.scalars(select(model.LibraryDatasetDatasetAssociation)).all()
    assert len(all_lddas) == 1, len(all_lddas)


def test_import_allow_discarded():
    fixture_context = setup_fixture_context_with_history()
    import_dict = one_hda_model_store_dict(include_source=False)
    import_options = store.ImportOptions(
        discarded_data=store.ImportDiscardedDataType.ALLOW,
    )
    perform_import_from_store_dict(fixture_context, import_dict, import_options=import_options)
    import_history = fixture_context.history
    datasets = import_history.datasets
    assert len(datasets) == 1
    imported_hda = datasets[0]
    assert imported_hda.name == "my cool name"
    assert imported_hda.hid == 1
    # it wasn't deleted going in but we delete discarded datasets by default
    assert imported_hda.state == "discarded"
    assert not imported_hda.deleted
    assert not imported_hda.metadata_deferred


def test_import_deferred_metadata():
    fixture_context = setup_fixture_context_with_history()
    import_dict = deferred_hda_model_store_dict(metadata_deferred=True)
    import_options = store.ImportOptions(
        discarded_data=store.ImportDiscardedDataType.ALLOW,
    )
    perform_import_from_store_dict(fixture_context, import_dict, import_options=import_options)
    import_history = fixture_context.history
    datasets = import_history.datasets
    assert len(datasets) == 1
    imported_hda = datasets[0]
    assert imported_hda.name == "my cool name"
    assert imported_hda.hid == 1
    # it wasn't deleted going in but we delete discarded datasets by default
    assert imported_hda.state == "deferred"
    assert not imported_hda.deleted
    assert imported_hda.metadata_deferred


def test_import_library_require_permissions():
    """Verify library creation (import) is off by default."""
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")

    library = model.Library(name="my library 1", description="my library description", synopsis="my synopsis")
    root_folder = model.LibraryFolder(name="my library 1", description="folder description")
    library.root_folder = root_folder
    sa_session.add_all((library, root_folder))
    app.commit()

    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, app=app) as export_store:
        export_store.export_library(library)

    error_caught = False
    try:
        import_model_store = store.get_import_model_store_for_directory(temp_directory, app=app, user=u)
        import_model_store.perform_import()
    except AssertionError:
        # TODO: throw and catch a better exception...
        error_caught = True

    assert error_caught


def test_import_export_library(tmp_path):
    """Test basics of library, library folder, and library dataset import/export."""
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")

    library = model.Library(name="my library 1", description="my library description", synopsis="my synopsis")
    root_folder = model.LibraryFolder(name="my library 1", description="folder description")
    library.root_folder = root_folder
    sa_session.add_all((library, root_folder))
    app.commit()

    subfolder = model.LibraryFolder(name="sub folder 1", description="sub folder")
    root_folder.add_folder(subfolder)
    sa_session.add(subfolder)

    ld = model.LibraryDataset(folder=root_folder, name="my name", info="my library dataset")
    ldda = model.LibraryDatasetDatasetAssociation(create_dataset=True, flush=False)
    ld.library_dataset_dataset_association = ldda
    root_folder.add_library_dataset(ld)

    sa_session.add(ld)
    sa_session.add(ldda)

    app.commit()
    assert len(root_folder.datasets) == 1
    assert len(root_folder.folders) == 1

    with store.DirectoryModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_library(library)

    import_model_store = store.get_import_model_store_for_directory(
        tmp_path, app=app, user=u, import_options=store.ImportOptions(allow_library_creation=True)
    )
    import_model_store.perform_import()

    all_libraries = sa_session.scalars(select(model.Library)).all()
    assert len(all_libraries) == 2, len(all_libraries)
    all_lddas = sa_session.scalars(select(model.LibraryDatasetDatasetAssociation)).all()
    assert len(all_lddas) == 2, len(all_lddas)

    new_library = [lib for lib in all_libraries if lib.id != library.id][0]
    assert new_library.name == "my library 1"
    assert new_library.description == "my library description"
    assert new_library.synopsis == "my synopsis"

    new_root = new_library.root_folder
    assert new_root
    assert new_root.name == "my library 1"

    assert len(new_root.folders) == 1
    assert len(new_root.datasets) == 1


def test_import_export_invocation():
    app = _mock_app()
    workflow_invocation = _setup_invocation(app)

    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, app=app) as export_store:
        export_store.export_workflow_invocation(workflow_invocation)

    sa_session = app.model.context
    h2 = model.History(user=workflow_invocation.user)
    sa_session.add(h2)
    app.commit()

    import_model_store = store.get_import_model_store_for_directory(
        temp_directory, app=app, user=workflow_invocation.user, import_options=store.ImportOptions()
    )
    import_model_store.perform_import(history=h2)


def validate_crate_metadata(as_dict):
    assert as_dict["@context"] == "https://w3id.org/ro/crate/1.1/context"


def validate_has_pl_galaxy(ro_crate: ROCrate):
    programming_language = ro_crate.mainEntity.get("programmingLanguage")
    assert programming_language
    assert programming_language.id == "https://w3id.org/workflowhub/workflow-ro-crate#galaxy"
    assert programming_language.name == "Galaxy"
    assert programming_language.url == "https://galaxyproject.org/"


def validate_organize_action(ro_crate: ROCrate):
    organize_action = next((x for x in ro_crate.contextual_entities if x.type == "OrganizeAction"), None)
    assert organize_action


def validate_has_mit_license(ro_crate: ROCrate):
    found_license = False
    for e in ro_crate.get_entities():
        if e.id == "./":
            assert e["license"] == "MIT"
            found_license = True
    assert found_license


def validate_has_readme(ro_crate: ROCrate):
    found_readme = False
    for e in ro_crate.get_entities():
        if e.id == "README.md":
            assert e.type == "File"
            assert e["encodingFormat"] == "text/markdown"
            # assert e["about"] == "./"
            found_readme = True
    assert found_readme


def open_ro_crate(crate_directory):
    metadata_json_path = crate_directory / "ro-crate-metadata.json"
    with metadata_json_path.open() as f:
        metadata_json = json.load(f)
    validate_crate_metadata(metadata_json)
    crate = ROCrate(crate_directory)
    return crate


def validate_history_crate_directory(crate_directory):
    crate = open_ro_crate(crate_directory)
    validate_has_readme(crate)


def validate_main_entity(ro_crate: ROCrate):
    workflow = ro_crate.mainEntity
    assert workflow
    assert workflow.id.endswith(".gxwf.yml")
    assert workflow["name"]
    assert workflow["name"] == "Test Workflow"
    assert "SoftwareSourceCode" in workflow.type
    assert "ComputationalWorkflow" in workflow.type
    assert len(workflow["input"]) == 1
    assert len(workflow["output"]) == 1


def validate_create_action(ro_crate: ROCrate):
    workflow = ro_crate.mainEntity
    actions = [_ for _ in ro_crate.contextual_entities if "CreateAction" in _.type]
    assert len(actions) == 1
    wf_action = actions[0]
    assert wf_action["instrument"]
    assert wf_action["instrument"] is workflow
    wf_objects = wf_action["object"]
    wf_results = wf_action["result"]
    assert len(wf_objects) == 1
    assert len(wf_results) == 1
    for entity in wf_results:
        if entity.id.endswith(".txt"):
            assert "File" in entity.type
            wf_output_file = entity
            assert wf_output_file["encodingFormat"] == "text/plain"
            assert wf_output_file["exampleOfWork"] is workflow["output"][0]


def validate_other_entities(ro_crate: ROCrate):
    workflow = ro_crate.mainEntity
    inputs = workflow["input"]
    outputs = workflow["output"]
    assert inputs[0]["additionalType"] == "File"
    assert outputs[0]["additionalType"] == "File"

    for entity in inputs + outputs:
        assert "FormalParameter" in entity.type

    sel = [_ for _ in ro_crate.contextual_entities if "OrganizeAction" in _.type]
    assert len(sel) == 1
    engine_action = sel[0]
    assert "SoftwareApplication" in engine_action["instrument"].type


def validate_invocation_crate_directory(crate_directory):
    crate = open_ro_crate(crate_directory)
    for e in crate.contextual_entities:
        print(e.type)
    validate_main_entity(crate)
    validate_create_action(crate)
    validate_other_entities(crate)
    validate_has_pl_galaxy(crate)
    validate_organize_action(crate)
    validate_has_mit_license(crate)
    # validate_has_readme(crate)


def validate_invocation_collection_crate_directory(crate_directory):
    ro_crate = open_ro_crate(crate_directory)
    workflow = ro_crate.mainEntity
    root = ro_crate.root_dataset
    actions = [_ for _ in ro_crate.contextual_entities if "CreateAction" in _.type]
    assert len(actions) == 1
    wf_action = actions[0]
    assert wf_action in root["mentions"]
    assert len(workflow["input"]) == 2
    assert len(workflow["output"]) == 1
    assert len(root["mentions"]) == 4
    collections = [_ for _ in ro_crate.contextual_entities if "Collection" in _.type]
    assert len(collections) == 3
    collection = collections[0]
    assert collection.type == "Collection"
    assert (
        collection["additionalType"]
        == "https://training.galaxyproject.org/training-material/faqs/galaxy/collections_build_list.html"
    )
    assert len(collection["hasPart"]) == 2
    for dataset in collection["hasPart"]:
        assert dataset in root["hasPart"]


def test_export_history_with_missing_hid(tmp_path):
    # The dataset's hid was used to compose the file name during the export but it
    # can be missing sometimes. We now use the dataset's encoded id instead.
    app = _mock_app()
    u, history, d1, d2, j = _setup_simple_cat_job(app)

    # Remove hid from d1
    d1.hid = None
    app.commit()

    with store.DirectoryModelExportStore(tmp_path, app=app, export_files="copy") as export_store:
        export_store.export_history(history)


def test_export_history_to_ro_crate(tmp_path):
    app = _mock_app()
    u, history, d1, d2, j = _setup_simple_cat_job(app)

    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_history(history)
    validate_history_crate_directory(tmp_path)


def test_export_invocation_to_ro_crate(tmp_path):
    app = _mock_app()
    workflow_invocation = _setup_invocation(app)
    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_workflow_invocation(workflow_invocation)
    validate_invocation_crate_directory(tmp_path)


def test_export_simple_invocation_to_ro_crate(tmp_path):
    app = _mock_app()
    workflow_invocation = _setup_simple_invocation(app)
    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_workflow_invocation(workflow_invocation)
    validate_invocation_crate_directory(tmp_path)


def test_export_collection_invocation_to_ro_crate(tmp_path):
    app = _mock_app()
    workflow_invocation = _setup_collection_invocation(app)
    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_workflow_invocation(workflow_invocation)
    validate_invocation_collection_crate_directory(tmp_path)


def test_export_invocation_to_ro_crate_archive(tmp_path):
    app = _mock_app()
    workflow_invocation = _setup_invocation(app)

    crate_zip = tmp_path / "crate.zip"
    with store.ROCrateArchiveModelExportStore(crate_zip, app=app, export_files="symlink") as export_store:
        export_store.export_workflow_invocation(workflow_invocation)
    with CompressedFile(crate_zip) as compressed_file:
        assert compressed_file.file_type == "zip"
        compressed_file.extract(tmp_path)
    crate_directory = tmp_path / "crate"
    validate_invocation_crate_directory(crate_directory)


def test_finalize_job_state():
    """Verify jobs are given finalized states on import."""
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": False})
    u = h.user

    with open(os.path.join(temp_directory, store.ATTRS_FILENAME_JOBS)) as f:
        job_attrs = json.load(f)

    for job in job_attrs:
        job["state"] = "queued"

    with open(os.path.join(temp_directory, store.ATTRS_FILENAME_JOBS), "w") as f:
        json.dump(job_attrs, f)

    _perform_import_from_directory(temp_directory, app, u, import_history)

    datasets = import_history.datasets
    assert len(datasets) == 2
    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.state == model.Job.states.ERROR


def test_import_traceback_handling():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": False})
    u = h.user
    traceback_message = "Oh no, a traceback here!!!"

    with open(os.path.join(temp_directory, store.TRACEBACK), "w") as f:
        f.write(traceback_message)

    with pytest.raises(store.FileTracebackException) as exc:
        _perform_import_from_directory(temp_directory, app, u, import_history)
    assert exc.value.traceback == traceback_message


def test_import_export_edit_datasets():
    """Test modifying existing HDA and dataset metadata with import."""
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    u = h.user

    # Fabric editing metadata...
    datasets_metadata_path = os.path.join(temp_directory, store.ATTRS_FILENAME_DATASETS)
    with open(datasets_metadata_path) as f:
        datasets_metadata = json.load(f)

    datasets_metadata[0]["name"] = "my new name 0"
    datasets_metadata[1]["name"] = "my new name 1"

    assert "dataset" in datasets_metadata[0]
    datasets_metadata[0]["dataset"]["object_store_id"] = "foo1"

    with open(datasets_metadata_path, "w") as f:
        json.dump(datasets_metadata, f)

    _perform_import_from_directory(temp_directory, app, u, import_history, store.ImportOptions(allow_edit=True))

    datasets = import_history.datasets
    assert len(datasets) == 0

    d1 = h.datasets[0]
    d2 = h.datasets[1]

    assert d1.name == "my new name 0", d1.name
    assert d2.name == "my new name 1", d2.name
    assert d1.dataset.object_store_id == "foo1", d1.dataset.object_store_id


def test_import_export_edit_collection(tmp_path):
    """Test modifying existing collections with imports."""
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    c1 = model.DatasetCollection(collection_type="list", populated=False)
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=1, collection=c1, name="HistoryCollectionTest1")

    sa_session.add(hc1)
    sa_session.add(h)
    import_history = model.History(name="Test History for Import", user=u)
    app.add_and_commit(import_history)

    with store.DirectoryModelExportStore(tmp_path, app=app, for_edit=True) as export_store:
        export_store.add_dataset_collection(hc1)

    # Fabric editing metadata for collection...
    collections_metadata_path = os.path.join(tmp_path, store.ATTRS_FILENAME_COLLECTIONS)
    datasets_metadata_path = os.path.join(tmp_path, store.ATTRS_FILENAME_DATASETS)
    with open(collections_metadata_path) as f:
        hdcas_metadata = json.load(f)

    assert len(hdcas_metadata) == 1
    hdca_metadata = hdcas_metadata[0]
    assert hdca_metadata
    assert "id" in hdca_metadata
    assert "collection" in hdca_metadata
    collection_metadata = hdca_metadata["collection"]
    assert "populated_state" in collection_metadata
    assert collection_metadata["populated_state"] == model.DatasetCollection.populated_states.NEW

    collection_metadata["populated_state"] = model.DatasetCollection.populated_states.OK

    d1 = model.HistoryDatasetAssociation(extension="txt", create_dataset=True, flush=False)
    d1.hid = 1
    d2 = model.HistoryDatasetAssociation(extension="txt", create_dataset=True, flush=False)
    d2.hid = 2
    serialization_options = model.SerializationOptions(for_edit=True)
    dataset_list = [
        d1.serialize(app.security, serialization_options),
        d2.serialize(app.security, serialization_options),
    ]

    dc = model.DatasetCollection(
        id=collection_metadata["id"],
        collection_type="list",
        element_count=2,
    )
    dc.populated_state = model.DatasetCollection.populated_states.OK
    dce1 = model.DatasetCollectionElement(
        element=d1,
        element_index=0,
        element_identifier="first",
    )
    dce2 = model.DatasetCollectionElement(
        element=d2,
        element_index=1,
        element_identifier="second",
    )
    dc.elements = [dce1, dce2]
    with open(datasets_metadata_path, "w") as datasets_f:
        json.dump(dataset_list, datasets_f)

    hdca_metadata["collection"] = dc.serialize(app.security, serialization_options)
    with open(collections_metadata_path, "w") as collections_f:
        json.dump(hdcas_metadata, collections_f)

    _perform_import_from_directory(tmp_path, app, u, import_history, store.ImportOptions(allow_edit=True))

    sa_session.refresh(c1)
    assert c1.populated_state == model.DatasetCollection.populated_states.OK, c1.populated_state
    assert len(c1.elements) == 2


def test_import_export_composite_datasets(tmp_path):
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    d1 = _create_datasets(sa_session, h, 1, extension="html")[0]
    d1.dataset.create_extra_files_path()
    app.add_and_commit(h, d1)

    app.write_primary_file(d1, "cool primary file")
    app.write_composite_file(d1, "cool composite file", "child_file")

    with store.DirectoryModelExportStore(tmp_path, app=app, export_files="copy") as export_store:
        export_store.add_dataset(d1)

    import_history = model.History(name="Test History for Import", user=u)
    app.add_and_commit(import_history)
    _perform_import_from_directory(tmp_path, app, u, import_history)
    assert len(import_history.datasets) == 1
    import_dataset = import_history.datasets[0]
    _assert_extra_files_has_parent_directory_with_single_file_containing(
        import_dataset, "child_file", "cool composite file"
    )


def _assert_extra_files_has_parent_directory_with_single_file_containing(
    dataset, expected_file_name, expected_contents
):
    root_extra_files_path = dataset.extra_files_path
    assert len(os.listdir(root_extra_files_path)) == 1
    assert os.listdir(root_extra_files_path)[0] == "parent_dir"
    composite_sub_dir = os.path.join(root_extra_files_path, "parent_dir")
    child_files = os.listdir(composite_sub_dir)
    assert len(child_files) == 1
    assert child_files[0] == expected_file_name
    with open(os.path.join(composite_sub_dir, child_files[0])) as f:
        contents = f.read()
        assert contents == expected_contents


def test_edit_metadata_files(tmp_path):
    app = _mock_app(store_by="uuid")
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    d1 = _create_datasets(sa_session, h, 1, extension="bam")[0]
    app.add_and_commit(h, d1)
    index = NamedTemporaryFile("w")
    index.write("cool bam index")
    metadata_dict = {"bam_index": MetadataTempFile.from_JSON({"kwds": {}, "filename": index.name})}
    d1.metadata.from_JSON_dict(json_dict=metadata_dict)
    assert d1.metadata.bam_index
    assert isinstance(d1.metadata.bam_index, model.MetadataFile)

    with store.DirectoryModelExportStore(tmp_path, app=app, for_edit=True, strip_metadata_files=False) as export_store:
        export_store.add_dataset(d1)

    import_history = model.History(name="Test History for Import", user=u)
    app.add_and_commit(import_history)
    _perform_import_from_directory(tmp_path, app, u, import_history, store.ImportOptions(allow_edit=True))


def test_sessionless_import_edit_datasets():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    # Create a model store without a session and import it.
    import_model_store = store.get_import_model_store_for_directory(
        temp_directory, import_options=store.ImportOptions(allow_dataset_object_edit=True, allow_edit=True)
    )
    import_model_store.perform_import()
    # Not using app.sa_session but a session mock that has a query/find pattern emulating usage
    # of real sa_session.
    d1 = import_model_store.sa_session.query(model.HistoryDatasetAssociation).find(h.datasets[0].id)
    d2 = import_model_store.sa_session.query(model.HistoryDatasetAssociation).find(h.datasets[1].id)
    assert d1 is not None
    assert d2 is not None


def test_import_job_with_output_copy():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    hda = h.active_datasets[-1]
    # Simulate a copy being made of an output hda
    copy = hda.copy(new_name="output copy")
    # set extension to auto, should be changed to real extension when finalizing job
    copy.extension = "auto"
    app.add_and_commit(copy)
    import_model_store = store.get_import_model_store_for_directory(
        temp_directory, import_options=store.ImportOptions(allow_dataset_object_edit=True, allow_edit=True), app=app
    )
    import_model_store.perform_import()
    assert copy.extension == "txt"


def test_import_datasets_with_ids_fails_if_not_editing_models():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    u = h.user

    caught = None
    try:
        _perform_import_from_directory(temp_directory, app, u, import_history, store.ImportOptions(allow_edit=False))
    except AssertionError as e:
        # TODO: catch a better exception
        caught = e
    assert caught


def _setup_simple_export(export_kwds):
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    import_history = model.History(name="Test History for Import", user=u)
    app.add_and_commit(import_history)

    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, app=app, **export_kwds) as export_store:
        export_store.add_dataset(d1)
        export_store.add_dataset(d2)

    return app, h, temp_directory, import_history


def _assert_simple_cat_job_imported(imported_history, state="ok"):
    assert imported_history.name == "imported from archive: Test History"

    datasets = imported_history.datasets
    assert len(datasets) == 2
    assert datasets[0].state == datasets[1].state == state
    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.state == state
    assert imported_job.output_datasets
    assert imported_job.output_datasets[0].dataset == datasets[1]

    assert imported_job.input_datasets
    assert imported_job.input_datasets[0].dataset == datasets[0]

    with open(datasets[0].get_file_name()) as f:
        assert f.read().startswith("chr1    4225    19670")
    with open(datasets[1].get_file_name()) as f:
        assert f.read().startswith("chr1\t147962192\t147962580\tNM_005997_cds_0_0_chr1_147962193_r\t0\t-")


def _setup_simple_cat_job(app, state="ok"):
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    d1, d2 = _create_datasets(sa_session, h, 2)
    d1.state = d2.state = state

    j = model.Job()
    j.user = u
    j.tool_id = "cat1"
    j.state = state

    j.add_input_dataset("input1", d1)
    j.add_output_dataset("out_file1", d2)

    app.add_and_commit(d1, d2, h, j)

    app.object_store.update_from_file(d1, file_name=TEST_PATH_1, create=True)
    app.object_store.update_from_file(d2, file_name=TEST_PATH_2, create=True)

    return u, h, d1, d2, j


def _setup_invocation(app):
    sa_session = app.model.context

    u, h, d1, d2, j = _setup_simple_cat_job(app)
    j.parameters = [model.JobParameter(name="index_path", value='"/old/path/human"')]

    workflow_step_1 = model.WorkflowStep()
    workflow_step_1.order_index = 0
    workflow_step_1.type = "data_input"
    sa_session.add(workflow_step_1)
    workflow_1 = _workflow_from_steps(u, [workflow_step_1])
    workflow_1.license = "MIT"
    workflow_1.name = "Test Workflow"
    sa_session.add(workflow_1)
    workflow_invocation = _invocation_for_workflow(u, workflow_1)
    invocation_step = model.WorkflowInvocationStep()
    invocation_step.workflow_step = workflow_step_1
    invocation_step.job = j
    sa_session.add(invocation_step)
    output_assoc = model.WorkflowInvocationStepOutputDatasetAssociation()
    output_assoc.dataset = d2
    invocation_step.output_datasets = [output_assoc]
    workflow_invocation.steps = [invocation_step]
    workflow_invocation.user = u
    workflow_invocation.add_input(d1, step=workflow_step_1)
    wf_output = model.WorkflowOutput(workflow_step_1, label="output_label")
    workflow_invocation.add_output(wf_output, workflow_step_1, d2)
    app.add_and_commit(workflow_invocation)
    return workflow_invocation


def _setup_simple_collection_job(app, state="ok"):
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    d1, d2, d3, d4 = _create_datasets(sa_session, h, 4)

    c1 = model.DatasetCollection(collection_type="list")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=1, collection=c1, name="HistoryCollectionTest1")
    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)

    c2 = model.DatasetCollection(collection_type="list")
    hc2 = model.HistoryDatasetCollectionAssociation(history=h, hid=2, collection=c2, name="HistoryCollectionTest2")
    dce3 = model.DatasetCollectionElement(collection=c2, element=d1, element_identifier="forward", element_index=0)
    dce4 = model.DatasetCollectionElement(collection=c2, element=d3, element_identifier="reverse", element_index=1)

    c3 = model.DatasetCollection(collection_type="list")
    hc3 = model.HistoryDatasetCollectionAssociation(history=h, hid=3, collection=c3, name="HistoryCollectionTest3")
    dce5 = model.DatasetCollectionElement(collection=c3, element=d4, element_identifier="out", element_index=0)

    j = model.Job()
    j.user = h.user
    j.tool_id = "cat1"
    j.add_input_dataset("input1", d1)
    j.add_input_dataset("input2", d2)
    j.add_input_dataset("input3", d3)
    j.add_output_dataset("out_file1", d4)
    j.add_input_dataset_collection("input1_collect", hc1)
    j.add_input_dataset_collection("input2_collect", hc2)
    j.add_output_dataset_collection("output", hc3)

    sa_session.add(dce1)
    sa_session.add(dce2)
    sa_session.add(dce3)
    sa_session.add(dce4)
    sa_session.add(dce5)
    sa_session.add(hc1)
    sa_session.add(hc2)
    sa_session.add(hc3)
    sa_session.add(j)
    app.commit()

    return u, h, c1, c2, c3, hc1, hc2, hc3, j


def _setup_collection_invocation(app):
    sa_session = app.model.context

    u, h, c1, c2, c3, hc1, hc2, hc3, j = _setup_simple_collection_job(app)

    workflow_step_1 = model.WorkflowStep()
    workflow_step_1.order_index = 0
    workflow_step_1.type = "data_collection_input"
    workflow_step_1.tool_inputs = {}
    sa_session.add(workflow_step_1)
    workflow_1 = _workflow_from_steps(u, [workflow_step_1])
    workflow_1.license = "MIT"
    workflow_1.name = "Test Workflow"
    sa_session.add(workflow_1)
    workflow_invocation = _invocation_for_workflow(u, workflow_1)
    workflow_invocation.user = u
    workflow_invocation.add_input(hc1, step=workflow_step_1)
    workflow_invocation.add_input(hc2, step=workflow_step_1)
    wf_output = model.WorkflowOutput(workflow_step_1, label="output_label")
    workflow_invocation.add_output(wf_output, workflow_step_1, hc3)

    app.add_and_commit(workflow_invocation)
    return workflow_invocation


def _setup_simple_invocation(app):
    sa_session = app.model.context

    u, h, d1, d2, j = _setup_simple_cat_job(app)
    j.parameters = [model.JobParameter(name="index_path", value='"/old/path/human"')]

    workflow_step_1 = model.WorkflowStep()
    workflow_step_1.order_index = 0
    workflow_step_1.type = "data_input"
    workflow_step_1.tool_inputs = {}
    sa_session.add(workflow_step_1)
    workflow = _workflow_from_steps(u, [workflow_step_1])
    workflow.license = "MIT"
    workflow.name = "Test Workflow"
    workflow.create_time = now()
    workflow.update_time = now()
    sa_session.add(workflow)
    invocation = _invocation_for_workflow(u, workflow)
    invocation.create_time = now()
    invocation.update_time = now()

    invocation.add_input(d1, step=workflow_step_1)
    wf_output = model.WorkflowOutput(workflow_step_1, label="output_label")
    invocation.add_output(wf_output, workflow_step_1, d2)
    return invocation


def _import_export_history(app, h, dest_export=None, export_files=None, import_options=None, include_hidden=False):
    if dest_export is None:
        dest_parent = mkdtemp()
        dest_export = os.path.join(dest_parent, "moo.tgz")

    with store.TarModelExportStore(dest_export, app=app, export_files=export_files) as export_store:
        export_store.export_history(h, include_hidden=include_hidden)

    imported_history = import_archive(dest_export, app, h.user, import_options=import_options)
    assert imported_history
    return imported_history


def _perform_import_from_directory(directory, app, user, import_history, import_options=None):
    import_model_store = store.get_import_model_store_for_directory(
        directory, app=app, user=user, import_options=import_options
    )
    with import_model_store.target_history(default_history=import_history):
        import_model_store.perform_import(import_history)


def _create_datasets(sa_session, history, n, extension="txt"):
    return [
        model.HistoryDatasetAssociation(
            extension=extension, history=history, create_dataset=True, sa_session=sa_session, hid=i + 1
        )
        for i in range(n)
    ]


class MockWorkflowContentsManager:
    def store_workflow_artifacts(self, directory, workflow_key, workflow, **kwd):
        path = os.path.join(directory, f"{workflow_key}.gxwf.yml")
        with open(path, "w") as f:
            f.write("MY COOL WORKFLOW!!!")
        path = os.path.join(directory, f"{workflow_key}.abstract.cwl")
        with open(path, "w") as f:
            f.write("MY COOL WORKFLOW as CWL!!!")

    def read_workflow_from_path(self, app, user, path, allow_in_directory=None):
        stored_workflow = model.StoredWorkflow()
        stored_workflow.user = user
        workflow_step_1 = model.WorkflowStep()
        workflow_step_1.order_index = 0
        workflow_step_1.type = "data_input"
        workflow = model.Workflow()
        workflow.steps = [workflow_step_1]
        stored_workflow.latest_workflow = workflow
        app.add_and_commit(stored_workflow, workflow)
        return workflow


class TestApp(GalaxyDataTestApp):
    workflow_contents_manager = MockWorkflowContentsManager()

    def add_and_commit(self, *objs):
        session = self.model.session
        session.add_all(objs)
        self.commit()

    def commit(self):
        session = self.model.session
        session.commit()

    def write_primary_file(self, dataset_instance, contents):
        primary = NamedTemporaryFile("w")
        primary.write(contents)
        primary.flush()
        self.object_store.update_from_file(
            dataset_instance.dataset, file_name=primary.name, create=True, preserve_symlinks=True
        )

    def write_composite_file(self, dataset_instance, contents, file_name):
        composite1 = NamedTemporaryFile("w")
        composite1.write(contents)
        composite1.flush()

        dataset_instance.dataset.create_extra_files_path()
        self.object_store.update_from_file(
            dataset_instance.dataset,
            extra_dir=os.path.normpath(os.path.join(dataset_instance.extra_files_path, "parent_dir")),
            alt_name=file_name,
            file_name=composite1.name,
            create=True,
            preserve_symlinks=True,
        )


class MockTool:
    """Mock class to simulate Galaxy tools with essential metadata for testing."""

    def __init__(self, tool_id):
        self.tool_id = tool_id
        self.citations = [{"type": "doi", "value": "10.1234/example.doi"}]
        self.xrefs = [{"type": "registry", "value": "tool_registry_id"}]
        self.edam_operations = ["operation_1234"]


class MockToolbox:
    """Mock class for the Galaxy toolbox, which returns tools based on their IDs."""

    def get_tool(self, tool_id):
        # Returns a MockTool object with basic metadata for testing
        return MockTool(tool_id)


def _mock_app(store_by=DEFAULT_OBJECT_STORE_BY):
    app = TestApp()
    test_object_store_config = TestConfig(store_by=store_by)
    app.object_store = test_object_store_config.object_store
    app.model.Dataset.object_store = app.object_store

    # Add a mocked toolbox attribute for tests requiring tool metadata
    app.toolbox = MockToolbox()

    return app


class StoreFixtureContextWithUser(NamedTuple):
    app: TestApp
    sa_session: scoped_session
    user: model.User


def setup_fixture_context_with_user(
    user_email="test@example.com", store_by=DEFAULT_OBJECT_STORE_BY
) -> StoreFixtureContextWithUser:
    app = _mock_app(store_by=store_by)
    sa_session = app.model.context
    user = model.User(email=user_email, password="password")
    return StoreFixtureContextWithUser(app=app, sa_session=sa_session, user=user)


class StoreFixtureContextWithHistory(NamedTuple):
    app: TestApp
    sa_session: scoped_session
    user: model.User
    history: model.History


def setup_fixture_context_with_history(
    history_name="Test History for Model Store", **kwd
) -> StoreFixtureContextWithHistory:
    app, sa_session, user = setup_fixture_context_with_user(**kwd)
    history = model.History(name=history_name, user=user)
    sa_session.add(history)
    app.commit()
    return StoreFixtureContextWithHistory(app, sa_session, user, history)


def perform_import_from_store_dict(
    fixture_context: StoreFixtureContextWithHistory,
    import_dict: Dict[str, Any],
    import_options: Optional[store.ImportOptions] = None,
) -> None:
    import_options = import_options or store.ImportOptions()
    import_model_store = store.get_import_model_store_for_dict(
        import_dict, app=fixture_context.app, user=fixture_context.user, import_options=import_options
    )
    with import_model_store.target_history(default_history=fixture_context.history):
        import_model_store.perform_import(fixture_context.history)


class Options:
    is_url = False
    is_file = True
    is_b64encoded = False


def import_archive(archive_path, app, user, import_options=None):
    dest_parent = mkdtemp()
    with CompressedFile(archive_path) as cf:
        dest_dir = cf.extract(dest_parent)

    import_options = import_options or store.ImportOptions()
    model_store = store.get_import_model_store_for_directory(
        dest_dir,
        app=app,
        user=user,
        import_options=import_options,
    )
    with model_store.target_history(default_history=None) as new_history:
        model_store.perform_import(new_history)

    shutil.rmtree(dest_parent)

    return new_history
