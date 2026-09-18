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

/** ``q`` and ``qv`` are parallel arrays the backend zips positionally, so they
 * have to be asserted zipped — asserting each independently passes even when
 * every key is paired with the wrong value. */
function requestFilters() {
    const url = new URL(axios.get.mock.calls[0][0], "http://localhost");
    const keys = url.searchParams.getAll("q");
    const values = url.searchParams.getAll("qv");
    expect(keys).toHaveLength(values.length);
    return Object.fromEntries(keys.map((key, index) => [key, values[index]]));
}

function requestParams() {
    return new URL(axios.get.mock.calls[0][0], "http://localhost").searchParams;
}

describe("searchHistoryContents", () => {
    beforeEach(() => {
        axios.get.mockReset();
        axios.get.mockResolvedValue({ data: [] });
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

    it("matches a numeric query against the hid and a text query against the name", async () => {
        await searchHistoryContents("history-id", { type: "dataset", search: "42" });
        expect(requestFilters()).toMatchObject({ "hid-eq": "42" });

        axios.get.mockClear();
        await searchHistoryContents("history-id", { type: "dataset", search: "sample" });
        expect(requestFilters()).toMatchObject({ "name-contains": "sample" });
    });

    it("comma-joins the accepted extensions", async () => {
        await searchHistoryContents("history-id", { type: "dataset", extensions: ["bam", "txt"] });

        expect(requestFilters()).toMatchObject({ "extension-in": "bam,txt" });
    });
});

describe("getRunData", () => {
    afterEach(() => {
        vi.mocked(axios.get).mockReset();
    });

    it("turns a missing-tools rejection into a WorkflowMissingToolsError", async () => {
        vi.mocked(axios.get).mockRejectedValue({
            response: {
                status: 400,
                data: { err_msg: "Workflow cannot be run.", missing_tool_ids: ["fastqc", "bwa"] },
            },
        });

        const error = await getRunData("abc").catch((e) => e);

        expect(error).toBeInstanceOf(WorkflowMissingToolsError);
        expect(error.message).toBe("Workflow cannot be run.");
        expect(error.missingToolIds).toEqual(["fastqc", "bwa"]);
    });

    it("rethrows other failures as plain errors", async () => {
        vi.mocked(axios.get).mockRejectedValue({
            response: { status: 403, data: { err_msg: "Workflow is not accessible." } },
        });

        const error = await getRunData("abc").catch((e) => e);

        expect(error).not.toBeInstanceOf(WorkflowMissingToolsError);
        expect(error.message).toBe("Workflow is not accessible.");
    });

    it("does not treat an empty missing_tool_ids list as missing tools", async () => {
        vi.mocked(axios.get).mockRejectedValue({
            response: { status: 400, data: { err_msg: "Bad request.", missing_tool_ids: [] } },
        });

        const error = await getRunData("abc").catch((e) => e);

        expect(error).not.toBeInstanceOf(WorkflowMissingToolsError);
        expect(error.message).toBe("Bad request.");
    });
});
