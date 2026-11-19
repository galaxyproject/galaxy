"""Exercise a dataset default against a running Galaxy server.

Set GALAXY_PLAYWRIGHT_URL, GALAXY_PLAYWRIGHT_USER and GALAXY_PLAYWRIGHT_PASSWORD,
then run pytest --noconftest test/playwright/test_workflow_default_location.py.
Use pytest-playwright's --video=on to record the same test.
"""

import os
import time
from uuid import uuid4

import pytest
from playwright.sync_api import (
    expect,
    Page,
)

GALAXY_URL = os.environ.get("GALAXY_PLAYWRIGHT_URL")
GALAXY_USER = os.environ.get("GALAXY_PLAYWRIGHT_USER")
GALAXY_PASSWORD = os.environ.get("GALAXY_PLAYWRIGHT_PASSWORD")
LOCATION = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed"


def pause_for_video(page: Page):
    if os.environ.get("GALAXY_PLAYWRIGHT_DEMO"):
        page.wait_for_timeout(1200)


@pytest.mark.skipif(
    not (GALAXY_URL and GALAXY_USER and GALAXY_PASSWORD),
    reason="Set GALAXY_PLAYWRIGHT_URL, GALAXY_PLAYWRIGHT_USER and GALAXY_PLAYWRIGHT_PASSWORD",
)
@pytest.mark.browser_context_args(viewport={"width": 1280, "height": 720}, record_video_size={"width": 1280, "height": 720})
def test_dataset_default_location_editor_and_run(page: Page):
    assert GALAXY_URL is not None
    assert GALAXY_USER is not None
    assert GALAXY_PASSWORD is not None
    page.set_default_timeout(60_000)
    page.goto(f"{GALAXY_URL}/login/start", wait_until="domcontentloaded")
    page.locator("#login-form-name").fill(GALAXY_USER)
    page.locator("#login-form-password").fill(GALAXY_PASSWORD)
    page.locator("#login button[type=submit]").click()
    expect(page.locator("#login-form-name")).to_have_count(0)

    # Ensure there is a selectable alternative even with an otherwise empty history.
    history_response = page.request.get(f"{GALAXY_URL}/history/current_history_json")
    assert history_response.ok, history_response.text()
    history_id = history_response.json()["id"]
    alternative_name = f"Alternative metadata {uuid4().hex[:8]}.txt"
    fetch = page.request.post(
        f"{GALAXY_URL}/api/tools/fetch",
        data={
            "history_id": history_id,
            "targets": [
                {
                    "destination": {"type": "hdas"},
                    "items": [{"src": "pasted", "paste_content": "alternative\n", "name": alternative_name}],
                }
            ],
        },
    )
    assert fetch.ok, fetch.text()
    alternative_id = fetch.json()["outputs"][0]["id"]
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        alternative = page.request.get(f"{GALAXY_URL}/api/histories/{history_id}/contents/{alternative_id}")
        assert alternative.ok, alternative.text()
        state = alternative.json()["state"]
        if state == "ok":
            break
        assert state not in ("error", "discarded"), alternative.json()
        time.sleep(1)
    else:
        pytest.fail("Alternative dataset did not become ready within 120 seconds")

    # Create a connected workflow through Galaxy's API; all edits and the run
    # below go through the real browser UI and are persisted by the server.
    response = page.request.post(
        f"{GALAXY_URL}/api/workflows",
        data={
            "workflow": {
                "class": "GalaxyWorkflow",
                "name": f"Reference metadata {uuid4().hex[:8]}",
                "inputs": {"reference": "data"},
                "steps": {"copy": {"tool_id": "cat1", "in": {"input1": "reference"}}},
            }
        },
    )
    assert response.ok, response.text()
    workflow_id = response.json()["id"]
    page.goto(f"{GALAXY_URL}/workflows/edit?id={workflow_id}", wait_until="domcontentloaded")
    page.get_by_text("1: reference", exact=True).click()
    field = page.locator("#__default_location")
    expect(field).to_be_visible()
    pause_for_video(page)
    field.fill(LOCATION)
    pause_for_video(page)
    with page.expect_response(
        lambda r: r.request.method == "PUT" and f"/api/workflows/{workflow_id}" in r.url
    ) as save_response:
        page.locator("#workflow-save-button").click()
    assert save_response.value.ok, save_response.value.text()
    expect(page.get_by_text("No changes to save.")).to_be_visible()
    pause_for_video(page)

    # Check the server's persisted representation, then reopen the editor.
    saved = page.request.get(f"{GALAXY_URL}/api/workflows/{workflow_id}/download?style=editor")
    assert saved.ok, saved.text()
    assert saved.json()["steps"]["0"]["in"]["input"]["default"] == {"class": "File", "location": LOCATION}
    page.reload(wait_until="domcontentloaded")
    page.get_by_text("1: reference", exact=True).click()
    expect(page.locator("#__default_location")).to_have_value(LOCATION)
    pause_for_video(page)

    page.get_by_text("Run", exact=True).first.click()
    expect(page.get_by_text("Using default file", exact=True)).to_be_visible()
    expect(page.get_by_text(LOCATION, exact=True)).to_be_visible()
    expect(page.get_by_text("Use default file", exact=True)).to_be_visible()
    page.locator(".form-data .multiselect__select").first.click()
    page.get_by_role("option").filter(has_text=alternative_name).click()
    expect(page.get_by_text("Using selected dataset", exact=True)).to_be_visible()
    pause_for_video(page)
    page.locator(".form-data .multiselect__select").first.click()
    page.get_by_role("option", name="Use default file").click()
    expect(page.get_by_text("Using default file", exact=True)).to_be_visible()
    page.locator(".workflow-run-settings").click()
    page.locator(".workflow-expand-form-link").click()
    expect(page.get_by_text("Using default file", exact=True)).to_be_visible()
    expect(page.get_by_text("Use default file", exact=True)).to_be_visible()
    pause_for_video(page)
    page.get_by_text("Simple Form", exact=True).click()
    expect(page.get_by_text("Using default file", exact=True)).to_be_visible()
    pause_for_video(page)
    with page.expect_response(
        lambda r: r.request.method == "POST" and f"/api/workflows/{workflow_id}/invocations" in r.url
    ) as invoke_response:
        page.locator("#run-workflow").click()
    assert invoke_response.value.ok, invoke_response.value.text()
    invocations = invoke_response.value.json()
    invocation = invocations[0] if isinstance(invocations, list) else invocations
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        detail_response = page.request.get(f"{GALAXY_URL}/api/invocations/{invocation['id']}?step_details=true")
        assert detail_response.ok, detail_response.text()
        detail = detail_response.json()
        if detail["state"] == "completed":
            break
        assert detail["state"] not in ("failed", "cancelled"), detail
        time.sleep(1)
    else:
        pytest.fail("Workflow did not complete within 120 seconds")

    copy_step = next(step for step in detail["steps"] if step["workflow_step_label"] == "copy")
    assert copy_step["jobs"][0]["state"] == "ok"
    output_id = copy_step["outputs"]["out_file1"]["id"]
    output = page.request.get(f"{GALAXY_URL}/api/histories/{detail['history_id']}/contents/{output_id}/display")
    assert output.ok, output.text()
    assert "chr1" in output.text()
    pause_for_video(page)
