import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { vi } from "vitest";
import { ref } from "vue";
import Multiselect from "vue-multiselect";

import { getDataset } from "./services";

import SelectionField from "./SelectionField.vue";

vi.mock("@/stores/eventStore", () => ({
    useEventStore: () => ({
        getDragItems: vi.fn(() => [{ id: "item1", name: "Item One", history_content_type: "dataset" }]),
    }),
}));

vi.mock("./services", () => ({
    getHistories: vi.fn(() => Promise.resolve([{ id: "1", name: "History One" }])),
    getDataset: vi.fn(() => Promise.resolve([{ id: "ds1", name: "Dataset A" }])),
    getDatasetCollection: vi.fn(),
    getInvocations: vi.fn(),
    getJobs: vi.fn(),
    getWorkflows: vi.fn(),
}));

const localVue = getLocalVue();
let mockedStore;

// Helper to wait for debounce + async resolution
const waitForDebouncedSearch = async () => {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await flushPromises();
};

vi.mock("@/stores/historyStore", () => {
    return {
        useHistoryStore: () => mockedStore,
    };
});

function mountComponent(props = {}) {
    return mount(SelectionField, {
        localVue,
        propsData: {
            objectType: "history_dataset_id",
            ...props,
        },
    });
}

beforeEach(() => {
    setActivePinia(createPinia());
    const useFakeHistoryStore = defineStore("history", {
        state: () => ({
            currentHistoryId: ref("history123"),
        }),
    });
    mockedStore = useFakeHistoryStore();
});

describe("SelectionField.vue", () => {
    it("renders label and multiselect when ready", async () => {
        const wrapper = mountComponent({ objectName: "My Dataset", objectId: "ds1" });
        await waitForDebouncedSearch();
        const label = wrapper.find("label");
        expect(label.exists()).toBe(true);
        expect(label.text()).toContain("Select a History Dataset Id");
        expect(wrapper.findComponent(Multiselect).exists()).toBeTruthy();
    });

    it("renders empty state when no data found", async () => {
        getDataset.mockImplementationOnce(() => Promise.resolve([]));
        const wrapper = mountComponent();
        await waitForDebouncedSearch();
        expect(wrapper.text()).toContain("No datasets found in your current history");
    });

    it("triggers search when input changes", async () => {
        const wrapper = mountComponent();
        await waitForDebouncedSearch();
        const multiselect = wrapper.findComponent(Multiselect);
        expect(multiselect.exists()).toBe(true);
        multiselect.vm.$emit("search-change", "abc");
        await waitForDebouncedSearch();
        expect(getDataset).toHaveBeenCalledWith("abc", "history123");
    });

    it("shows error if service throws", async () => {
        getDataset.mockImplementationOnce(() => {
            throw new Error("Oops!");
        });
        const wrapper = mountComponent();
        await waitForDebouncedSearch();
        expect(wrapper.text()).toContain("Oops!");
    });

    it("handles dragenter and drop", async () => {
        const wrapper = mountComponent();
        await waitForDebouncedSearch();
        expect(wrapper.classes()).not.toContain("ui-dragover-success");
        await wrapper.trigger("dragenter");
        expect(wrapper.classes()).toContain("ui-dragover-success");
        await wrapper.trigger("drop");
        expect(wrapper.classes()).not.toContain("ui-dragover-success");
        expect(wrapper.emitted("change")).toEqual([[{ id: "item1", name: "Item One" }]]);
    });

    it("uses custom objectQuery function when provided", async () => {
        const mockQuery = vi.fn(() => Promise.resolve([{ id: "custom1", name: "Custom Result" }]));
        const wrapper = mountComponent({ objectQuery: mockQuery });
        await waitForDebouncedSearch();
        const multiselect = wrapper.findComponent(Multiselect);
        multiselect.vm.$emit("search-change", "test");
        await waitForDebouncedSearch();
        expect(mockQuery).toHaveBeenCalledWith("test");
    });

    it("falls back to first option if no objectId and objectName provided", async () => {
        const wrapper = mountComponent({ objectId: "", objectName: "" });
        await waitForDebouncedSearch();
        const multiselect = wrapper.findComponent(Multiselect);
        expect(multiselect.exists()).toBe(true);
        const multiselectOptions = multiselect.props("options");
        expect(multiselectOptions.length).toBeGreaterThan(0);
        await wrapper.vm.$nextTick();
        const currentValue = wrapper.vm.currentValue;
        expect(currentValue.id).toBe("ds1");
        expect(currentValue.name).toBe("Dataset A");
    });
});
