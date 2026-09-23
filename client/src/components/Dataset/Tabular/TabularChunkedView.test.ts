import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TabularChunkedView from "./TabularChunkedView.vue";
import GTable from "@/components/Common/GTable.vue";

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

function mountChunkedView(fileExt: string) {
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
    beforeEach(() => {
        vi.stubGlobal("IntersectionObserver", VisibleIntersectionObserver);
        vi.mocked(axios.get).mockReset().mockResolvedValue(EOF_CHUNK);
    });

    it("hides the table header for generic tabular datasets", () => {
        const wrapper = mountChunkedView("tabular");

        expect(wrapper.findComponent(GTable).props("hideHeader")).toBe(true);
    });

    it("keeps the table header for CSV datasets", () => {
        const wrapper = mountChunkedView("csv");

        expect(wrapper.findComponent(GTable).props("hideHeader")).toBe(false);
    });

    it("loads chunks until the end of the dataset while the view is not filled", async () => {
        vi.mocked(axios.get)
            .mockResolvedValueOnce({ data: { ck_data: "a\t1\nb\t2\n", offset: 8, data_line_offset: 0 } })
            .mockResolvedValueOnce({ data: { ck_data: "c\t3\n", offset: 12, data_line_offset: 0 } });
        const wrapper = mountChunkedView("tabular");

        await vi.waitFor(() => expect(axios.get).toHaveBeenCalledTimes(3));
        expect(vi.mocked(axios.get).mock.calls.map(([, config]) => config?.params.offset)).toEqual([0, 8, 12]);
        await vi.waitFor(() => expect(wrapper.findComponent(GTable).props("items")).toHaveLength(3));
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
});
