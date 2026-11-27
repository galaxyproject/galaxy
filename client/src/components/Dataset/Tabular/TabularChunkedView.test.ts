import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import TabularChunkedView from "./TabularChunkedView.vue";

vi.mock("axios");
vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

const localVue = getLocalVue();

async function mountChunkedView(
    fileExt: string,
    {
        metadataColumnNames,
        chunkColumnNames,
    }: { metadataColumnNames?: string[]; chunkColumnNames?: (string | null)[] } = {},
) {
    vi.mocked(axios.get).mockResolvedValue({
        data: { ck_data: "chr1\t100\n", offset: 9, data_line_offset: 0, column_names: chunkColumnNames },
    });
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
    await flushPromises();
    return wrapper;
}

function columnIndex(wrapper: Awaited<ReturnType<typeof mountChunkedView>>) {
    return wrapper.findAll("thead th").wrappers.map((th) => ({
        number: th.find(".column-number").text(),
        name: th.find(".column-name").exists() ? th.find(".column-name").text() : null,
        title: th.find(".column-index").attributes("title"),
    }));
}

describe("TabularChunkedView", () => {
    it.each(["tabular", "csv"])("numbers the columns of %s datasets", async (fileExt) => {
        const wrapper = await mountChunkedView(fileExt);

        expect(columnIndex(wrapper)).toEqual([
            { number: "1", name: null, title: "Column 1. Galaxy metadata, not part of the file." },
            { number: "2", name: null, title: "Column 2. Galaxy metadata, not part of the file." },
        ]);
        expect(wrapper.findAll("tbody td").wrappers.map((td) => td.text())).toEqual(["chr1", "100"]);
    });

    it("names the columns from metadata column names", async () => {
        const wrapper = await mountChunkedView("tabular", { metadataColumnNames: ["GeneID", "Base mean"] });

        expect(columnIndex(wrapper)).toEqual([
            { number: "1", name: "GeneID", title: "Column 1: GeneID. Galaxy metadata, not part of the file." },
            { number: "2", name: "Base mean", title: "Column 2: Base mean. Galaxy metadata, not part of the file." },
        ]);
    });

    it("names the columns from the column names the server sends with the chunk", async () => {
        const wrapper = await mountChunkedView("bed", { chunkColumnNames: ["Chrom", null] });

        expect(columnIndex(wrapper).map(({ number, name }) => [number, name])).toEqual([
            ["1", "Chrom"],
            ["2", null],
        ]);
    });
});
