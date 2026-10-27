"""Real SQL transactions around the opt-in upload finish protocol."""

import copy
import json
import os
from pathlib import Path
from types import (
    MethodType,
    SimpleNamespace,
)
from unittest.mock import Mock

import pytest
from sqlalchemy import (
    create_engine,
    event,
    inspect,
    text,
    update,
)
from sqlalchemy.engine import make_url

from galaxy import model
from galaxy.jobs import JobWrapper
from galaxy.jobs.runners import BaseJobRunner
from galaxy.jobs.upload_finish import (
    RECEIPT_KEY,
    UploadFinishCancelled,
    UploadFinishContext,
    UploadFinishError,
    validate_upload,
)
from galaxy.model import store
from galaxy.model.unittest_utils import (
    GalaxyDataTestApp,
    GalaxyDataTestConfig,
)
from galaxy.model.unittest_utils.store_fixtures import (
    one_hda_model_store_dict,
    one_ld_library_model_store_dict,
)
from galaxy.tool_util.output_checker import DETECTED_JOB_STATE
from galaxy.tools import Tool


class SimulatedCrash(BaseException):
    pass


@pytest.fixture(scope="module")
def postgres_url():
    configured = os.environ.get("GALAXY_UPLOAD_FINISH_TEST_DATABASE")
    if not configured:
        yield None
        return
    url = make_url(configured)
    if url.get_backend_name() != "postgresql" or not (url.database or "").startswith("galaxy_upload_finish_test_"):
        pytest.fail(
            "GALAXY_UPLOAD_FINISH_TEST_DATABASE must name an isolated galaxy_upload_finish_test_ PostgreSQL database"
        )
    url = url.update_query_dict({"options": "-c statement_timeout=60000"})
    connection_url = url.render_as_string(hide_password=False)
    engine = create_engine(connection_url)
    try:
        if inspect(engine).get_table_names():
            pytest.fail("The dedicated upload test database must have an empty schema before this module")
        yield connection_url
    finally:
        engine.dispose()


@pytest.fixture
def finish_case(tmp_path, postgres_url):
    database = postgres_url or f"sqlite:///{tmp_path / 'finish.sqlite'}"
    app = GalaxyDataTestApp(GalaxyDataTestConfig(root=str(tmp_path), database_connection=database))
    app.config.enable_celery_tasks = False
    app.config.calculate_dataset_hash = "never"
    app.execution_timer_factory = SimpleNamespace(get_timer=lambda *_: SimpleNamespace(to_str=lambda **_: "test"))
    session = app.model.session
    user = model.User(email="upload-test@example.invalid", username="upload-test", password="test")
    user.disk_usage = 0
    history = model.History(name="Upload recovery", user=user)
    job = model.Job()
    job.user, job.history = user, history
    job.tool_id, job.tool_version = "__DATA_FETCH__", "0.1.0"
    job.state = model.Job.states.FINISHING
    job.destination_params = {"metadata_strategy": "extended", "unrelated": "retained"}
    session.add_all([user, history, job])
    session.commit()
    directory = tmp_path / "job"
    populated = directory / "metadata/outputs_populated"
    populated.mkdir(parents=True)
    payload = one_hda_model_store_dict(include_source=True)["datasets"][0]
    payload.update(
        encoded_id="output-key",
        name="upload.txt",
        extension="txt",
        file_name="data.txt",
        state="ok",
        metadata={"dbkey": "?", "data_lines": 2},
    )
    data = b"first\nsecond\n"
    (populated / "data.txt").write_bytes(data)
    manifests = {
        store.ATTRS_FILENAME_EXPORT: {"galaxy_export_version": "2"},
        store.ATTRS_FILENAME_DATASETS: [payload],
        store.ATTRS_FILENAME_COLLECTIONS: [],
        store.ATTRS_FILENAME_JOBS: [
            {
                "id": job.id,
                "state": "ok",
                "output_dataset_mapping": {"output": ["output-key"]},
            }
        ],
    }
    for filename, value in manifests.items():
        (populated / filename).write_text(json.dumps(value))
    case = SimpleNamespace(
        app=app,
        job_id=job.id,
        user_id=user.id,
        history_id=history.id,
        directory=directory,
        populated=populated,
        payload=payload,
        data=data,
        token="one-detached-execution",
    )
    try:
        yield case
    finally:
        session.remove()
        app.model.engine.dispose()
        if postgres_url:
            engine = create_engine(postgres_url)
            try:
                names = inspect(engine).get_table_names()
                if names:
                    quote = engine.dialect.identifier_preparer.quote
                    with engine.begin() as connection:
                        connection.execute(
                            text("TRUNCATE " + ", ".join(map(quote, names)) + " RESTART IDENTITY CASCADE")
                        )
            finally:
                engine.dispose()


