import json
import os
import tarfile
import tempfile
from shutil import rmtree
from unittest.mock import Mock

from sqlalchemy import select

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.exceptions import MalformedContents
from galaxy.model.base import transaction
from galaxy.model.orm.util import add_object_to_object_session
from galaxy.objectstore.unittest_utils import Config as TestConfig
from galaxy.tools.imp_exp import (
    JobExportHistoryArchiveWrapper,
    JobImportHistoryArchiveWrapper,
    unpack_tar_gz_archive,
)
from galaxy.tools.imp_exp.export_history import create_archive
from galaxy.util import galaxy_directory

# good enough for the very specific tests we're writing as of now...
DATASETS_ATTRS = """[{{"info": "\\nuploaded txt file", "peek": "foo\\n\\n\\n\\n\\n\\n", "update_time": "2016-02-08 18:39:22.937474", "name": "Pasted Entry", "extension": "txt", "tags": {{}}, "__HistoryDatasetAssociation__": true, "file_name": "{file_name}", "deleted": false, "designation": null, "visible": true, "create_time": "2016-02-08 18:38:38.682087", "hid": 1, "parent_id": null, "extra_files_path": "", "uuid": "406d913e-925d-4ccd-800d-06c9b32df309", "metadata": {{"dbkey": "?", "data_lines": 1}}, "annotation": null, "blurb": "1 line", "exported": true}}]"""
DATASETS_ATTRS_EXPORT = """[{{"info": "\\nuploaded txt file", "peek": "foo\\n\\n\\n\\n\\n\\n", "update_time": "2016-02-08 18:39:22.937474", "name": "Pasted Entry", "extension": "txt", "tags": {{}}, "__HistoryDatasetAssociation__": true, "file_name": "{file_name}", "deleted": false, "designation": null, "visible": true, "create_time": "2016-02-08 18:38:38.682087", "hid": 1, "parent_id": null, "_extra_files_path": "", "uuid": "406d913e-925d-4ccd-800d-06c9b32df309", "metadata": {{"dbkey": "?", "data_lines": 1}}, "annotation": null, "blurb": "1 line"}}]"""
DATASETS_ATTRS_PROVENANCE = """[]"""
HISTORY_ATTRS = """{"hid_counter": 2, "update_time": "2016-02-08 18:38:38.705058", "create_time": "2016-02-08 18:38:20.790057", "name": "paste", "tags": {}, "genome_build": "?", "annotation": null}"""
JOBS_ATTRS = """[{"info": null, "tool_id": "upload1", "update_time": "2016-02-08T18:39:23.356482", "stdout": "", "input_mapping": {}, "tool_version": "1.1.4", "traceback": null, "command_line": "python /galaxy/tools/data_source/upload.py /galaxy /scratch/tmppwU9rD /scratch/tmpP4_45Y 1:/scratch/jobs/000/dataset_1_files:/data/000/dataset_1.dat", "exit_code": 0, "output_datasets": [1], "state": "ok", "create_time": "2016-02-08T18:38:39.153873", "params": {"files": [{"to_posix_lines": "Yes", "NAME": "None", "file_data": null, "space_to_tab": null, "url_paste": "/scratch/strio_url_paste_o6nrv8", "__index__": 0, "ftp_files": "", "uuid": "None"}], "paramfile": "/scratch/tmpP4_45Y", "file_type": "auto", "files_metadata": {"file_type": "auto", "__current_case__": 41}, "async_datasets": "None", "dbkey": "?"}, "stderr": ""}]"""


def t_data_path(name):
    return os.path.join(galaxy_directory(), "test-data", name)


def _run_jihaw_cleanup(archive_dir, app=None):
    app = app or _mock_app()
    job = model.Job()
    job.user = model.User(email="test@test.org", password="test")
    job.tool_stderr = ""
    jiha = model.JobImportHistoryArchive(job=job, archive_dir=archive_dir)
    app.model.context.current.add_all([job, jiha])
    session = app.model.context
    with transaction(session):
        session.commit()
    jihaw = JobImportHistoryArchiveWrapper(app, job.id)  # yeehaw!
    return app, jihaw.cleanup_after_job()


