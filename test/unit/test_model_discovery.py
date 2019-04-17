import os
from tempfile import mkdtemp

from galaxy import model
from galaxy.model import store
from galaxy.model.store.discover import persist_target_to_export_store
from .tools.test_history_imp_exp import _mock_app


def test_model_create_context_persist_hdas():
    work_directory = mkdtemp()
    with open(os.path.join(work_directory, "file1.txt"), "w") as f:
        f.write("hello world\nhello world line 2")
    target = {
        "destination": {
            "type": "hdas",
        },
        "elements": [{
            "filename": "file1.txt",
            "ext": "txt",
            "dbkey": "hg19",
            "name": "my file",
            "md5": "e5d21b1ea57fc9a31f8ea0110531bf3d",
        }],
    }
    app = _mock_app(store_by="uuid")
    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, serialize_dataset_objects=True) as export_store:
        persist_target_to_export_store(target, export_store, app.object_store, work_directory)

    u = model.User(email="collection@example.com", password="password")
    import_history = model.History(name="Test History for Import", user=u)

    sa_session = app.model.context
    sa_session.add(u)
    sa_session.add(import_history)
    sa_session.flush()

    assert len(import_history.datasets) == 0

    import_options = store.ImportOptions(allow_dataset_object_edit=True)
    import_model_store = store.get_import_model_store_for_directory(temp_directory, app=app, user=u, import_options=import_options)
    with import_model_store.target_history(default_history=import_history):
        import_model_store.perform_import(import_history)

    assert len(import_history.datasets) == 1
    imported_hda = import_history.datasets[0]
    assert imported_hda.ext == "txt"
    assert imported_hda.name == "my file"
    assert imported_hda.metadata.data_lines == 2
    assert len(imported_hda.dataset.hashes) == 1
    assert imported_hda.dataset.hashes[0].hash_value == "e5d21b1ea57fc9a31f8ea0110531bf3d"

    with open(imported_hda.file_name, "r") as f:
        assert f.read().startswith("hello world\n")


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
        "elements": [{
            "filename": "file1.txt",
            "ext": "txt",
            "dbkey": "hg19",
            "name": "my file",
        }],
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
    with open(ldda.file_name, "r") as f:
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
        "items": [{
            "name": "Folder 1",
            "description": "Folder 1 Description",
            "items": [{
                "filename": "file1.txt",
                "ext": "txt",
                "dbkey": "hg19",
                "info": "dataset info",
                "name": "my file",
            }]
        }],
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
    with open(ldda.file_name, "r") as f:
        assert f.read().startswith("hello world\n")


def _assert_one_library_created(sa_session):
    all_libraries = sa_session.query(model.Library).all()
    assert len(all_libraries) == 1, len(all_libraries)
    new_library = all_libraries[0]
    return new_library


def _import_library_target(target, work_directory):
    app = _mock_app(store_by="uuid")
    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, app=app, serialize_dataset_objects=True) as export_store:
        persist_target_to_export_store(target, export_store, app.object_store, work_directory)

    u = model.User(email="library@example.com", password="password")

    import_options = store.ImportOptions(allow_dataset_object_edit=True, allow_library_creation=True)
    import_model_store = store.get_import_model_store_for_directory(temp_directory, app=app, user=u, import_options=import_options)
    import_model_store.perform_import()

    sa_session = app.model.context
    return sa_session