def wrapper_for(case):
    job = case.app.model.session.get(model.Job, case.job_id)
    tool = object.__new__(Tool)
    tool.id = job.tool_id
    tool.get_hook = lambda _: None
    tool.call_hook = lambda *_args, **_kwds: None
    tool.stdio_regexes, tool.stdio_exit_codes = [], []
    tool.runtime_environment_variables = []
    cleanup = []
    wrapper = SimpleNamespace(
        app=case.app,
        sa_session=case.app.model.session,
        tool=tool,
        get_job=lambda: job,
        job_id=job.id,
        working_directory=str(case.directory),
        external_output_metadata=SimpleNamespace(extended=True),
        get_tool_provided_job_metadata=lambda: SimpleNamespace(has_failed_outputs=lambda: False),
        reclaim_ownership=lambda: None,
        get_param_dict=lambda _: {},
        _set_unknown_output_extensions_to_data=lambda _: None,
        _fix_output_permissions=lambda: None,
        _collect_metrics=lambda *_: None,
        _report_error=lambda: None,
        cleanup=lambda delete_files: cleanup.append(delete_files),
        cleanup_job="never",
        fail=lambda *_args, **_kwds: pytest.fail("transactional finish must not call fail"),
        cleanup_calls=cleanup,
    )
    wrapper.check_tool_output = MethodType(JobWrapper.check_tool_output, wrapper)
    wrapper.finish_context = UploadFinishContext(wrapper, case.token)
    return wrapper


def importer_for(case):
    job = case.app.model.session.get(model.Job, case.job_id)
    return store.get_import_model_store_for_directory(
        str(case.populated),
        app=case.app,
        user=job.user,
        import_options=store.ImportOptions(allow_edit=True, allow_dataset_object_edit=True, commit=False),
        tag_handler=case.app.tag_handler.create_tag_handler_session(None),
    )


def restart(case):
    case.app.model.session.remove()
    return wrapper_for(case)


def finish(wrapper):
    JobWrapper.finish(wrapper, "", "", tool_exit_code=0)


def counts(case):
    session = case.app.model.session
    return tuple(
        session.query(klass).count()
        for klass in (
            model.HistoryDatasetAssociation,
            model.Dataset,
            model.JobToOutputDatasetAssociation,
            model.DatasetHash,
            model.DatasetSource,
        )
    )


@pytest.mark.parametrize("event_name", ["before_commit", "after_commit"])
@pytest.mark.parametrize("commit_number", [1, 2, 3])
def test_recovery_across_each_sql_commit_and_lost_ack(finish_case, event_name, commit_number):
    case = finish_case
    wrapper = wrapper_for(case)
    sql_session = case.app.model.session()
    calls = 0

    def crash(_session):
        nonlocal calls
        calls += 1
        if calls == commit_number:
            raise SimulatedCrash()

    event.listen(sql_session, event_name, crash)
    try:
        with pytest.raises(SimulatedCrash):
            finish(wrapper)
    finally:
        event.remove(sql_session, event_name, crash)
    wrapper = restart(case)
    finish(wrapper)
    job = wrapper.get_job()
    assert job.state == "ok"
    assert counts(case) == (1, 1, 1, 1, 1)
    assert case.app.model.session.get(model.User, case.user_id).disk_usage == len(case.data)
    assert Path(job.output_datasets[0].dataset.get_file_name()).read_bytes() == case.data
    receipt = job.destination_params[RECEIPT_KEY]
    assert receipt["imported"]["ids"]["hdas_by_key"]["output-key"] == job.output_datasets[0].dataset.id
    assert receipt["postprocessed"]["final_state"] == receipt["finalized"]["final_state"] == "ok"
    assert job.destination_params["unrelated"] == "retained"
    before = counts(case)
    finish(restart(case))
    assert counts(case) == before
    assert case.app.model.session.get(model.User, case.user_id).disk_usage == len(case.data)