def _mock_app(store_by="id"):
    app = MockApp()
    test_object_store_config = TestConfig(store_by=store_by)
    app.object_store = test_object_store_config.object_store
    app.model.Dataset.object_store = app.object_store
    return app


def _run_jihaw_cleanup_check_secure(history_archive, msg):
    malformed = False
    try:
        _run_jihaw_cleanup(history_archive.arc_directory)
    except MalformedContents:
        malformed = True
    assert malformed


def test_create_archive():
    tempdir = tempfile.mkdtemp()
    with tempfile.NamedTemporaryFile() as temp:
        out_file = temp.name
        dataset = os.path.join(tempdir, "datasets/Pasted_Entry_1.txt")
        history_attrs_file = os.path.join(tempdir, "history_attrs.txt")
        datasets_attrs_file = os.path.join(tempdir, "datasets_attrs.txt")
        jobs_attrs_file = os.path.join(tempdir, "jobs_attrs.txt")
        os.makedirs(os.path.join(tempdir, "datasets"))
        with open(dataset, "w") as out:
            out.write("Hello\n")
        with open(history_attrs_file, "w") as out:
            out.write(HISTORY_ATTRS)
        with open(datasets_attrs_file, "w") as out:
            out.write(DATASETS_ATTRS_EXPORT.format(file_name=dataset))
        with open(jobs_attrs_file, "w") as out:
            out.write(JOBS_ATTRS)
        create_archive(tempdir, out_file, gzip=True)
        with tarfile.open(out_file) as t:
            assert sorted(t.getnames()) == sorted(
                ["datasets", "datasets/Pasted_Entry_1.txt", "history_attrs.txt", "datasets_attrs.txt", "jobs_attrs.txt"]
            ), t.getnames()


def test_history_import_symlink():
    """Ensure a history containing a dataset that is a symlink cannot be imported"""
    with HistoryArchive() as history_archive:
        history_archive.write_metafiles()
        history_archive.write_link("datasets/Pasted_Entry_1.txt", "../target.txt")
        history_archive.write_file("target.txt", "insecure")
        _run_jihaw_cleanup_check_secure(history_archive, "Symlink dataset in import archive allowed")


def test_history_import_relpath_in_metadata():
    """Ensure that dataset_attrs.txt cannot contain a relative path outside the archive"""
    with HistoryArchive() as history_archive:
        history_archive.write_metafiles(dataset_file_name="../outside.txt")
        history_archive.write_file("datasets/Pasted_Entry_1.txt", "foo")
        history_archive.write_outside()
        _run_jihaw_cleanup_check_secure(history_archive, "Relative parent path in datasets_attrs.txt allowed")


def test_history_import_abspath_in_metadata():
    """Ensure that dataset_attrs.txt cannot contain a absolute path outside the archive"""
    with HistoryArchive() as history_archive:
        history_archive.write_metafiles(dataset_file_name=os.path.join(history_archive.temp_directory, "outside.txt"))
        history_archive.write_file("datasets/Pasted_Entry_1.txt", "foo")
        history_archive.write_outside()
        _run_jihaw_cleanup_check_secure(history_archive, "Absolute path in datasets_attrs.txt allowed")


