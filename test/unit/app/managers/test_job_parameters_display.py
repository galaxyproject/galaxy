import json
from unittest import mock

from galaxy.managers.jobs import (
    encode_job_params,
    summarize_job_parameters,
)


def _data_fetch_job_and_trans(request_json: str):
    request_json_param = mock.Mock(type="hidden", visible=True, label="request_json")
    request_json_param.name = "request_json"
    request_json_param.value_to_display_text = lambda value: value
    tool = mock.Mock(inputs={"request_json": request_json_param})
    param_values = {"request_json": request_json}
    tool.get_param_values.return_value = param_values
    trans = mock.Mock()
    trans.app.toolbox.get_tool.return_value = tool
    trans.security.encode_id = lambda id: f"encoded_{id}"
    job = mock.Mock(
        tool_id="__DATA_FETCH__",
        dynamic_tool=None,
        output_datasets=[],
        output_library_datasets=[],
        output_dataset_collection_instances=[],
    )
    return job, trans, param_values


def test_data_fetch_parameters_display_masks_url_userinfo():
    request = {
        "targets": [
            {
                "destination": {"type": "hdas"},
                "elements": [
                    {"src": "url", "url": "https://user:secret@example.org/a.bed"},
                    {"src": "url", "url": "https://example.org/b?next=ftp://user:secret@inner/b.bed"},
                    {"src": "pasted", "paste_content": "ftp://user:secret@example.org/c.bed\n"},
                    {"src": "url", "url": "https://example.org/d.bed", "object_id": 5},
                ],
            }
        ]
    }
    request_json = json.dumps(request)
    job, trans, param_values = _data_fetch_job_and_trans(request_json)

    parameters = summarize_job_parameters(trans, job)["parameters"]

    displayed_value = next(p["value"] for p in parameters if p["text"] == "request_json")
    assert "secret" not in displayed_value
    elements = json.loads(displayed_value)["targets"][0]["elements"]
    assert elements[0]["url"] == "https://example.org/a.bed"
    assert elements[1]["url"] == "https://example.org/b?next=ftp://inner/b.bed"
    assert elements[2]["paste_content"] == "ftp://example.org/c.bed\n"
    assert elements[3] == {"src": "url", "url": "https://example.org/d.bed", "object_id": "encoded_5"}
    # The job keeps the full URLs to run and rerun with.
    assert param_values["request_json"] == request_json


def test_data_fetch_job_params_mask_url_userinfo():
    request = {
        "targets": [
            {
                "destination": {"type": "hdas"},
                "elements": [
                    {"src": "url", "url": "https://user:secret@example.org/a.bed"},
                    {"src": "url", "url": "https://example.org/b?next=ftp://user:secret@inner/b.bed"},
                    {"src": "url", "url": "https://example.org/d.bed", "object_id": 5},
                ],
            }
        ]
    }
    job = mock.Mock(tool_id="__DATA_FETCH__")
    security = mock.Mock()
    security.encode_id = lambda id: f"encoded_{id}"
    job_dict = {"params": {"request_json": json.dumps(json.dumps(request))}}

    shown = encode_job_params(security, job, job_dict)

    request_json = shown["params"]["request_json"]
    assert "secret" not in request_json
    elements = json.loads(json.loads(request_json))["targets"][0]["elements"]
    assert elements[0]["url"] == "https://example.org/a.bed"
    assert elements[1]["url"] == "https://example.org/b?next=ftp://inner/b.bed"
    assert elements[2] == {"src": "url", "url": "https://example.org/d.bed", "object_id": "encoded_5"}


def test_data_fetch_job_params_keep_pasted_text():
    pasted = "see http://example.org\ncontact alice@other.org/x"
    request = {
        "targets": [
            {
                "destination": {"type": "hdas"},
                "elements": [
                    {"src": "pasted", "paste_content": pasted},
                    {"src": "pasted", "paste_content": "line one\nhttps://user:secret@example.org/a.bed\nline three"},
                ],
            }
        ]
    }
    job = mock.Mock(tool_id="__DATA_FETCH__")
    security = mock.Mock()
    security.encode_id = lambda id: f"encoded_{id}"
    job_dict = {"params": {"request_json": json.dumps(json.dumps(request))}}

    shown = encode_job_params(security, job, job_dict)

    elements = json.loads(json.loads(shown["params"]["request_json"]))["targets"][0]["elements"]
    assert elements[0]["paste_content"] == pasted
    assert elements[1]["paste_content"] == "line one\nhttps://example.org/a.bed\nline three"