@pytest.mark.parametrize("commit", [False, True])
def test_import_flush_policy_leaves_commit_ownership_with_caller(finish_case, commit):
    case = finish_case
    importer = importer_for(case)
    importer.import_options.commit = commit
    job = case.app.model.session.get(model.Job, case.job_id)
    importer.perform_import(history=job.history, job=job)
    case.app.model.session.rollback()
    assert counts(case)[0] == int(commit)


def test_phase_a_failure_rolls_back_all_imported_rows(finish_case, monkeypatch):
    case = finish_case
    wrapper = wrapper_for(case)
    context = wrapper.finish_context
    context.begin()
    importer = importer_for(case)
    native = importer._import_jobs

    def fail_after_flush(*args):
        native(*args)
        raise OSError("database connection interrupted")

    monkeypatch.setattr(importer, "_import_jobs", fail_after_flush)
    with pytest.raises(OSError, match="interrupted"):
        context.import_outputs(importer)
    assert counts(case) == (0, 0, 0, 0, 0)
    assert RECEIPT_KEY not in wrapper.get_job().destination_params
    finish(restart(case))
    assert counts(case) == (1, 1, 1, 1, 1)


def test_imported_receipt_skips_importer_and_keeps_object_identities(finish_case, monkeypatch):
    case = finish_case
    wrapper = wrapper_for(case)
    context = wrapper.finish_context
    context.begin()
    context.import_outputs(importer_for(case))
    parameters = copy.deepcopy(wrapper.get_job().destination_params)
    identities = parameters[RECEIPT_KEY]["imported"]["ids"]
    hda_id = identities["hdas_by_key"]["output-key"]
    # Exercise the receipt's raw-ID index alongside its exported-key index.
    identities["hdas_by_id"] = {str(hda_id): hda_id}
    wrapper.get_job().destination_params = parameters
    case.app.model.session.commit()
    wrapper = restart(case)
    context = wrapper.finish_context
    context.begin()
    importer = importer_for(case)
    monkeypatch.setattr(importer, "perform_import", lambda **_: pytest.fail("must not replay a committed import"))
    tracker = context.import_outputs(importer)
    assert context.receipt["imported"]["ids"] == identities
    assert tracker.hdas_by_key["output-key"].id == hda_id
    assert tracker.hdas_by_id == {hda_id: tracker.hdas_by_key["output-key"]}
    assert all(type(key) is int for key in tracker.hdas_by_id)