def test_export_dataset():
    app, sa_session, h = _setup_history_for_export("Datasets History")

    d1, d2 = _create_datasets(sa_session, h, 2)
    d1_hash = model.DatasetHash()
    d1_hash.hash_function = "MD5"
    d1_hash.hash_value = "foobar"
    d1.dataset.hashes.append(d1_hash)
    d1.dataset.created_from_basename = "my_cool_name.txt"
    d1_source = model.DatasetSource()
    d1_source.source_uri = "http://google.com/mycooldata.txt"
    d1.dataset.sources.append(d1_source)

    d1.state = d2.state = "ok"

    j = model.Job()
    j.user = h.user
    j.tool_id = "cat1"
    j.state = "ok"

    j.add_input_dataset("input1", d1)
    j.add_output_dataset("out_file1", d2)

    sa_session.add(d1)
    sa_session.add(d2)
    sa_session.add(h)
    sa_session.add(j)
    with transaction(sa_session):
        sa_session.commit()

    app.object_store.update_from_file(d1, file_name=t_data_path("1.txt"), create=True)
    app.object_store.update_from_file(d2, file_name=t_data_path("2.bed"), create=True)

    imported_history = _import_export(app, h)

    datasets = list(imported_history.contents_iter(types=["dataset"]))
    assert len(datasets) == 2
    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.output_datasets
    assert imported_job.output_datasets[0].dataset == datasets[1]

    assert imported_job.input_datasets
    assert imported_job.input_datasets[0].dataset == datasets[0]

    assert datasets[0].state == "ok"
    assert datasets[1].state == "ok"
    assert len(datasets[0].dataset.hashes) == 1
    dataset_hash = datasets[0].dataset.hashes[0]
    assert dataset_hash.hash_function == "MD5"
    assert dataset_hash.hash_value == "foobar"
    assert datasets[0].dataset.created_from_basename == "my_cool_name.txt"

    assert len(datasets[0].dataset.sources) == 1
    dataset_source = datasets[0].dataset.sources[0]
    assert dataset_source.source_uri == "http://google.com/mycooldata.txt"

    with open(datasets[0].get_file_name()) as f:
        assert f.read().startswith("chr1    4225    19670")
    with open(datasets[1].get_file_name()) as f:
        assert f.read().startswith("chr1\t147962192\t147962580\tNM_005997_cds_0_0_chr1_147962193_r\t0\t-")


def test_export_dataset_with_deleted_and_purged():
    app, sa_session, h = _setup_history_for_export("Datasets History with deleted")

    d1, d2 = _create_datasets(sa_session, h, 2)

    # Maybe use abstractions for deleting?
    d1.deleted = True
    d1.dataset.deleted = True
    d1.dataset.purged = False

    d2.deleted = True
    d2.dataset.deleted = True
    d2.dataset.purged = True

    j1 = model.Job()
    j1.user = h.user
    j1.tool_id = "cat1"

    j1.add_output_dataset("out_file1", d1)

    j2 = model.Job()
    j2.user = h.user
    j2.tool_id = "cat1"

    j2.add_output_dataset("out_file1", d2)

    sa_session.add(d1)
    sa_session.add(d2)
    sa_session.add(j1)
    sa_session.add(j2)
    sa_session.add(h)
    with transaction(sa_session):
        sa_session.commit()

    assert d1.deleted

    app.object_store.update_from_file(d1, file_name=t_data_path("1.txt"), create=True)
    app.object_store.update_from_file(d2, file_name=t_data_path("2.bed"), create=True)

    imported_history = _import_export(app, h)

    datasets = list(imported_history.contents_iter(types=["dataset"]))
    assert len(datasets) == 1

    assert datasets[0].state == "discarded"
    assert datasets[0].deleted
    assert datasets[0].dataset.deleted
    assert datasets[0].creating_job


def test_multi_inputs():
    app, sa_session, h = _setup_history_for_export("Datasets History")

    d1, d2, d3 = _create_datasets(sa_session, h, 3)

    j = model.Job()
    j.user = h.user
    j.tool_id = "cat_multi"

    # Emulate multiple data inputs into multi data input parameter...
    j.add_input_dataset("input1", d1)
    j.add_input_dataset("input11", d1)
    j.add_input_dataset("input12", d2)
    j.add_output_dataset("out_file1", d3)

    sa_session.add(d1)
    sa_session.add(d2)
    sa_session.add(d3)
    sa_session.add(h)
    sa_session.add(j)
    with transaction(sa_session):
        sa_session.commit()

    app.object_store.update_from_file(d1, file_name=t_data_path("1.txt"), create=True)
    app.object_store.update_from_file(d2, file_name=t_data_path("2.bed"), create=True)
    app.object_store.update_from_file(d3, file_name=t_data_path("4.bed"), create=True)

    imported_history = _import_export(app, h)

    datasets = list(imported_history.contents_iter(types=["dataset"]))
    assert len(datasets) == 3
    imported_job = datasets[2].creating_job
    assert imported_job
    assert imported_job.output_datasets
    assert imported_job.output_datasets[0].dataset.hid == 3
    assert imported_job.output_datasets[0].dataset == datasets[2]

    assert imported_job.input_datasets
    assert len(imported_job.input_datasets) == 3
    names = [d.name for d in imported_job.input_datasets]
    hids = [d.dataset.hid for d in imported_job.input_datasets]
    _assert_distinct(names)
    for name in ["input1", "input11", "input12"]:
        assert name in names
    for hid in [1, 2]:
        assert hid in hids

    with open(datasets[0].get_file_name()) as f:
        assert f.read().startswith("chr1    4225    19670")
    with open(datasets[1].get_file_name()) as f:
        assert f.read().startswith("chr1\t147962192\t147962580\tNM_005997_cds_0_0_chr1_147962193_r\t0\t-")


