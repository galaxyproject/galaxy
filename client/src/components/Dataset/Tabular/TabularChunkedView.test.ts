import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TabularChunkedView from "./TabularChunkedView.vue";
import GTable from "@/components/Common/GTable.vue";

vi.mock("axios");
vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

const localVue = getLocalVue();

const EMPTY_CHUNK = { data: { ck_data: "", offset: 0, data_line_offset: 0 } };

function mountChunkedView(fileExt: string, ckData?: string) {
    if (ckData !== undefined) {
        vi.mocked(axios.get).mockResolvedValueOnce({
            data: { ck_data: ckData, offset: ckData.length, data_line_offset: 0 },
        });
    }
    // Galaxy signals the end of the dataset with an empty chunk.
    vi.mocked(axios.get).mockResolvedValue(EMPTY_CHUNK);
    return shallowMount(TabularChunkedView as object, {
        localVue,
        propsData: {
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
    await flushPromises();
    return wrapper.findComponent(GTable).props("items");
}

beforeEach(() => {
    vi.mocked(axios.get).mockReset();
});

describe("TabularChunkedView", () => {
    it("hides the table header for generic tabular datasets", () => {
        const wrapper = mountChunkedView("tabular");

        expect(wrapper.findComponent(GTable).props("hideHeader")).toBe(true);
    });

    it("keeps the table header for CSV datasets", () => {
        const wrapper = mountChunkedView("csv");

        expect(wrapper.findComponent(GTable).props("hideHeader")).toBe(false);
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
