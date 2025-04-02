import { mount } from "@vue/test-utils";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import ConfigureSelector from "./ConfigureSelector.vue";

jest.mock("@/stores/eventStore", () => ({
    useEventStore: () => ({
        getDragItems: jest.fn(() => [{ id: "item1", name: "Item One", history_content_type: "dataset" }]),
    }),
}));

jest.mock("@/components/Markdown/services", () => ({
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
    return mount(ConfigureSelector, {
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

describe("ConfigureSelector.vue", () => {
    it("renders label and multiselect when ready", async () => {
        const wrapper = mountComponent({ objectName: "My Dataset", objectId: "ds1" });
        await wrapper.vm.$nextTick();
        expect(wrapper.find("label").text()).toContain("Select a History Dataset Id");
        expect(wrapper.find(".multiselect").exists()).toBe(true);
    });

    it("renders empty state when no data found", async () => {
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("No elements found");
    });
});