def test_export_collection_history():
    app, sa_session, h = _setup_history_for_export("Collection History")

    d1, d2, d3, d4 = _create_datasets(sa_session, h, 4)

    c1 = model.DatasetCollection(collection_type="paired")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=1, collection=c1, name="HistoryCollectionTest1")

    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)

    c2 = model.DatasetCollection(collection_type="list:paired")
    hc2 = model.HistoryDatasetCollectionAssociation(history=h, hid=2, collection=c2, name="HistoryCollectionTest2")

    cleaf = model.DatasetCollection(collection_type="paired")
    dce2leaf1 = model.DatasetCollectionElement(
        collection=cleaf, element=d3, element_identifier="forward", element_index=0
    )
    dce2leaf2 = model.DatasetCollectionElement(
        collection=cleaf, element=d4, element_identifier="reverse", element_index=1
    )

    dce21 = model.DatasetCollectionElement(collection=c2, element=cleaf, element_identifier="listel", element_index=0)

    j = model.Job()
    j.user = h.user
    j.tool_id = "cat1"
    j.add_input_dataset_collection("input1_collect", hc1)
    j.add_output_dataset_collection("output_collect", hc2)

    sa_session.add(dce1)
    sa_session.add(dce2)
    sa_session.add(dce21)
    sa_session.add(dce2leaf1)
    sa_session.add(dce2leaf2)
    sa_session.add(hc1)
    sa_session.add(hc2)
    sa_session.add(j)
    with transaction(sa_session):
        sa_session.commit()

    imported_history = _import_export(app, h)

    datasets = imported_history.datasets
    assert len(datasets) == 4

    dataset_collections = list(imported_history.contents_iter(types=["dataset_collection"]))
    assert len(dataset_collections) == 2

    imported_hdca1 = dataset_collections[0]
    imported_hdca2 = dataset_collections[1]

    imported_collection_2 = imported_hdca2.collection
    assert imported_hdca1.collection.collection_type == "paired"
    assert imported_collection_2.collection_type == "list:paired"

    assert len(imported_collection_2.elements) == 1
    imported_top_level_element = imported_collection_2.elements[0]
    assert imported_top_level_element.element_identifier == "listel", imported_top_level_element.element_identifier
    assert imported_top_level_element.element_index == 0, imported_top_level_element.element_index
    imported_nested_collection = imported_top_level_element.child_collection
    assert len(imported_nested_collection.elements) == 2
    assert imported_nested_collection.collection_type == "paired", imported_nested_collection.collection_type

    assert len(imported_history.jobs) == 1
    imported_job = imported_history.jobs[0]
    assert imported_job
    assert len(imported_job.input_dataset_collections) == 1, len(imported_job.input_dataset_collections)
    assert len(imported_job.output_dataset_collection_instances) == 1
    assert imported_job.id != j.id


