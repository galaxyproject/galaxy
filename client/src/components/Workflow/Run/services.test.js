import { nth } from "@tests/vitest/helpers";
import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { VALID_INPUT_DATASET_STATES } from "@/api/datasets";

import { getRunData, searchHistoryContents, WorkflowMissingToolsError } from "./services";

vi.mock("axios", () => ({
    default: {
        get: vi.fn(),
    },
}));

vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

const getRequest = vi.mocked(axios.get);

afterEach(() => {
    getRequest.mockReset();
});

/** ``q`` and ``qv`` are parallel arrays the backend zips positionally, so they
 * have to be asserted zipped — asserting each independently passes even when
 * every key is paired with the wrong value. */
function requestFilters() {
    const params = requestParams();
    const keys = params.getAll("q");
    const values = params.getAll("qv");
    expect(keys).toHaveLength(values.length);
    return Object.fromEntries(keys.map((key, index) => [key, values[index]]));
}

function requestParams() {
    return new URL(nth(nth(getRequest.mock.calls, 0), 0), "http://localhost").searchParams;
}

describe("searchHistoryContents", () => {
    beforeEach(() => {
        getRequest.mockReset();
        getRequest.mockResolvedValue({ data: [] });
    });

    it("preserves a workflow input tag when paging history contents", async () => {
        await searchHistoryContents("history-id", {
            type: "dataset",
            tag: "genomescope_model",
            offset: 50,
            limit: 50,
        });

        expect(requestFilters()).toMatchObject({
            "tag-eq": "genomescope_model",
            "history_content_type-eq": "dataset",
        });
        expect(requestParams().get("offset")).toBe("50");
    });

    it("omits the tag filter entirely when no tag is required", async () => {
        await searchHistoryContents("history-id", { type: "dataset" });

        expect(requestFilters()).not.toHaveProperty("tag-eq");
    });

    it("restricts datasets to input-eligible states", async () => {
        await searchHistoryContents("history-id", { type: "dataset" });

        expect(requestFilters()["state-in"]).toBe(VALID_INPUT_DATASET_STATES.join(","));
    });

    it("does not apply a dataset-state filter to collections", async () => {
        await searchHistoryContents("history-id", { type: "dataset_collection" });

        expect(requestFilters()).not.toHaveProperty("state-in");
    });

    it("drops the visibility filter when hidden items are offered", async () => {
        await searchHistoryContents("history-id", { type: "dataset_collection", visibleOnly: false });

        expect(requestFilters()).not.toHaveProperty("visible-eq");
    });

    it.each([
        { kind: "numeric hid", search: "42", filter: { "hid-eq": "42" } },
        { kind: "text name", search: "sample", filter: { "name-contains": "sample" } },
    ])("matches a $kind query against its corresponding filter", async ({ search, filter }) => {
        await searchHistoryContents("history-id", { type: "dataset", search });
        expect(requestFilters()).toMatchObject(filter);
    });

    it("comma-joins the accepted extensions", async () => {
        await searchHistoryContents("history-id", { type: "dataset", extensions: ["bam", "txt"] });

        expect(requestFilters()).toMatchObject({ "extension-in": "bam,txt" });
    });
});

describe("getRunData", () => {
    it("turns a missing-tools rejection into a WorkflowMissingToolsError", async () => {
        getRequest.mockRejectedValue({
            response: {
                status: 400,
                data: { err_msg: "Workflow cannot be run.", missing_tool_ids: ["fastqc", "bwa"] },
            },
        });

        const request = getRunData("abc");
        await expect(request).rejects.toBeInstanceOf(Error);
        const error = await request.catch((e) => e);

        expect(error).toBeInstanceOf(WorkflowMissingToolsError);
        expect(error.message).toBe("Workflow cannot be run.");
        expect(error.missingToolIds).toEqual(["fastqc", "bwa"]);
    });

    it("rethrows other failures as plain errors", async () => {
        getRequest.mockRejectedValue({
            response: { status: 403, data: { err_msg: "Workflow is not accessible." } },
        });

        const request = getRunData("abc");
        await expect(request).rejects.toBeInstanceOf(Error);
        const error = await request.catch((e) => e);

        expect(error).not.toBeInstanceOf(WorkflowMissingToolsError);
        expect(error.message).toBe("Workflow is not accessible.");
    });

    it("does not treat an empty missing_tool_ids list as missing tools", async () => {
        getRequest.mockRejectedValue({
            response: { status: 400, data: { err_msg: "Bad request.", missing_tool_ids: [] } },
        });

        const request = getRunData("abc");
        await expect(request).rejects.toBeInstanceOf(Error);
        const error = await request.catch((e) => e);

        expect(error).not.toBeInstanceOf(WorkflowMissingToolsError);
        expect(error.message).toBe("Bad request.");
    });
});
