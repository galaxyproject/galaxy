import { getLocalVue } from "@tests/vitest/helpers";
import { VisibleIntersectionObserver } from "@tests/vitest/visibleIntersectionObserver";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TabularChunkedView from "./TabularChunkedView.vue";

vi.mock("axios");
vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

enableAutoUnmount(afterEach);
afterEach(() => vi.unstubAllGlobals());

const EOF_CHUNK = { data: { ck_data: "", offset: 0, data_line_offset: 0 } };

function mountChunkedView(fileExt: string, ckData?: string) {
    if (ckData !== undefined) {
        vi.mocked(axios.get).mockResolvedValueOnce({
            data: { ck_data: ckData, offset: ckData.length, data_line_offset: 0 },
        });
    }
    return shallowMount(TabularChunkedView as object, {
        global: getLocalVue(),
        props: {
            options: {
                id: "dataset-id",
                file_ext: fileExt,
                metadata_columns: 2,
            },
        },
    });
}

async function renderedItems(fileExt: string, ckData: string) {
    const wrapper = mountChunkedView(fileExt, ckData);
    await vi.waitFor(() => expect(wrapper.findComponent({ name: "GTable" }).props("items")).not.toHaveLength(0));
    return wrapper.findComponent({ name: "GTable" }).props("items");
}

describe("TabularChunkedView", () => {
    beforeEach(() => {
        vi.stubGlobal("IntersectionObserver", VisibleIntersectionObserver);
        vi.mocked(axios.get).mockReset().mockResolvedValue(EOF_CHUNK);
    });

    it.each([
        { fileExt: "tabular", hideHeader: true },
        { fileExt: "csv", hideHeader: false },
    ])("sets hideHeader to $hideHeader for $fileExt datasets", ({ fileExt, hideHeader }) => {
        const wrapper = mountChunkedView(fileExt);

        expect(wrapper.findComponent({ name: "GTable" }).props("hideHeader")).toBe(hideHeader);
    });

    it("loads chunks until the end of the dataset while the view is not filled", async () => {
        vi.mocked(axios.get)
            .mockResolvedValueOnce({ data: { ck_data: "a\t1\nb\t2\n", offset: 8, data_line_offset: 0 } })
            .mockResolvedValueOnce({ data: { ck_data: "c\t3\n", offset: 12, data_line_offset: 0 } });
        const wrapper = mountChunkedView("tabular");

        await vi.waitFor(() => expect(axios.get).toHaveBeenCalledTimes(3));
        expect(
            vi.mocked(axios.get).mock.calls.map(([, config]) => (config?.params as { offset: number }).offset),
        ).toEqual([0, 8, 12]);
        await vi.waitFor(() => expect(wrapper.findComponent({ name: "GTable" }).props("items")).toHaveLength(3));
        // Wait beyond the infinite-scroll retry interval to verify that the terminal state stops fetching.
        await new Promise((resolve) => setTimeout(resolve, 250));
        expect(axios.get).toHaveBeenCalledTimes(3);
    });

    it("shows the error and stops requesting chunks when a chunk fails to load", async () => {
        vi.mocked(axios.get).mockRejectedValue(new Error("chunk request failed"));
        const wrapper = mountChunkedView("tabular");

        await vi.waitFor(() => expect(wrapper.text()).toContain("chunk request failed"));
        // Wait beyond the infinite-scroll retry interval to verify that the terminal state stops fetching.
        await new Promise((resolve) => setTimeout(resolve, 250));
        expect(axios.get).toHaveBeenCalledTimes(1);
    });

    it("keeps a comma inside a quoted CSV cell", async () => {
        expect(await renderedItems("csv", 'a,"b,c"\n')).toEqual([{ column_0: "a", column_1: "b,c" }]);
    });

    it("keeps a tab inside a quoted tabular cell", async () => {
        expect(await renderedItems("tabular", 'a\t"b\tc"\n')).toEqual([{ column_0: "a", column_1: "b\tc" }]);
    });

    it("falls back to per-line parsing when the chunk has ragged records", async () => {
        // Parsing the chunk as a whole raises CSV_RECORD_INCONSISTENT_FIELDS_LENGTH, so each line is
        // parsed on its own and the extra field is folded into the last column.
        expect(await renderedItems("csv", "a,b\nc,d,e\n")).toEqual([
            { column_0: "a", column_1: "b" },
            { column_0: "c", column_1: "d\te" },
        ]);
    });
});
