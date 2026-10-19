import { createTestingPinia } from "@pinia/testing";
import { getFakeHistorySummary } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { copyDataset } from "@/api/datasets";
import { useHistoryStore } from "@/stores/historyStore";

import ContentOptions from "./ContentOptions.vue";

vi.mock("@/api/datasets");

const localVue = getLocalVue();

function mountOptions(props: Record<string, unknown>) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);

    const historyStore = useHistoryStore();
    historyStore.setHistory(getFakeHistorySummary({ id: "current-history" }));
    historyStore.setCurrentHistoryId("current-history");

    return mount(ContentOptions as object, {
        localVue,
        router: createRouter({ history: createMemoryHistory(), routes: [] }),
        pinia,
        propsData: {
            writable: false,
            isDataset: false,
            isDeleted: false,
            isHistoryItem: true,
            isVisible: true,
            itemUrls: {},
            itemId: "collection-id",
            ...props,
        },
    });
}

describe("ContentOptions copy to current history button", () => {
    it("renders for an unowned top-level collection", () => {
        const wrapper = mountOptions({});
        expect(wrapper.find(".copy-to-current-history-btn").exists()).toBe(true);
    });

    it("does not render when the collection is writable (owned)", () => {
        const wrapper = mountOptions({ writable: true });
        expect(wrapper.find(".copy-to-current-history-btn").exists()).toBe(false);
    });

    it("does not render for a dataset (handled separately by DatasetActions)", () => {
        const wrapper = mountOptions({ isDataset: true });
        expect(wrapper.find(".copy-to-current-history-btn").exists()).toBe(false);
    });

    it("does not render for a nested sub-collection (not a top-level history item)", () => {
        const wrapper = mountOptions({ isHistoryItem: false });
        expect(wrapper.find(".copy-to-current-history-btn").exists()).toBe(false);
    });

    it("does not render for a deleted collection, even if unowned", () => {
        const wrapper = mountOptions({ isDeleted: true });
        expect(wrapper.find(".copy-to-current-history-btn").exists()).toBe(false);
    });

    it("does not render without an item id", () => {
        const wrapper = mountOptions({ itemId: "" });
        expect(wrapper.find(".copy-to-current-history-btn").exists()).toBe(false);
    });

    it("calls copyDataset with the collection id and current history exactly once on click", async () => {
        vi.mocked(copyDataset).mockResolvedValue({ id: "new-collection" } as never);

        const wrapper = mountOptions({});
        await wrapper.find(".copy-to-current-history-btn").trigger("click");
        await flushPromises();

        expect(copyDataset).toHaveBeenCalledOnce();
        expect(copyDataset).toHaveBeenCalledWith("collection-id", "current-history", "dataset_collection");
    });
});
