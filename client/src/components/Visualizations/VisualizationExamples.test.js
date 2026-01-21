import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { BDropdown, BDropdownItem } from "bootstrap-vue";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useToast } from "@/composables/toast";
import { uploadPayload } from "@/utils/upload-payload.js";
import { sendPayload } from "@/utils/upload-submit.js";

import UploadExamples from "./VisualizationExamples.vue";

vi.mock("@/utils/upload-payload.js", () => ({
    uploadPayload: vi.fn(() => "mockedPayload"),
}));

vi.mock("@/utils/upload-submit.js", () => ({
    sendPayload: vi.fn(),
}));

vi.mock("@/composables/toast");
const toastSuccess = vi.fn();
const toastError = vi.fn();
useToast.mockReturnValue({
    success: toastSuccess,
    error: toastError,
});

let mockedStore;
vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => mockedStore,
}));

const localVue = getLocalVue();

describe("UploadExamples.vue", () => {
    const urlData = [
        { name: "Example 1", url: "https://example.com/data1.txt", ftype: "tabular" },
        { name: "Example 2", url: "https://example.com/data2.txt" },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
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
            global: localVue,
            props: { urlData },
        });
        expect(wrapper.find("svg").exists()).toBe(true);
    });

    it("renders dropdown with upload options", () => {
        const wrapper = mount(UploadExamples, {
            global: localVue,
            props: { urlData },
        });
        const items = wrapper.findAllComponents(BDropdownItem);
        expect(items.length).toBe(urlData.length);
        expect(wrapper.text()).toContain("Example 1");
        expect(wrapper.text()).toContain("Example 2");
    });

    it("calls upload and shows success toast on item click", async () => {
        const wrapper = mount(UploadExamples, {
            global: localVue,
            props: { urlData },
        });
        const items = wrapper.findAllComponents(BDropdownItem);
        await items.at(0).find("a").trigger("click");
        expect(uploadPayload).toHaveBeenCalledWith(
            [{ fileMode: "new", fileName: "Example 1", fileUri: urlData[0].url, extension: urlData[0].ftype }],
            "fake-history-id",
        );
        expect(sendPayload).toHaveBeenCalledWith("mockedPayload", {
            success: expect.any(Function),
            error: expect.any(Function),
        });
        vi.mocked(sendPayload).mock.calls[0][1].success();
        expect(toastSuccess).toHaveBeenCalledWith("The sample dataset 'Example 1' is being uploaded to your history.");
    });

    it("shows error toast when upload fails", async () => {
        const wrapper = mount(UploadExamples, {
            global: localVue,
            props: { urlData },
        });
        const items = wrapper.findAllComponents(BDropdownItem);
        await items.at(1).find("a").trigger("click");
        vi.mocked(sendPayload).mock.calls[0][1].error();
        expect(toastError).toHaveBeenCalledWith("Uploading the sample dataset 'Example 2' has failed.");
    });

    it("does not render dropdown if urlData is missing", () => {
        const wrapper = mount(UploadExamples, {
            global: localVue,
            props: {},
        });
        expect(wrapper.findComponent(BDropdown).exists()).toBe(false);
    });

    it("reacts to history ID becoming available", async () => {
        mockedStore.currentHistoryId = ref(null);
        const wrapper = mount(UploadExamples, {
            global: localVue,
            props: { urlData },
        });
        expect(wrapper.find("svg").exists()).toBe(true);
        mockedStore.currentHistoryId = ref("new-history-id");
        await wrapper.vm.$nextTick();
        const items = wrapper.findAllComponents(BDropdownItem);
        expect(items.length).toBe(urlData.length);
    });
});
