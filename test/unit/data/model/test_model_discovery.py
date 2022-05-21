import os
from tempfile import mkdtemp

from galaxy import model
from galaxy.model import store
from galaxy.model.store.discover import persist_target_to_export_store
from galaxy.model.unittest_utils import GalaxyDataTestApp


def test_model_create_context_persist_hdas():
    work_directory = mkdtemp()
    with open(os.path.join(work_directory, "file1.txt"), "w") as f:
        f.write("hello world\nhello world line 2")
    target = {
        "destination": {
            "type": "hdas",
        },
        "elements": [
            {
                "filename": "file1.txt",
                "ext": "txt",
                "dbkey": "hg19",
                "name": "my file",
                "md5": "e5d21b1ea57fc9a31f8ea0110531bf3d",
                "tags": ["name:value"],
            }
        ],
    }
    app = _mock_app()
    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, serialize_dataset_objects=True) as export_store:
        persist_target_to_export_store(target, export_store, app.object_store, work_directory)

    import_history = _import_directory_to_history(app, temp_directory, work_directory)

    assert len(import_history.datasets) == 1
    imported_hda = import_history.datasets[0]
    assert imported_hda.ext == "txt"
    assert imported_hda.name == "my file"
    assert imported_hda.metadata.data_lines == 2
    assert len(imported_hda.dataset.hashes) == 1
    assert imported_hda.dataset.hashes[0].hash_value == "e5d21b1ea57fc9a31f8ea0110531bf3d"
    tags = imported_hda.tags
    assert len(tags) == 1
    assert tags[0].value == "value"

    with open(imported_hda.file_name) as f:
        assert f.read().startswith("hello world\n")


def test_model_create_context_persist_error_hda():
    work_directory = mkdtemp()
    with open(os.path.join(work_directory, "file1.txt"), "w") as f:
        f.write("hello world\nhello world line 2")
    target = {
        "destination": {
            "type": "hdas",
        },
        "elements": [
            {
                "error_message": "Failed to download some URL I guess",
            }
        ],
    }
    app = _mock_app()
    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, serialize_dataset_objects=True) as export_store:
        persist_target_to_export_store(target, export_store, app.object_store, work_directory)

    import_history = _import_directory_to_history(app, temp_directory, work_directory)

    assert len(import_history.datasets) == 1
    imported_hda = import_history.datasets[0]
    assert imported_hda.state == "error"
    assert imported_hda.info == "Failed to download some URL I guess"


def test_persist_target_library_dataset():
    work_directory = mkdtemp()
    with open(os.path.join(work_directory, "file1.txt"), "w") as f:
        f.write("hello world\nhello world line 2")
    target = {
        "destination": {
            "type": "library",
            "name": "Example Library",
            "description": "Example Library Description",
            "synopsis": "Example Library Synopsis",
        },
        "elements": [
            {
                "filename": "file1.txt",
                "ext": "txt",
                "dbkey": "hg19",
                "name": "my file",
            }
        ],
    }
    sa_session = _import_library_target(target, work_directory)
    new_library = _assert_one_library_created(sa_session)

    assert new_library.name == "Example Library"
    assert new_library.description == "Example Library Description"
    assert new_library.synopsis == "Example Library Synopsis"

    new_root = new_library.root_folder
    assert new_root
    assert new_root.name == "Example Library"

    assert len(new_root.datasets) == 1
    ldda = new_root.datasets[0].library_dataset_dataset_association
    assert ldda.metadata.data_lines == 2
    with open(ldda.file_name) as f:
        assert f.read().startswith("hello world\n")


