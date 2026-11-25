import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import { describe, expect, it, vi } from "vitest";

import type { TableField } from "@/components/Common/GTable.types";

import TabularChunkedView from "./TabularChunkedView.vue";
import GTable from "@/components/Common/GTable.vue";

vi.mock("axios");
vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

const localVue = getLocalVue();

function mountChunkedView(fileExt: string, metadataColumnNames?: string[]) {
    vi.mocked(axios.get).mockResolvedValue({ data: { ck_data: "", offset: 0, data_line_offset: 0 } });
    return shallowMount(TabularChunkedView as object, {
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
}

function fieldLabels(fields: TableField[]) {
    return fields.map((field) => field.label);
}

describe("TabularChunkedView", () => {
    it.each(["tabular", "csv"])("numbers the columns of %s datasets like the peek", (fileExt) => {
        const table = mountChunkedView(fileExt).findComponent(GTable);

        expect(table.props("hideHeader")).toBe(false);
        expect(fieldLabels(table.props("fields"))).toEqual(["1", "2"]);
    });

    it("adds metadata column names to the column numbers", () => {
        const table = mountChunkedView("tabular", ["GeneID", "Base mean"]).findComponent(GTable);

        expect(fieldLabels(table.props("fields"))).toEqual(["1.GeneID", "2.Base mean"]);
    });
});