def test_recovery_after_import_commit_applies_default_permissions(finish_case):
    case = finish_case
    session = case.app.model.session
    job = session.get(model.Job, case.job_id)
    role = model.Role(name="upload-owner", type=model.Role.types.PRIVATE)
    actions = case.app.security_agent.permitted_actions
    permissions = (actions.DATASET_ACCESS.action, actions.DATASET_MANAGE_PERMISSIONS.action)
    session.add(role)
    session.add(model.UserRoleAssociation(job.user, role))
    session.add_all(model.DefaultHistoryPermissions(job.history, action, role) for action in permissions)
    session.commit()
    role_id = role.id
    wrapper = wrapper_for(case)
    sql_session = session()

    def crash_after_import_commit(_session):
        raise SimulatedCrash()

    event.listen(sql_session, "after_commit", crash_after_import_commit)
    try:
        with pytest.raises(SimulatedCrash):
            finish(wrapper)
    finally:
        event.remove(sql_session, "after_commit", crash_after_import_commit)
    wrapper = restart(case)
    job = wrapper.get_job()
    hda = job.output_datasets[0].dataset
    hda_id = hda.id
    assert not hda.dataset.actions
    assert "postprocessed" not in job.destination_params[RECEIPT_KEY]
    context = wrapper.finish_context
    context.begin()
    tracker = context.import_outputs(importer_for(case))
    assert tracker.hdas_by_key == {"output-key": hda}

    finish(wrapper)
    wrapper = restart(case)
    job = wrapper.get_job()
    dataset = job.output_datasets[0].dataset.dataset
    expected = sorted((action, role_id) for action in permissions)
    assert sorted((permission.action, permission.role_id) for permission in dataset.actions) == expected
    assert job.output_datasets[0].dataset.id == hda_id
    assert job.state == "ok"
    assert counts(case) == (1, 1, 1, 1, 1)
    assert job.user.disk_usage == len(case.data)
    finish(wrapper)
    wrapper = restart(case)
    dataset = wrapper.get_job().output_datasets[0].dataset.dataset
    assert sorted((permission.action, permission.role_id) for permission in dataset.actions) == expected
    assert wrapper.get_job().user.disk_usage == len(case.data)


def test_library_upload_import_rolls_back_folder_flush_and_recovers_once(finish_case, monkeypatch):
    case = finish_case
    session = case.app.model.session
    library = model.Library(name="Existing library", description="", synopsis="")
    folder = model.LibraryFolder(name="Existing folder", description="")
    library.root_folder = folder
    session.add(library)
    session.commit()
    folder_id = folder.id
    exported = one_ld_library_model_store_dict()
    ldda_attributes = exported["datasets"][0]
    ldda_attributes.update(file_name="data.txt", state="ok", extension="txt", metadata={"dbkey": "?", "data_lines": 2})
    folder_attributes = exported["libraries"][0]["root_folder"]
    folder_attributes["id"] = folder_id
    (case.populated / store.ATTRS_FILENAME_DATASETS).write_text(json.dumps([ldda_attributes]))
    (case.populated / store.ATTRS_FILENAME_LIBRARIES).write_text(json.dumps([folder_attributes]))
    (case.populated / store.ATTRS_FILENAME_JOBS).write_text(json.dumps([{"id": case.job_id, "state": "ok"}]))
    context = wrapper_for(case).finish_context
    context.begin()
    importer = importer_for(case)
    original = importer._import_libraries

    def fail_after_folder_flush(tracker):
        original(tracker)
        raise OSError("interrupted after library folder flush")

    monkeypatch.setattr(importer, "_import_libraries", fail_after_folder_flush)
    with pytest.raises(OSError, match="folder flush"):
        context.import_outputs(importer)
    assert session.query(model.LibraryDataset).count() == 0
    assert session.query(model.LibraryDatasetDatasetAssociation).count() == 0
    assert session.query(model.Dataset).count() == 0
    finish(restart(case))
    folder = session.get(model.LibraryFolder, folder_id)
    assert len(folder.datasets) == 1
    ldda = folder.datasets[0].library_dataset_dataset_association
    assert Path(ldda.get_file_name()).read_bytes() == case.data
    receipt = session.get(model.Job, case.job_id).destination_params[RECEIPT_KEY]
    assert receipt["imported"]["ids"]["lddas_by_key"][ldda_attributes["encoded_id"]] == ldda.id
    finish(restart(case))
    assert session.query(model.LibraryDataset).count() == 1
    assert session.query(model.LibraryDatasetDatasetAssociation).count() == 1
    assert session.query(model.LibraryFolder).count() == 1