def test_export_collection_with_mapping_history():
    app, sa_session, h = _setup_history_for_export("Collection Mapping History")

    d1, d2, d3, d4 = _create_datasets(sa_session, h, 4)

    c1 = model.DatasetCollection(collection_type="list")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=1, collection=c1, name="HistoryCollectionTest1")
    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="el1", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="el2", element_index=1)

    c2 = model.DatasetCollection(collection_type="list")
    hc2 = model.HistoryDatasetCollectionAssociation(history=h, hid=2, collection=c2, name="HistoryCollectionTest2")
    dce3 = model.DatasetCollectionElement(collection=c2, element=d3, element_identifier="el1", element_index=0)
    dce4 = model.DatasetCollectionElement(collection=c2, element=d4, element_identifier="el2", element_index=1)

    hc2.add_implicit_input_collection("input1", hc1)

    j1 = model.Job()
    j1.user = h.user
    j1.tool_id = "cat1"
    j1.add_input_dataset("input1", d1)
    j1.add_output_dataset("out_file1", d3)

    j2 = model.Job()
    j2.user = h.user
    j2.tool_id = "cat1"
    j2.add_input_dataset("input1", d2)
    j2.add_output_dataset("out_file1", d4)

    sa_session.add(dce1)
    sa_session.add(dce2)
    sa_session.add(dce3)
    sa_session.add(dce4)
    sa_session.add(hc1)
    sa_session.add(hc2)
    sa_session.add(j1)
    sa_session.add(j2)
    with transaction(sa_session):
        sa_session.commit()

    implicit_collection_jobs = model.ImplicitCollectionJobs()
    j1.add_output_dataset_collection("out_file1", hc2)  # really?
    ija1 = model.ImplicitCollectionJobsJobAssociation()
    ija1.order_index = 0
    ija1.implicit_collection_jobs = implicit_collection_jobs
    add_object_to_object_session(ija1, j1)
    ija1.job = j1

    j2.add_output_dataset_collection("out_file1", hc2)  # really?
    ija2 = model.ImplicitCollectionJobsJobAssociation()
    ija2.order_index = 1
    add_object_to_object_session(ija2, implicit_collection_jobs)
    ija2.implicit_collection_jobs = implicit_collection_jobs
    ija2.job = j2

    sa_session.add(implicit_collection_jobs)
    sa_session.add(ija1)
    sa_session.add(ija2)
    with transaction(sa_session):
        sa_session.commit()

    imported_history = _import_export(app, h)
    assert len(imported_history.jobs) == 2
    imported_job0 = imported_history.jobs[0]

    imported_icj = imported_job0.implicit_collection_jobs_association.implicit_collection_jobs
    assert imported_icj
    assert len(imported_icj.jobs) == 2, len(imported_icj.jobs)


def test_export_collection_with_datasets_from_other_history():
    app, sa_session, h = _setup_history_for_export("Collection History with dataset from other history")

    dataset_history = model.History(name="Dataset History", user=h.user)

    d1, d2 = _create_datasets(sa_session, dataset_history, 2)

    c1 = model.DatasetCollection(collection_type="paired")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=1, collection=c1, name="HistoryCollectionTest1")
    h.hid_counter = 2
    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)

    sa_session.add(dce1)
    sa_session.add(dce2)
    sa_session.add(d1)
    sa_session.add(d2)
    sa_session.add(hc1)
    with transaction(sa_session):
        sa_session.commit()

    imported_history = _import_export(app, h)

    assert imported_history.hid_counter == 4, imported_history.hid_counter
    assert len(imported_history.dataset_collections) == 1
    assert len(imported_history.datasets) == 2
    for hdca in imported_history.dataset_collections:
        assert hdca.hid == 1, hdca.hid
    for hda in imported_history.datasets:
        assert hda.hid in [2, 3]
    _assert_distinct_hids(imported_history)


def test_export_collection_with_copied_datasets_and_overlapping_hids():
    app, sa_session, h = _setup_history_for_export("Collection History with dataset from other history")

    dataset_history = model.History(name="Dataset History", user=h.user)

    d1, d2 = _create_datasets(sa_session, dataset_history, 2)

    sa_session.add(d1)
    sa_session.add(d2)
    sa_session.add(dataset_history)
    with transaction(sa_session):
        sa_session.commit()

    app.object_store.update_from_file(d1, file_name=t_data_path("1.txt"), create=True)
    app.object_store.update_from_file(d2, file_name=t_data_path("2.bed"), create=True)

    d1_copy = d1.copy()
    d2_copy = d2.copy()

    d1_copy.history = h
    d2_copy.history = h

    c1 = model.DatasetCollection(collection_type="paired")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=3, collection=c1, name="HistoryCollectionTest1")
    h.hid_counter = 5
    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)

    sa_session.add(dce1)
    sa_session.add(dce2)
    sa_session.add(d1_copy)
    sa_session.add(d2_copy)
    sa_session.add(hc1)
    with transaction(sa_session):
        sa_session.commit()

    _import_export(app, h)
    # Currently d1 and d1_copy would have conflicting paths in the tar file... this test verifies at least
    # this doesn't prevent the tar ball creation. A lot more work could be done here - such as making sure
    # they map to the same dataset on import and making sure the resulting datasets all look good in the
    # imported history.


