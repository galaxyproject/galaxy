import { ref } from "vue";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import Multiselect from "vue-multiselect";

import SelectionField from "./SelectionField.vue";
import { getDataset } from "./services";

jest.mock("@/stores/eventStore", () => ({
    useEventStore: () => ({
        getDragItems: jest.fn(() => [{ id: "item1", name: "Item One", history_content_type: "dataset" }]),
    }),
}));

jest.mock("./services", () => ({
    getHistories: jest.fn(() => Promise.resolve([{ id: "1", name: "History One" }])),
    getDataset: jest.fn(() => Promise.resolve([{ id: "ds1", name: "Dataset A" }])),
    getDatasetCollection: jest.fn(),
    getInvocations: jest.fn(),
    getJobs: jest.fn(),
    getWorkflows: jest.fn(),
}));

const localVue = getLocalVue();
let mockedStore;

// Helper to wait for debounce + async resolution
const waitForDebouncedSearch = async () => {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await flushPromises();
};

jest.mock("@/stores/historyStore", () => {
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
        const mockQuery = jest.fn(() => Promise.resolve([{ id: "custom1", name: "Custom Result" }]));
        const wrapper = mountComponent({ objectQuery: mockQuery });
        await waitForDebouncedSearch();
        const multiselect = wrapper.findComponent(Multiselect);
        multiselect.vm.$emit("search-change", "test");
        await waitForDebouncedSearch();
        expect(mockQuery).toHaveBeenCalledWith("test");
    });
});