def write_collection_manifest(case, job_attributes):
    collection_attributes = {
        "encoded_id": "collection-key",
        "display_name": "Uploaded collection",
        "collection": {
            "type": "list",
            "populated_state": "ok",
            "elements": [
                {
                    "encoded_id": "element-key",
                    "element_index": 0,
                    "element_identifier": "upload",
                    "hda": {"encoded_id": "output-key"},
                }
            ],
        },
    }
    (case.populated / store.ATTRS_FILENAME_COLLECTIONS).write_text(json.dumps([collection_attributes]))
    (case.populated / store.ATTRS_FILENAME_JOBS).write_text(json.dumps([job_attributes]))


@pytest.mark.parametrize("id_type", [int, str])
def test_collection_upload_keeps_collection_and_element_ids_after_phase_a(finish_case, id_type):
    case = finish_case
    write_collection_manifest(
        case,
        {
            "id": id_type(case.job_id),
            "state": "ok",
            "output_dataset_mapping": {"output": ["output-key"]},
            "output_dataset_collection_mapping": {"collection": ["collection-key"]},
        },
    )
    context = wrapper_for(case).finish_context
    context.begin()
    context.import_outputs(importer_for(case))
    identities = copy.deepcopy(context.receipt["imported"]["ids"])
    finish(restart(case))
    session = case.app.model.session
    hdca = session.query(model.HistoryDatasetCollectionAssociation).one()
    assert hdca.id == identities["hdcas_by_key"]["collection-key"]
    assert hdca.collection.elements[0].id == identities["dces_by_key"]["element-key"]
    assert hdca.collection.elements[0].hda.id == identities["hdas_by_key"]["output-key"]
    assert session.query(model.JobToOutputDatasetCollectionAssociation).count() == 1
    finish(restart(case))
    assert session.query(model.HistoryDatasetCollectionAssociation).count() == 1
    assert session.query(model.DatasetCollectionElement).count() == 1
    assert session.query(model.JobToOutputDatasetCollectionAssociation).count() == 1


def test_native_minimal_string_job_id_dynamic_collection_finishes_without_rewriting_manifest(finish_case):
    case = finish_case
    write_collection_manifest(case, {"id": str(case.job_id), "output_dataset_mapping": {"output": ["output-key"]}})
    original = (case.populated / store.ATTRS_FILENAME_JOBS).read_bytes()
    finish(wrapper_for(case))
    session = case.app.model.session
    job = session.get(model.Job, case.job_id)
    assert job.state == "ok"
    assert Path(job.output_datasets[0].dataset.get_file_name()).read_bytes() == case.data
    hdca = session.query(model.HistoryDatasetCollectionAssociation).one()
    assert hdca.collection.elements[0].hda.id == job.output_datasets[0].dataset.id
    assert job.destination_params[RECEIPT_KEY]["finalized"]["final_state"] == "ok"
    assert (case.populated / store.ATTRS_FILENAME_JOBS).read_bytes() == original


def test_existing_native_collection_associations_use_their_real_orm_relationships(finish_case):
    case = finish_case
    session = case.app.model.session
    job = session.get(model.Job, case.job_id)
    collection = model.DatasetCollection(collection_type="list")
    hdca = model.HistoryDatasetCollectionAssociation(
        collection=collection, history=job.history, name="Upload collection"
    )
    session.add(hdca)
    job.add_input_dataset_collection("input_collection", hdca)
    job.add_output_dataset_collection("output_collection", hdca)
    job.add_implicit_output_dataset_collection("implicit_collection", collection)
    session.commit()
    hdca_id, collection_id = hdca.id, collection.id
    write_collection_manifest(case, {"id": str(case.job_id), "output_dataset_mapping": {"output": ["output-key"]}})
    filename = case.populated / store.ATTRS_FILENAME_COLLECTIONS
    attributes = json.loads(filename.read_text())[0]
    del attributes["encoded_id"]
    attributes["id"] = hdca_id
    attributes["collection"]["id"] = collection_id
    filename.write_text(json.dumps([attributes]))
    original = filename.read_bytes()
    context = wrapper_for(case).finish_context
    context.begin()
    context.import_outputs(importer_for(case))
    finish(restart(case))
    job = session.get(model.Job, case.job_id)
    assert job.state == "ok"
    assert job.input_dataset_collections[0].dataset_collection.id == hdca_id
    assert job.output_dataset_collection_instances[0].dataset_collection_instance.id == hdca_id
    assert job.output_dataset_collections[0].dataset_collection.id == collection_id
    assert session.query(model.HistoryDatasetCollectionAssociation).count() == 1
    assert session.query(model.DatasetCollection).count() == 1
    assert session.query(model.DatasetCollectionElement).count() == 1
    assert filename.read_bytes() == original
    assert Path(job.output_datasets[0].dataset.get_file_name()).read_bytes() == case.data


