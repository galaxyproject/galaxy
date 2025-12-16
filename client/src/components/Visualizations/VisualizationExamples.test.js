import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { BDropdown, BDropdownItem } from "bootstrap-vue";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useToast } from "@/composables/toast";
import { createUrlUploadItem, uploadDatasets } from "@/utils/upload";

import UploadExamples from "./VisualizationExamples.vue";

vi.mock("@/utils/upload", () => ({
    createUrlUploadItem: vi.fn((url, historyId, options) => ({
        src: "url",
        url,
        historyId,
        name: options?.name ?? "default",
        ext: options?.ext ?? "auto",
    })),
    uploadDatasets: vi.fn(),
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
        expect(createUrlUploadItem).toHaveBeenCalledWith(urlData[0].url, "fake-history-id", {
            name: "Example 1",
            ext: urlData[0].ftype,
        });
        expect(uploadDatasets).toHaveBeenCalledWith(
            [
                expect.objectContaining({
                    src: "url",
                    url: urlData[0].url,
                    historyId: "fake-history-id",
                    name: "Example 1",
                    ext: urlData[0].ftype,
                }),
            ],
            {
                success: expect.any(Function),
                error: expect.any(Function),
            },
        );
        vi.mocked(uploadDatasets).mock.calls[0][1].success();
        expect(toastSuccess).toHaveBeenCalledWith("The sample dataset 'Example 1' is being uploaded to your history.");
    });

    it("shows error toast when upload fails", async () => {
        const wrapper = mount(UploadExamples, {
            global: localVue,
            props: { urlData },
        });
        const items = wrapper.findAllComponents(BDropdownItem);
        await items.at(1).find("a").trigger("click");
        vi.mocked(uploadDatasets).mock.calls[0][1].error();
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