def test_export_copied_collection():
    app, sa_session, h = _setup_history_for_export("Collection History with copied collection")

    d1, d2 = _create_datasets(sa_session, h, 2)

    c1 = model.DatasetCollection(collection_type="paired")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=3, collection=c1, name="HistoryCollectionTest1")
    h.hid_counter = 4
    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)

    sa_session.add_all((dce1, dce2, d1, d2, hc1))
    with transaction(sa_session):
        sa_session.commit()

    hc2 = hc1.copy(element_destination=h)
    h.add_pending_items()
    assert h.hid_counter == 7

    sa_session.add(hc2)
    with transaction(sa_session):
        sa_session.commit()

    assert hc2.copied_from_history_dataset_collection_association == hc1

    imported_history = _import_export(app, h)
    assert imported_history.hid_counter == 7

    assert len(imported_history.dataset_collections) == 2
    assert len(imported_history.datasets) == 4

    _assert_distinct_hids(imported_history)
    imported_by_hid = _hid_dict(imported_history)
    assert imported_by_hid[4].copied_from_history_dataset_association == imported_by_hid[1]
    assert imported_by_hid[5].copied_from_history_dataset_association == imported_by_hid[2]
    assert imported_by_hid[6].copied_from_history_dataset_collection_association == imported_by_hid[3]


def test_export_copied_objects_copied_outside_history():
    app, sa_session, h = _setup_history_for_export("Collection History with copied objects")

    d1, d2 = _create_datasets(sa_session, h, 2)

    c1 = model.DatasetCollection(collection_type="paired")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=3, collection=c1, name="HistoryCollectionTest1")
    h.hid_counter = 4
    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)

    sa_session.add_all((dce1, dce2, d1, d2, hc1))
    with transaction(sa_session):
        sa_session.commit()

    hc2 = hc1.copy(element_destination=h)

    sa_session.add(hc2)

    other_h = model.History(name=h.name + "-other", user=h.user)
    sa_session.add(other_h)
    with transaction(sa_session):
        sa_session.commit()

    hc3 = hc2.copy(element_destination=other_h)
    other_h.add_pending_items()

    hc4 = hc3.copy(element_destination=h)
    sa_session.add(hc4)
    h.add_pending_items()
    with transaction(sa_session):
        sa_session.commit()

    assert h.hid_counter == 10

    original_by_hid = _hid_dict(h)
    assert original_by_hid[7].copied_from_history_dataset_association != original_by_hid[4]
    assert original_by_hid[8].copied_from_history_dataset_association != original_by_hid[5]
    assert original_by_hid[9].copied_from_history_dataset_collection_association != original_by_hid[6]

    imported_history = _import_export(app, h)

    assert imported_history.hid_counter == 10
    assert len(imported_history.dataset_collections) == 3
    assert len(imported_history.datasets) == 6

    _assert_distinct_hids(imported_history)
    imported_by_hid = _hid_dict(imported_history)
    assert imported_by_hid[4].copied_from_history_dataset_association == imported_by_hid[1]
    assert imported_by_hid[5].copied_from_history_dataset_association == imported_by_hid[2]
    assert imported_by_hid[6].copied_from_history_dataset_collection_association == imported_by_hid[3]

    assert imported_by_hid[7].copied_from_history_dataset_association == imported_by_hid[4]
    assert imported_by_hid[8].copied_from_history_dataset_association == imported_by_hid[5]
    assert imported_by_hid[9].copied_from_history_dataset_collection_association == imported_by_hid[6]