def test_string_job_id_metadata_error_is_exposed_with_canonical_tracker_key(finish_case):
    case = finish_case
    jobs = [{"id": str(case.job_id), "state": "error", "output_dataset_mapping": {"output": ["output-key"]}}]
    (case.populated / store.ATTRS_FILENAME_JOBS).write_text(json.dumps(jobs))
    context = wrapper_for(case).finish_context
    context.begin()
    tracker = context.import_outputs(importer_for(case))
    assert tracker.job_states_by_id == {case.job_id: "error"}
    finish(restart(case))
    assert case.app.model.session.get(model.Job, case.job_id).state == "error"


@pytest.mark.parametrize("identifier", [True, 1.0, "01", " 1", "+1", "other", 2, None])
def test_unrelated_or_noncanonical_job_identifiers_are_rejected(finish_case, identifier):
    case = finish_case
    (case.populated / store.ATTRS_FILENAME_JOBS).write_text(json.dumps([{"id": identifier}]))
    context = wrapper_for(case).finish_context
    context.begin()
    with pytest.raises(UploadFinishError, match="unrelated job"):
        context.import_outputs(importer_for(case))
    assert counts(case) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize("changed", ["token", "manifest", "receipt"])
def test_recovery_rejects_mismatched_execution_or_manifest(finish_case, changed):
    case = finish_case
    wrapper = wrapper_for(case)
    context = wrapper.finish_context
    context.begin()
    context.import_outputs(importer_for(case))
    if changed == "token":
        case.token = "another-execution"
    elif changed == "manifest":
        (case.populated / "data.txt").write_text("changed metadata output")
    else:
        job = wrapper.get_job()
        parameters = copy.deepcopy(job.destination_params)
        parameters[RECEIPT_KEY]["identity"]["history_id"] = -1
        job.destination_params = parameters
        case.app.model.session.commit()
    before = counts(case)
    with pytest.raises(UploadFinishError):
        finish(restart(case))
    assert counts(case) == before
    assert case.app.model.session.get(model.User, case.user_id).disk_usage == 0


@pytest.mark.parametrize("phase", ["imported", "postprocessed"])
def test_recovery_preserves_committed_metadata_messages(finish_case, phase):
    case = finish_case
    marker = {"type": "output_discovery", "desc": "An imported metadata warning", "error_level": 1}
    jobs = json.loads((case.populated / store.ATTRS_FILENAME_JOBS).read_text())
    jobs[0]["job_messages"] = [marker]
    (case.populated / store.ATTRS_FILENAME_JOBS).write_text(json.dumps(jobs))
    context = wrapper_for(case).finish_context
    context.begin()
    context.import_outputs(importer_for(case))
    messages = [marker]
    if phase == "postprocessed":
        context.prepare_postprocessing()
        messages.append({"type": "unknown_datatype", "desc": "A completion warning", "error_level": 1})
        context.job.job_messages = copy.deepcopy(messages)
        context.commit_postprocessed("ok")
    # The native runner checks immutable streams before entering finish again.
    # That preamble must not discard messages from an already committed phase.
    context.job.job_messages = []
    case.app.model.session.commit()
    finish(restart(case))
    assert case.app.model.session.get(model.Job, case.job_id).job_messages == messages


