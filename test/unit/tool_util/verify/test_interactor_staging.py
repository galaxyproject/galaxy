import pytest
import responses
from requests.exceptions import HTTPError

from galaxy.tool_util.parser.factory import build_xml_tool_source
from galaxy.tool_util.verify.interactor import (
    GalaxyInteractorApi,
    InputStagingError,
    JobDataT,
    JobOutputsError,
    RunToolException,
    verify_tool,
)
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions

API = "http://galaxy.example/api"
SUBMISSION_ERROR = "Parameter 'input': the previously selected dataset has entered an unusable state"
DATASET_ERROR = "Checksum mismatch"


@pytest.fixture
def interactor():
    return GalaxyInteractorApi(galaxy_url="http://galaxy.example", master_api_key="key", api_key="key")


@pytest.fixture
def mocked():
    with responses.RequestsMock() as mock:
        mock.post(
            f"{API}/tools/fetch",
            json={
                "jobs": [{"id": "upload1", "history_id": "hist1"}],
                "outputs": [{"id": "hda1"}],
            },
        )
        mock.get(f"{API}/jobs/upload1", json={"state": "ok"})
        yield mock


@pytest.fixture
def tool_test():
    source = build_xml_tool_source("""
        <tool id="staging_test" name="Staging test" version="1.0" profile="24.2">
            <command>cat '$input'</command>
            <inputs><param name="input" type="data" format="txt"/></inputs>
            <tests><test>
                <param name="input" value="input.txt" location="https://example.org/input.txt"/>
            </test></tests>
        </tool>
    """)
    return next(iter(parse_tool_test_descriptions(source))).to_dict()


def _verify(interactor, tool_test, reports, use_legacy_api="always"):
    verify_tool(
        "staging_test",
        interactor,
        test_history="hist1",
        register_job_data=reports.append,
        _tool_test_dicts=[tool_test],
        use_legacy_api=use_legacy_api,
        quiet=True,
    )


def _mock_tool_job(mocked, state="error"):
    mocked.post(
        f"{API}/tools",
        json={"jobs": [{"id": "tool1", "tool_id": "staging_test"}], "outputs": [], "output_collections": []},
    )
    mocked.get(f"{API}/jobs/tool1", json={"state": state}, match=[responses.matchers.query_param_matcher({})])
    mocked.get(
        f"{API}/jobs/tool1?full=true",
        json={"state": state, "tool_id": "staging_test", "exit_code": 1, "stderr": "Tool execution failed"},
    )


@pytest.mark.parametrize("upload_async", [True, False])
@pytest.mark.parametrize("expect_failure", [True, False])
@pytest.mark.parametrize("failure_phase", ["submission", "request", "job"])
def test_failed_staged_input_is_reported(
    interactor, mocked, tool_test, monkeypatch, upload_async, expect_failure, failure_phase
):
    monkeypatch.setattr("galaxy.tool_util.verify.interactor.UPLOAD_ASYNC", upload_async)
    tool_test["expect_failure"] = expect_failure
    tool_test["expect_test_failure"] = expect_failure
    use_legacy_api = "always"
    original_error = SUBMISSION_ERROR
    if failure_phase == "submission":
        mocked.post(f"{API}/tools", status=400, json={"err_msg": original_error})
    elif failure_phase == "request":
        use_legacy_api = "never"
        mocked.post(f"{API}/jobs", json={"tool_request_id": "request1"})
        mocked.get(f"{API}/tool_requests/request1/state", json="failed")
        mocked.get(f"{API}/tool_requests/request1", json={"state": "failed", "state_message": original_error})
    else:
        original_error = "Tool execution failed"
        _mock_tool_job(mocked)
    mocked.get(
        f"{API}/histories/hist1/contents/hda1",
        json={"name": "input.txt", "state": "error", "info": DATASET_ERROR},
    )
    reports: list[JobDataT] = []

    with pytest.raises(InputStagingError, match=DATASET_ERROR) as exc:
        _verify(interactor, tool_test, reports, use_legacy_api)

    assert "input.txt" in str(exc.value)
    assert "hda1" in str(exc.value)
    assert original_error in str(exc.value.__cause__)
    assert reports[0]["status"] == "error"
    assert "Input staging problem:" in reports[0]["execution_problem"]
    assert DATASET_ERROR in reports[0]["execution_problem"]
    assert original_error in reports[0]["execution_problem"]


