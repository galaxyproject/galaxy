import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TabularChunkedView from "./TabularChunkedView.vue";

vi.mock("axios");
vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

const localVue = getLocalVue();

const EOF_CHUNK = { data: { ck_data: "", offset: 0, data_line_offset: 0 } };

// jsdom has no IntersectionObserver; report every observed element as visible.
class VisibleIntersectionObserver {
    constructor(private callback: IntersectionObserverCallback) {}
    observe(target: Element) {
        this.callback([{ isIntersecting: true, time: 1, target } as IntersectionObserverEntry], this as never);
    }
    unobserve() {}
    disconnect() {}
}

// Mounted views keep loading chunks after a test ends; unmount them so they can't take the next test's responses.
const mounted: { unmount: () => void }[] = [];

function mountChunkedView(
    fileExt: string,
    {
        ckData,
        metadataColumnNames,
        chunkColumnNames,
    }: { ckData?: string; metadataColumnNames?: string[]; chunkColumnNames?: (string | null)[] } = {},
) {
    if (ckData !== undefined) {
        vi.mocked(axios.get).mockResolvedValueOnce({
            data: { ck_data: ckData, offset: ckData.length, data_line_offset: 0, column_names: chunkColumnNames },
        });
    }
    const wrapper = mount(TabularChunkedView as object, {
        localVue,
        propsData: {
            options: {
                id: "dataset-id",
                file_ext: fileExt,
                metadata_columns: 2,
                metadata_column_names: metadataColumnNames,
            },
        },
    });
    mounted.push(wrapper);
    return wrapper;
}

async function renderedItems(fileExt: string, ckData: string) {
    const wrapper = mountChunkedView(fileExt, { ckData });
    await vi.waitFor(() => expect(wrapper.findComponent({ name: "GTable" }).props("items")).not.toHaveLength(0));
    return wrapper.findComponent({ name: "GTable" }).props("items");
}

async function renderedView(fileExt: string, options: Parameters<typeof mountChunkedView>[1] = {}) {
    const wrapper = mountChunkedView(fileExt, { ckData: "chr1\t100\n", ...options });
    await vi.waitFor(() => expect(wrapper.findAll("tbody td")).not.toHaveLength(0));
    return wrapper;
}

function columnIndex(wrapper: ReturnType<typeof mountChunkedView>) {
    return wrapper.findAll("thead th").map((th) => ({
        number: th.find(".column-number").text(),
        name: th.find(".column-name").exists() ? th.find(".column-name").text() : null,
        title: th.find(".column-index").attributes("title"),
    }));
}

describe("TabularChunkedView", () => {
    beforeEach(() => {
        vi.stubGlobal("IntersectionObserver", VisibleIntersectionObserver);
        vi.mocked(axios.get).mockReset().mockResolvedValue(EOF_CHUNK);
    });

    afterEach(() => {
        mounted.splice(0).forEach((wrapper) => wrapper.unmount());
    });

    it.each(["tabular", "csv"])("numbers the columns of %s datasets", async (fileExt) => {
        const wrapper = await renderedView(fileExt);

        expect(columnIndex(wrapper)).toEqual([
            { number: "1", name: null, title: "Column 1. Galaxy metadata, not part of the file." },
            { number: "2", name: null, title: "Column 2. Galaxy metadata, not part of the file." },
        ]);
        expect(wrapper.findAll("tbody td").map((td) => td.text())).toEqual(["chr1", "100"]);
    });

    it("names the columns from metadata column names", async () => {
        const wrapper = await renderedView("tabular", { metadataColumnNames: ["GeneID", "Base mean"] });

        expect(columnIndex(wrapper)).toEqual([
            { number: "1", name: "GeneID", title: "Column 1: GeneID. Galaxy metadata, not part of the file." },
            { number: "2", name: "Base mean", title: "Column 2: Base mean. Galaxy metadata, not part of the file." },
        ]);
    });

    it("names the columns from the column names the server sends with the chunk", async () => {
        const wrapper = await renderedView("bed", { chunkColumnNames: ["Chrom", null] });

        expect(columnIndex(wrapper).map(({ number, name }) => [number, name])).toEqual([
            ["1", "Chrom"],
            ["2", null],
        ]);
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
        await new Promise((resolve) => setTimeout(resolve, 250));
        expect(axios.get).toHaveBeenCalledTimes(3);
    });

    it("shows the error and stops requesting chunks when a chunk fails to load", async () => {
        vi.mocked(axios.get).mockRejectedValue(new Error("chunk request failed"));
        const wrapper = mountChunkedView("tabular");

        await vi.waitFor(() => expect(wrapper.text()).toContain("chunk request failed"));
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