@pytest.mark.parametrize("corruption", ["ids", "raw_hda_key", "state", "messages", "phase"])
def test_corrupt_receipts_fail_permanently_instead_of_retrying(finish_case, corruption):
    case = finish_case
    wrapper = wrapper_for(case)
    context = wrapper.finish_context
    context.begin()
    context.import_outputs(importer_for(case))
    parameters = copy.deepcopy(context.job.destination_params)
    receipt = parameters[RECEIPT_KEY]
    if corruption == "ids":
        receipt["imported"]["ids"]["hdas_by_key"] = []
    elif corruption == "raw_hda_key":
        receipt["imported"]["ids"]["hdas_by_id"] = {
            "bad": next(iter(receipt["imported"]["ids"]["hdas_by_key"].values()))
        }
    elif corruption == "state":
        receipt["imported"]["job_states"] = {"not-a-job-id": "ok"}
    elif corruption == "messages":
        receipt["imported"]["job_messages"] = "invalid"
    else:
        receipt["finalized"] = {"final_state": "ok"}
    context.job.destination_params = parameters
    case.app.model.session.commit()
    with pytest.raises(UploadFinishError):
        finish(restart(case))


def test_initial_import_rejects_foreign_raw_hda_before_mutating_it(finish_case):
    case = finish_case
    session = case.app.model.session
    foreign_history = model.History(name="Other history", user=session.get(model.User, case.user_id))
    foreign = model.HistoryDatasetAssociation(
        name="Keep me", history=foreign_history, create_dataset=True, sa_session=session, flush=False
    )
    session.add(foreign)
    session.commit()
    payload = copy.deepcopy(case.payload)
    payload["id"] = foreign.id
    (case.populated / store.ATTRS_FILENAME_DATASETS).write_text(json.dumps([payload]))
    with pytest.raises(UploadFinishError, match="does not belong"):
        finish(wrapper_for(case))
    assert session.get(model.HistoryDatasetAssociation, foreign.id).name == "Keep me"
    assert RECEIPT_KEY not in session.get(model.Job, case.job_id).destination_params


@pytest.mark.parametrize("invalid", ["invalid JSON", "[5]"])
def test_malformed_manifest_is_a_permanent_error(finish_case, invalid):
    case = finish_case
    (case.populated / store.ATTRS_FILENAME_DATASETS).write_text(invalid)
    with pytest.raises(UploadFinishError, match="frozen upload metadata store"):
        finish(wrapper_for(case))
    assert counts(case) == (0, 0, 0, 0, 0)


def test_existing_hdca_cannot_redirect_import_into_another_raw_collection(finish_case):
    case = finish_case
    session = case.app.model.session
    job = session.get(model.Job, case.job_id)
    intended = model.DatasetCollection(collection_type="list")
    foreign = model.DatasetCollection(collection_type="paired")
    hdca = model.HistoryDatasetCollectionAssociation(collection=intended, history=job.history, name="Upload collection")
    session.add_all([hdca, foreign])
    session.commit()
    collection = {
        "id": hdca.id,
        "collection": {"id": foreign.id, "collection_type": "list", "elements": []},
    }
    (case.populated / store.ATTRS_FILENAME_COLLECTIONS).write_text(json.dumps([collection]))
    with pytest.raises(UploadFinishError, match="collection identity changed"):
        finish(wrapper_for(case))
    assert session.get(model.DatasetCollection, foreign.id).collection_type == "paired"
    assert RECEIPT_KEY not in session.get(model.Job, case.job_id).destination_params


@pytest.mark.parametrize("state", ["deleted", "deleting", "stopped", "stop"])
def test_cancellation_before_phase_commit_cannot_be_overwritten(finish_case, state):
    case = finish_case
    wrapper = wrapper_for(case)
    context = wrapper.finish_context
    context.begin()
    case.app.model.session.execute(update(model.Job).where(model.Job.id == case.job_id).values(state=state))
    case.app.model.session.commit()
    with pytest.raises(UploadFinishCancelled):
        context.import_outputs(importer_for(case))
    assert counts(case) == (0, 0, 0, 0, 0)
    assert case.app.model.session.get(model.Job, case.job_id).state == state


