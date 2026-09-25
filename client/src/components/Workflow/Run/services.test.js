import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VALID_INPUT_DATASET_STATES } from "@/api/datasets";

import { searchHistoryContents } from "./services";

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
