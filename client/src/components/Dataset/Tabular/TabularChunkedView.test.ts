import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import { describe, expect, it, vi } from "vitest";

import TabularChunkedView from "./TabularChunkedView.vue";
import GTable from "@/components/Common/GTable.vue";

vi.mock("axios");
vi.mock("@/onload/loadConfig", () => ({
    getAppRoot: () => "/",
}));

const localVue = getLocalVue();

function mountChunkedView(fileExt: string) {
    vi.mocked(axios.get).mockResolvedValue({ data: { ck_data: "", offset: 0, data_line_offset: 0 } });
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

describe("TabularChunkedView", () => {
    it("hides the table header for generic tabular datasets", () => {
        const wrapper = mountChunkedView("tabular");

        expect(wrapper.findComponent(GTable).props("hideHeader")).toBe(true);
    });

    it("keeps the table header for CSV datasets", () => {
        const wrapper = mountChunkedView("csv");

        expect(wrapper.findComponent(GTable).props("hideHeader")).toBe(false);
    });
});