def test_cancellation_between_postprocessing_and_final_state_wins_before_autoflush(finish_case, monkeypatch):
    case = finish_case
    wrapper = wrapper_for(case)
    context = wrapper.finish_context
    native_commit = context.commit_postprocessed

    def cancel_after_postprocessing(state):
        native_commit(state)
        assert "tasks" in inspect(wrapper.get_job()).unloaded
        with case.app.model.engine.begin() as connection:
            connection.execute(update(model.Job).where(model.Job.id == case.job_id).values(state="stopped"))

    monkeypatch.setattr(context, "commit_postprocessed", cancel_after_postprocessing)
    with pytest.raises(UploadFinishCancelled):
        finish(wrapper)
    job = case.app.model.session.get(model.Job, case.job_id)
    assert job.state == "stopped"
    assert "postprocessed" in job.destination_params[RECEIPT_KEY]
    assert "finalized" not in job.destination_params[RECEIPT_KEY]
    assert case.app.model.session.get(model.User, case.user_id).disk_usage == len(case.data)


@pytest.mark.parametrize("enabled", [False, True])
def test_native_runner_only_propagates_finish_errors_for_explicit_context(tmp_path, enabled):
    job = model.Job()
    job.id, job.state = 1, model.Job.states.FINISHING
    wrapper = Mock()
    wrapper.get_job.return_value = job
    wrapper.working_directory = str(tmp_path)
    wrapper.cleanup_job = "never"
    wrapper.check_tool_output.return_value = DETECTED_JOB_STATE.OK
    wrapper.finish.side_effect = OSError("uncertain SQL acknowledgement")
    wrapper.finish_context = SimpleNamespace(enabled=True) if enabled else Mock()
    for stream in ("stdout", "stderr"):
        (tmp_path / f"tool_{stream}").write_text("")
    state = SimpleNamespace(job_wrapper=wrapper, read_exit_code=lambda: 0)
    runner = object.__new__(BaseJobRunner)
    runner.sa_session = Mock()
    if enabled:
        with pytest.raises(OSError, match="acknowledgement"):
            runner._finish_or_resubmit_job(state, "", "")
        wrapper.fail.assert_not_called()
    else:
        runner._finish_or_resubmit_job(state, "", "")
        wrapper.fail.assert_called_once_with("Unable to finish job", exception=True)


def test_association_receipt_does_not_depend_on_orm_order(finish_case):
    case = finish_case
    wrapper = wrapper_for(case)
    context = wrapper.finish_context
    context.begin()
    context.import_outputs(importer_for(case))
    job = wrapper.get_job()
    # Reordering must not invalidate a receipt. Duplicate connections must.
    job.output_datasets.reverse()
    context._verify_identities()
    job.add_output_dataset("output", job.output_datasets[0].dataset)
    case.app.model.session.commit()
    with pytest.raises(UploadFinishError, match="associations changed"):
        restart(case).finish_context.begin()


@pytest.mark.parametrize("unsupported", ["tool", "hook", "method", "pja", "celery", "metadata"])
def test_eligibility_rejects_side_effects_before_execution(finish_case, unsupported):
    wrapper = wrapper_for(finish_case)
    if unsupported == "tool":
        wrapper.get_job().tool_id = "other"
    elif unsupported == "hook":
        wrapper.tool.get_hook = lambda _: lambda: None
    elif unsupported == "method":
        wrapper.tool.exec_after_process = lambda *_args, **_kwds: None
    elif unsupported == "pja":
        wrapper.get_job().add_post_job_action(model.PostJobAction(action_type="EmailAction"))
    elif unsupported == "celery":
        wrapper.app.config.enable_celery_tasks = True
    else:
        wrapper.external_output_metadata.extended = False
    with pytest.raises(UploadFinishError):
        validate_upload(wrapper)