def test_export_collection_hids():
    app, sa_session, h = _setup_history_for_export("Collection History with dataset from this history")

    d1, d2 = _create_datasets(sa_session, h, 2)

    c1 = model.DatasetCollection(collection_type="paired")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=3, collection=c1, name="HistoryCollectionTest1")
    h.hid_counter = 4
    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)

    sa_session.add(dce1)
    sa_session.add(dce2)
    sa_session.add(d1)
    sa_session.add(d2)
    sa_session.add(hc1)
    with transaction(sa_session):
        sa_session.commit()

    imported_history = _import_export(app, h)

    assert imported_history.hid_counter == 4, imported_history.hid_counter
    assert len(imported_history.dataset_collections) == 1
    assert len(imported_history.datasets) == 2
    for hdca in imported_history.dataset_collections:
        assert hdca.hid == 3, hdca.hid
    for hda in imported_history.datasets:
        assert hda.hid in [1, 2], hda.hid
    _assert_distinct_hids(imported_history)


def _assert_distinct_hids(history):
    hids = []
    for hdca in history.dataset_collections:
        hids.append(hdca.hid)
    for hda in history.datasets:
        hids.append(hda.hid)
    _assert_distinct(hids)


def _hid_dict(history):
    hids = {}
    for hdca in history.dataset_collections:
        hids[hdca.hid] = hdca
    for hda in history.datasets:
        hids[hda.hid] = hda
    return hids


def _assert_distinct(list_):
    assert len(list_) == len(set(list_))


def _create_datasets(sa_session, history, n, extension="txt"):
    return [
        model.HistoryDatasetAssociation(
            extension=extension, history=history, create_dataset=True, sa_session=sa_session, hid=i + 1
        )
        for i in range(n)
    ]


def _setup_history_for_export(history_name):
    app = _mock_app()
    sa_session = app.model.context

    email = history_name.replace(" ", "-") + "-user@example.org"
    u = model.User(email=email, password="password")
    h = model.History(name=history_name, user=u)

    return app, sa_session, h


def _import_export(app, h, dest_export=None):
    if dest_export is None:
        dest_parent = tempfile.mkdtemp()
        dest_export = os.path.join(dest_parent, "moo.tgz")

    job = model.Job()
    app.model.session.add(job, h)
    session = app.model.session
    with transaction(session):
        session.commit()
    jeha = model.JobExportHistoryArchive.create_for_history(
        h, job, app.model.context, app.object_store, compressed=True
    )
    wrapper = JobExportHistoryArchiveWrapper(app, job.id)
    wrapper.setup_job(h, jeha.temp_directory)

    from galaxy.tools.imp_exp import export_history

    ret = export_history.main(["--gzip", jeha.temp_directory, dest_export])
    assert ret == 0, ret

    _, imported_history = import_archive(dest_export, app=app)
    assert imported_history
    return imported_history


def test_import_1901_default():
    app, new_history = import_archive(t_data_path("exports/1901_two_datasets.tgz"))
    assert new_history

    datasets = new_history.datasets
    assert len(datasets) == 2
    dataset0 = datasets[0]
    dataset1 = datasets[1]

    assert dataset0.hid == 1
    # There was a deleted dataset so skip to 3
    assert dataset1.hid == 3, dataset1.hid

    stmt = select(model.Job).filter_by(history_id=new_history.id).order_by(model.Job.id)
    jobs = app.model.session.scalars(stmt).all()
    assert len(jobs) == 2
    assert jobs[0].tool_id == "upload1"
    assert jobs[1].tool_id == "cat"

    cat_job = jobs[1]
    assert len(cat_job.input_datasets) == 2
    assert len(cat_job.output_datasets) == 1

    assert cat_job.input_datasets[0].dataset == dataset0
    assert cat_job.input_datasets[1].dataset == dataset0
    assert cat_job.output_datasets[0].dataset == dataset1

    param_dict = cat_job.raw_param_dict()
    # Not sure these shouldn't be {"values": [{"src": "hda", "id": dataset0.id}]}
    # but parameter processing for pre-19.05 exports/imports didn't work anyway so
    # perhaps not a problem?
    input1_param = json.loads(param_dict["input1"])
    assert input1_param["src"] == "hda"
    assert input1_param["id"] == dataset0.id

    input2_param = json.loads(param_dict["queries"])[0]["input2"]
    assert input2_param["src"] == "hda"
    assert input2_param["id"] == dataset0.id


