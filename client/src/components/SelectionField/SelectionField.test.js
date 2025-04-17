import { mount } from "@vue/test-utils";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import Multiselect from "vue-multiselect";

import { getDataset } from "./services";

import SelectionField from "./SelectionField.vue";

jest.mock("@/stores/eventStore", () => ({
    useEventStore: () => ({
        getDragItems: jest.fn(() => [{ id: "item1", name: "Item One", history_content_type: "dataset" }]),
    }),
}));

jest.mock("./services", () => ({
    getHistories: jest.fn(() => Promise.resolve([{ id: "1", name: "History One" }])),
    getDataset: jest.fn(() => Promise.resolve([{ id: "ds1", name: "Dataset A" }])),
    getInvocations: jest.fn(),
    getJobs: jest.fn(),
    getWorkflows: jest.fn(),
}));

const localVue = getLocalVue();
let mockedStore;

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
            currentHistoryId: "history123",
        }),
    });
    mockedStore = useFakeHistoryStore();
});

describe("SelectionField.vue", () => {
    it("renders label and multiselect when ready", async () => {
        const wrapper = mountComponent({ objectName: "My Dataset", objectId: "ds1" });
        expect(wrapper.find("label").text()).toContain("Select a History Dataset Id");
        expect(wrapper.findComponent(Multiselect).exists()).toBeTruthy();
    });

    it("renders empty state when no data found", async () => {
        const wrapper = mountComponent();
        expect(wrapper.text()).toContain("No elements found");
    });

    it("triggers search when input changes", async () => {
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        const multiselect = wrapper.findComponent(Multiselect);
        expect(multiselect.exists()).toBe(true);
        multiselect.vm.$emit("search-change", "abc");
        await new Promise((resolve) => setTimeout(resolve, 400));
        expect(getDataset).toHaveBeenCalledWith("abc", "history123");
    });

    it("shows error if service throws", async () => {
        const original = getDataset.mockImplementation;
        getDataset.mockImplementationOnce(() => {
            throw new Error("Oops!");
        });
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 400));
        expect(wrapper.text()).toContain("Oops!");
        getDataset.mockImplementation = original;
    });

    it("handles dragenter and drop", async () => {
        const wrapper = mountComponent();
        expect(wrapper.classes()).not.toContain("ui-dragover-success");
        await wrapper.trigger("dragenter");
        expect(wrapper.classes()).toContain("ui-dragover-success");
        await wrapper.trigger("drop");
        expect(wrapper.classes()).not.toContain("ui-dragover-success");
        expect(wrapper.emitted("change")).toEqual([[{ id: "item1", name: "Item One" }]]);
    });

    it("uses custom objectQuery function when provided", async () => {
        const mockQuery = jest.fn(() =>
            Promise.resolve([{ id: "custom1", name: "Custom Result" }])
        );
        const wrapper = mountComponent({
            objectQuery: mockQuery,
        });
        await wrapper.vm.$nextTick();
        // Trigger search
        const multiselect = wrapper.findComponent(Multiselect);
        multiselect.vm.$emit("search-change", "test");
        await new Promise((resolve) => setTimeout(resolve, 400));
        expect(mockQuery).toHaveBeenCalledWith("test");
    });
});