def test_failed_input_in_nested_collection_is_reported(interactor, mocked):
    source = build_xml_tool_source("""
        <tool id="staging_test" name="Staging test" version="1.0" profile="24.2">
            <command>cat '$input'</command>
            <inputs><param name="input" type="data_collection" collection_type="list:list" format="txt"/></inputs>
            <tests><test>
                <param name="input">
                    <collection type="list:list">
                        <element name="sample"><collection type="list">
                            <element name="read" value="input.txt" location="https://example.org/input.txt"/>
                        </collection></element>
                    </collection>
                </param>
            </test></tests>
        </tool>
    """)
    tool_test = next(iter(parse_tool_test_descriptions(source))).to_dict()
    mocked.post(f"{API}/dataset_collections", json={"id": "hdca1"})
    mocked.post(f"{API}/tools", status=400, json={"err_msg": SUBMISSION_ERROR})
    mocked.get(
        f"{API}/histories/hist1/contents/hda1",
        json={"name": "input.txt", "state": "error", "info": DATASET_ERROR},
    )
    reports: list[JobDataT] = []

    with pytest.raises(InputStagingError, match=DATASET_ERROR):
        _verify(interactor, tool_test, reports)

    assert reports[0]["inputs"] == {"input": {"src": "hdca", "id": "hdca1"}}
    assert reports[0]["status"] == "error"
    assert DATASET_ERROR in reports[0]["execution_problem"]


@pytest.mark.parametrize("expect_failure", [True, False])
@pytest.mark.parametrize("diagnostics", ["ok", "unavailable", "invalid_json"])
def test_submission_error_is_preserved_without_staging_diagnostics(
    interactor, mocked, tool_test, expect_failure, diagnostics
):
    tool_test["expect_failure"] = expect_failure
    mocked.post(f"{API}/tools", status=400, json={"err_msg": SUBMISSION_ERROR})
    url = f"{API}/histories/hist1/contents/hda1"
    if diagnostics == "unavailable":
        mocked.get(url, status=503)
    elif diagnostics == "invalid_json":
        mocked.get(url, body="not JSON")
    else:
        mocked.get(url, json={"name": "input.txt", "state": "ok"})
    reports: list[JobDataT] = []

    if expect_failure:
        _verify(interactor, tool_test, reports)
    else:
        with pytest.raises(RunToolException, match=SUBMISSION_ERROR):
            _verify(interactor, tool_test, reports)

    assert reports[0]["execution_problem"] == SUBMISSION_ERROR
    assert reports[0]["status"] == ("success" if expect_failure else "error")


@pytest.mark.parametrize("expect_failure", [True, False])
def test_job_failure_with_healthy_inputs_keeps_existing_result(interactor, mocked, tool_test, expect_failure):
    tool_test["expect_failure"] = expect_failure
    _mock_tool_job(mocked)
    mocked.get(f"{API}/histories/hist1/contents/hda1", json={"state": "ok"})
    reports: list[JobDataT] = []

    if expect_failure:
        _verify(interactor, tool_test, reports)
    else:
        with pytest.raises(JobOutputsError, match="Tool execution failed"):
            _verify(interactor, tool_test, reports)

    assert reports[0]["status"] == ("success" if expect_failure else "failure")


def test_request_http_error_preserves_submitted_inputs(interactor, mocked, tool_test):
    mocked.post(f"{API}/jobs", json={"tool_request_id": "request1"})
    mocked.get(f"{API}/tool_requests/request1/state", status=503)
    mocked.get(f"{API}/histories/hist1/contents/hda1", json={"state": "ok"})
    reports: list[JobDataT] = []

    with pytest.raises(HTTPError, match="503"):
        _verify(interactor, tool_test, reports, use_legacy_api="never")

    assert reports[0]["inputs"] == {"input": {"src": "hda", "id": "hda1"}}
    assert reports[0]["status"] == "error"
    assert "503" in reports[0]["execution_problem"]


def test_success_does_not_request_staging_diagnostics(interactor, mocked, tool_test):
    _mock_tool_job(mocked, state="ok")
    reports: list[JobDataT] = []

    _verify(interactor, tool_test, reports)

    assert reports[0]["status"] == "success"
    assert not any("/contents/" in call.request.url for call in mocked.calls)


def test_diagnostics_continue_after_a_failed_lookup(interactor):
    interactor.uploads = {f"input{i}.txt": {"src": "hda", "id": f"hda{i}"} for i in range(1, 5)}
    original_error = RunToolException(SUBMISSION_ERROR)
    with responses.RequestsMock() as mock:
        mock.get(f"{API}/histories/hist1/contents/hda1", status=404)
        mock.get(f"{API}/histories/hist1/contents/hda2", json={"name": "good.txt", "state": "ok"})
        mock.get(
            f"{API}/histories/hist1/contents/hda3",
            json={"name": "broken.txt", "state": "error", "info": DATASET_ERROR},
        )
        mock.get(
            f"{API}/histories/hist1/contents/hda4",
            json={"name": "empty-info.txt", "state": "error", "info": None},
        )

        with pytest.raises(InputStagingError) as exc:
            interactor.raise_for_failed_staged_inputs("hist1", original_error)

    message = str(exc.value)
    assert "input3.txt" in message
    assert "broken.txt" in message
    assert DATASET_ERROR in message
    assert "empty-info.txt" in message
    assert "No dataset error details available." in message
    assert "good.txt" not in message
    assert exc.value.__cause__ is original_error
