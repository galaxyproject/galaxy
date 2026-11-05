import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { computed, ref } from "vue";

import HistoryStorageOverview from "./HistoryStorageOverview.vue";

vi.mock("vue-router", () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/composables/useObjectStores", () => ({
    useSelectableObjectStores: () => ({
        selectableObjectStores: ref([]),
        hasSelectableObjectStores: computed(() => false),
    }),
}));

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => ({
        getHistoryById: () => ({ id: "history-id", name: "Test history", purged: false, archived: false }),
        loadHistoryById: vi.fn(),
    }),
}));

vi.mock("./service", () => ({
    fetchHistoryContentsSizeSummary: vi.fn(async () => [
        { id: "active-dataset", name: "Active", size: 1024, deleted: false, purged: false },
        { id: "deleted-dataset", name: "Deleted", size: 2048, deleted: true, purged: false },
    ]),
}));

describe("HistoryStorageOverview", () => {
    it("keeps selection off on the active vs deleted chart", async () => {
        setActivePinia(createPinia());
        const wrapper = mount(HistoryStorageOverview as object, {
            props: { historyId: "history-id" },
            global: {
                ...getLocalVue(),
                stubs: { BarChart: true, BreadcrumbHeading: true, WarnDeletedDatasets: true },
            },
        });
        await flushPromises();

        const charts = wrapper.findAllComponents({ name: "BarChart" });
        expect(charts).toHaveLength(2);
        // Only the top-datasets chart lets you click through to a dataset.
        expect(charts[0]!.props("enableSelection")).toBe(true);
        expect(charts[1]!.props("enableSelection")).toBe(false);
        expect(charts[1]!.props("labelFormatter")).toBeTypeOf("function");
    });
});