def import_archive(archive_path, app=None):
    dest_parent = tempfile.mkdtemp()
    dest_dir = os.path.join(dest_parent, "dest")

    options = Mock()
    options.is_url = False
    options.is_file = True
    options.is_b64encoded = False

    args = (archive_path, dest_dir)
    unpack_tar_gz_archive.main(options, args)
    app, new_history = _run_jihaw_cleanup(dest_dir, app=app)
    return app, new_history


def _run_unpack(history_archive, dest_parent, msg):
    dest_dir = os.path.join(dest_parent, "dest")
    insecure_dir = os.path.join(dest_parent, "insecure")
    os.makedirs(dest_dir)
    options = Mock()
    options.is_url = False
    options.is_file = True
    options.is_b64encoded = False
    args = (history_archive.tar_file_path, dest_dir)
    try:
        unpack_tar_gz_archive.main(options, args)
    except AssertionError:
        pass
    assert not os.path.exists(insecure_dir), msg


def test_history_import_relpath_in_archive():
    """Ensure that a history import archive cannot reference a relative path
    outside the archive
    """
    dest_parent = tempfile.mkdtemp()
    with HistoryArchive(arcname_prefix="../insecure") as history_archive:
        history_archive.write_metafiles()
        history_archive.write_file("datasets/Pasted_Entry_1.txt", "foo")
        history_archive.finalize()
        _run_unpack(history_archive, dest_parent, "Relative parent path in import archive allowed")


def test_history_import_abspath_in_archive():
    """Ensure that a history import archive cannot reference a absolute path
    outside the archive
    """
    dest_parent = tempfile.mkdtemp()
    arcname_prefix = os.path.abspath(os.path.join(dest_parent, "insecure"))

    with HistoryArchive(arcname_prefix=arcname_prefix) as history_archive:
        history_archive.write_metafiles()
        history_archive.write_file("datasets/Pasted_Entry_1.txt", "foo")
        history_archive.finalize()
        _run_unpack(history_archive, dest_parent, "Absolute path in import archive allowed")


class HistoryArchive:
    def __init__(self, arcname_prefix=None):
        self.temp_directory = tempfile.mkdtemp()
        self.arc_directory = os.path.join(self.temp_directory, "archive")
        self.arcname_prefix = arcname_prefix
        self.tar_file_path = os.path.join(self.temp_directory, "archive.tar.gz")
        self.tar_file = tarfile.open(self.tar_file_path, "w:gz")
        os.makedirs(self.arc_directory)

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        rmtree(self.temp_directory)

    def _create_parent(self, fname):
        path = os.path.join(self.arc_directory, fname)
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

    def _arcname(self, path):
        if self.arcname_prefix:
            path = os.path.join(self.arcname_prefix, path)
        return path

    def write_metafiles(self, dataset_file_name="datasets/Pasted_Entry_1.txt"):
        self.write_file("datasets_attrs.txt", DATASETS_ATTRS.format(file_name=dataset_file_name))
        self.write_file("datasets_attrs.txt.provenance", DATASETS_ATTRS_PROVENANCE)
        self.write_file("history_attrs.txt", HISTORY_ATTRS)
        self.write_file("jobs_attrs.txt", JOBS_ATTRS)

    def write_outside(self, fname="outside.txt", contents="invalid"):
        with open(os.path.join(self.temp_directory, fname), "w") as f:
            f.write(contents)

    def write_file(self, fname, contents):
        self._create_parent(fname)
        path = os.path.join(self.arc_directory, fname)
        with open(path, "w") as f:
            f.write(contents)
        # TarFile.add() (via TarFile.gettarinfo()) strips leading '/' and is
        # unsuitable for our purposes
        ti = self.tar_file.gettarinfo(fileobj=open(path, "rb"))
        ti.name = self._arcname(fname)
        self.tar_file.addfile(ti, fileobj=open(path, "rb"))

    def write_link(self, fname, target):
        self._create_parent(fname)
        path = os.path.join(self.arc_directory, fname)
        os.symlink(target, path)

    def finalize(self):
        self.tar_file.close()


class Dummy:
    pass