def test_persist_target_library_folder():
    work_directory = mkdtemp()
    with open(os.path.join(work_directory, "file1.txt"), "w") as f:
        f.write("hello world\nhello world line 2")
    target = {
        "destination": {
            "type": "library",
            "name": "Example Library",
            "description": "Example Library Description",
            "synopsis": "Example Library Synopsis",
        },
        "items": [
            {
                "name": "Folder 1",
                "description": "Folder 1 Description",
                "items": [
                    {
                        "filename": "file1.txt",
                        "ext": "txt",
                        "dbkey": "hg19",
                        "info": "dataset info",
                        "name": "my file",
                    }
                ],
            }
        ],
    }
    sa_session = _import_library_target(target, work_directory)
    new_library = _assert_one_library_created(sa_session)
    new_root = new_library.root_folder
    assert len(new_root.datasets) == 0
    assert len(new_root.folders) == 1

    child_folder = new_root.folders[0]
    assert child_folder.name == "Folder 1"
    assert child_folder.description == "Folder 1 Description"
    assert len(child_folder.folders) == 0
    assert len(child_folder.datasets) == 1
    ldda = child_folder.datasets[0].library_dataset_dataset_association
    assert ldda.metadata.data_lines == 2
    with open(ldda.file_name) as f:
        assert f.read().startswith("hello world\n")


def test_persist_target_hdca():
    work_directory = mkdtemp()
    with open(os.path.join(work_directory, "file1.txt"), "w") as f:
        f.write("hello world\nhello world line 2")
    with open(os.path.join(work_directory, "file2.txt"), "w") as f:
        f.write("file 2 contents")

    target = {
        "destination": {
            "type": "hdca",
        },
        "name": "My HDCA",
        "collection_type": "list",
        "elements": [
            {
                "filename": "file1.txt",
                "ext": "txt",
                "dbkey": "hg19",
                "info": "dataset info",
                "name": "my file",
            },
            {
                "filename": "file2.txt",
                "ext": "txt",
                "dbkey": "hg18",
                "info": "dataset info 2",
                "name": "my file 2",
            },
        ],
    }

    app = _mock_app()
    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, serialize_dataset_objects=True) as export_store:
        persist_target_to_export_store(target, export_store, app.object_store, work_directory)

    import_history = _import_directory_to_history(app, temp_directory, work_directory)
    assert len(import_history.dataset_collections) == 1
    assert len(import_history.datasets) == 2

    import_hdca = import_history.dataset_collections[0]
    datasets = import_hdca.dataset_instances
    assert len(datasets) == 2
    dataset0 = datasets[0]
    dataset1 = datasets[1]

    with open(dataset0.file_name) as f:
        assert f.read().startswith("hello world\n")
    with open(dataset1.file_name) as f:
        assert f.read().startswith("file 2 contents")


def _assert_one_library_created(sa_session):
    all_libraries = sa_session.query(model.Library).all()
    assert len(all_libraries) == 1, len(all_libraries)
    new_library = all_libraries[0]
    return new_library


def _import_library_target(target, work_directory):
    app = _mock_app()
    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, app=app, serialize_dataset_objects=True) as export_store:
        persist_target_to_export_store(target, export_store, app.object_store, work_directory)

    u = model.User(email="library@example.com", password="password")

    import_options = store.ImportOptions(allow_dataset_object_edit=True, allow_library_creation=True)
    import_model_store = store.get_import_model_store_for_directory(
        temp_directory, app=app, user=u, import_options=import_options
    )
    import_model_store.perform_import()

    sa_session = app.model.context
    return sa_session


def _import_directory_to_history(app, target, work_directory):
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    import_history = model.History(name="Test History for Import", user=u)

    sa_session = app.model.context
    sa_session.add_all([u, import_history])
    sa_session.flush()

    assert len(import_history.datasets) == 0

    import_options = store.ImportOptions(allow_dataset_object_edit=True)
    import_model_store = store.get_import_model_store_for_directory(
        target, app=app, user=u, import_options=import_options, tag_handler=app.tag_handler.create_tag_handler_session()
    )
    with import_model_store.target_history(default_history=import_history):
        import_model_store.perform_import(import_history)

    return import_history


def _mock_app():
    return GalaxyDataTestApp()
