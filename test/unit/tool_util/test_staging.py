"""How the staging client decides between uploading a file and pointing the
server at its path."""

from typing import Any

from galaxy.tool_util.client.staging import StagingInterface


class _CapturingStagingInterface(StagingInterface):
    """Staging interface that captures the payload instead of posting it."""

    def __init__(self):
        self.payloads: list[dict[str, Any]] = []
        self.attached: list[str] = []

    def _post(self, api_path: str, payload: dict[str, Any], files_attached: bool = False) -> dict[str, Any]:
        self.payloads.append(payload)
        return {"outputs": [{"id": "dataset1"}]}

    def _attach_file(self, path: str):
        self.attached.append(path)
        return b"<file contents>"

    def _handle_job(self, job_response: dict[str, Any]) -> None:
        pass

    @property
    def use_fetch_api(self) -> bool:
        return True


def _element_for(file_value: dict[str, Any], use_path_paste: bool) -> dict[str, Any]:
    interface = _CapturingStagingInterface()
    interface.stage(
        "tool",
        history_id="hist1",
        job={"input1": dict(file_value, **{"class": "File"})},
        use_path_paste=use_path_paste,
    )
    assert interface.payloads, "no payload was built"
    return interface.payloads[0]["targets"][0]["elements"][0]


def test_server_resolvable_location_is_pasted_not_uploaded():
    """--force_path_paste must keep avoiding uploads for a path the server can
    open itself, which is the whole point of the flag."""
    element = _element_for({"location": "file:///srv/test-data/1.bed"}, use_path_paste=True)
    assert element["src"] == "url"


def test_client_local_file_is_uploaded_despite_path_paste(tmp_path):
    """A file only the client can see has to be uploaded - the server has no
    such path, and asking it to open one fails with ENOENT."""
    local = tmp_path / "downloaded.bed"
    local.write_text("chr1\t1\t2\n")
    element = _element_for({"path": str(local), "client_local": True}, use_path_paste=True)
    assert element["src"] == "files"


def test_unmarked_path_still_pasted(tmp_path):
    """Callers that do not mark provenance keep the previous behaviour."""
    local = tmp_path / "shared.bed"
    local.write_text("chr1\t1\t2\n")
    element = _element_for({"path": str(local)}, use_path_paste=True)
    assert element["src"] == "url"


def test_without_path_paste_everything_is_uploaded(tmp_path):
    local = tmp_path / "shared.bed"
    local.write_text("chr1\t1\t2\n")
    element = _element_for({"path": str(local)}, use_path_paste=False)
    assert element["src"] == "files"
