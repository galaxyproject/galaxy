import { mount } from "@vue/test-utils";
import { BDropdown, BDropdownItem } from "bootstrap-vue";
import { useToast } from "composables/toast";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import { ref } from "vue";

import UploadExamples from "./VisualizationExamples.vue";

jest.mock("@/utils/upload-payload.js", () => ({
    uploadPayload: jest.fn(() => "mockedPayload"),
}));

jest.mock("@/utils/upload-submit.js", () => ({
    sendPayload: jest.fn(),
}));

jest.mock("@/composables/toast");
const toastSuccess = jest.fn();
const toastError = jest.fn();
useToast.mockReturnValue({
    success: toastSuccess,
    error: toastError,
});

let mockedStore;
jest.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => mockedStore,
}));

const localVue = getLocalVue();

describe("UploadExamples.vue", () => {
    const urlData = [
        { name: "Example 1", url: "https://example.com/data1.txt" },
        { name: "Example 2", url: "https://example.com/data2.txt" },
    ];

    beforeEach(() => {
        setActivePinia(createPinia());
        const useFakeHistoryStore = defineStore("history", {
            state: () => ({
                currentHistoryId: ref("fake-history-id"),
            }),
        });
        mockedStore = useFakeHistoryStore();
    });

    it("renders loading spinner when no historyId", () => {
        mockedStore.currentHistoryId = ref(null);
        const wrapper = mount(UploadExamples, {
            localVue,
            propsData: { urlData },
        });
        expect(wrapper.find("svg").exists()).toBe(true);
    });

    it("renders dropdown with upload options", () => {
        const wrapper = mount(UploadExamples, {
            localVue,
            propsData: { urlData },
        });
        const items = wrapper.findAllComponents(BDropdownItem);
        expect(items.length).toBe(urlData.length);
        expect(wrapper.text()).toContain("Example 1");
        expect(wrapper.text()).toContain("Example 2");
    });

    it("calls upload and shows success toast on item click", async () => {
        const { uploadPayload } = require("@/utils/upload-payload.js");
        const { sendPayload } = require("@/utils/upload-submit.js");
        const wrapper = mount(UploadExamples, {
            localVue,
            propsData: { urlData },
        });
        const items = wrapper.findAllComponents(BDropdownItem);
        await items.at(0).find("a").trigger("click");
        expect(uploadPayload).toHaveBeenCalledWith([{ fileMode: "new", fileUri: urlData[0].url }], "fake-history-id");
        expect(sendPayload).toHaveBeenCalledWith("mockedPayload", {
            success: expect.any(Function),
            error: expect.any(Function),
        });
        sendPayload.mock.calls[0][1].success();
        expect(toastSuccess).toHaveBeenCalledWith("The sample dataset 'Example 1' is being uploaded to your history.");
    });

    it("shows error toast when upload fails", async () => {
        const { sendPayload } = require("@/utils/upload-submit.js");
        const wrapper = mount(UploadExamples, {
            localVue,
            propsData: { urlData },
        });
        const items = wrapper.findAllComponents(BDropdownItem);
        await items.at(1).find("a").trigger("click");
        sendPayload.mock.calls[0][1].error();
        expect(toastError).toHaveBeenCalledWith("Uploading the sample dataset 'Example 2' has failed.");
    });

    it("does not render dropdown if urlData is missing", () => {
        const wrapper = mount(UploadExamples, {
            localVue,
            propsData: {},
        });
        expect(wrapper.findComponent(BDropdown).exists()).toBe(false);
    });

    it("reacts to history ID becoming available", async () => {
        mockedStore.currentHistoryId = ref(null);
        const wrapper = mount(UploadExamples, {
            localVue,
            propsData: { urlData },
        });
        expect(wrapper.find("svg").exists()).toBe(true);
        mockedStore.currentHistoryId = ref("new-history-id");
        await wrapper.vm.$nextTick();
        const items = wrapper.findAllComponents(BDropdownItem);
        expect(items.length).toBe(urlData.length);
    });
});
