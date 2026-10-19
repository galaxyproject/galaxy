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

import DatasetActions from "./DatasetActions.vue";

vi.mock("@/api/datasets");

const localVue = getLocalVue();

const BASE_ITEM = {
    id: "dataset-id",
    state: "ok",
    accessible: true,
    deleted: false,
    purged: false,
} as any;

function mountActions(props: Record<string, unknown>) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);

    const historyStore = useHistoryStore();
    historyStore.setHistory(getFakeHistorySummary({ id: "current-history" }));
    historyStore.setCurrentHistoryId("current-history");

    return mount(DatasetActions as object, {
        localVue,
        router: createRouter({ history: createMemoryHistory(), routes: [] }),
        pinia,
        propsData: {
            item: BASE_ITEM,
            writable: true,
            showHighlight: false,
            itemUrls: {},
            ...props,
        },
    });
}

describe("DatasetActions copy to current history button", () => {
    it("does not render when the dataset is writable (owned)", () => {
        const wrapper = mountActions({ writable: true });
        expect(wrapper.find('[data-title="Copy to Current History"]').exists()).toBe(false);
    });

    it("renders when the dataset is not writable (unowned)", () => {
        const wrapper = mountActions({ writable: false });
        expect(wrapper.find('[data-title="Copy to Current History"]').exists()).toBe(true);
    });

    it("does not render for a deleted dataset, even if unowned", () => {
        const wrapper = mountActions({ writable: false, item: { ...BASE_ITEM, deleted: true } });
        expect(wrapper.find('[data-title="Copy to Current History"]').exists()).toBe(false);
    });

    it("does not render for a purged dataset, even if unowned", () => {
        const wrapper = mountActions({ writable: false, item: { ...BASE_ITEM, purged: true } });
        expect(wrapper.find('[data-title="Copy to Current History"]').exists()).toBe(false);
    });

    it("calls copyDataset with the dataset id and current history exactly once on click", async () => {
        vi.mocked(copyDataset).mockResolvedValue({ id: "new-dataset" } as never);

        const wrapper = mountActions({ writable: false });
        await wrapper.find('[data-title="Copy to Current History"]').trigger("click");
        await flushPromises();

        expect(copyDataset).toHaveBeenCalledOnce();
        expect(copyDataset).toHaveBeenCalledWith("dataset-id", "current-history", "dataset");
    });
});
