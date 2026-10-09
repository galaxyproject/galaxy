import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { createPinia, defineStore } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { Toast } from "@/composables/toast";
import { createUrlUploadItem, uploadDatasets } from "@/utils/upload";

import VisualizationExamples from "./VisualizationExamples.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

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

let historyStore;
vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => historyStore,
}));

const localVue = getLocalVue();
const historyId = "fake-history-id";
const useFakeHistoryStore = defineStore("history", {
    state: () => ({ currentHistoryId: historyId }),
});
const tabularExample = { name: "Example 1", url: "https://example.com/data1.txt", ftype: "tabular" };
const autoDetectedExample = { name: "Example 2", url: "https://example.com/data2.txt" };
const examples = [tabularExample, autoDetectedExample];

let pinia;

function mountExamples(props = { urlData: examples }) {
    // Keep the dropdown and its items real to exercise slot rendering and DOM click forwarding.
    return mount(VisualizationExamples, {
        global: withPlugins(localVue, pinia),
        props,
    });
}

async function selectExample(wrapper, name) {
    await wrapper.get('[aria-label="Upload Examples"]').trigger("click");
    const item = wrapper.findAllComponents(GDropdownItem).find((item) => item.text() === name);
    expect(item, `Upload example "${name}" should be available`).toBeDefined();
    await item.get("a").trigger("click");
}

enableAutoUnmount(afterEach);

describe("VisualizationExamples.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        pinia = createPinia();
        historyStore = useFakeHistoryStore(pinia);
    });

    it("shows a loading spinner while no history is available", () => {
        historyStore.currentHistoryId = null;
        const wrapper = mountExamples();

        expect(wrapper.find("svg[data-icon='spinner']").exists()).toBe(true);
    });

    it("lists each example by name in the upload dropdown", () => {
        const wrapper = mountExamples();
        const items = wrapper.findAllComponents(GDropdownItem);

        expect(items).toHaveLength(examples.length);
        expect(wrapper.text()).toContain(tabularExample.name);
        expect(wrapper.text()).toContain(autoDetectedExample.name);
    });

    it("submits the selected example with its specified datatype to the current history", async () => {
        const wrapper = mountExamples();

        await selectExample(wrapper, tabularExample.name);

        expect(createUrlUploadItem).toHaveBeenCalledWith(tabularExample.url, historyId, {
            name: tabularExample.name,
            ext: tabularExample.ftype,
        });
        expect(uploadDatasets).toHaveBeenCalledExactlyOnceWith(
            [
                expect.objectContaining({
                    src: "url",
                    url: tabularExample.url,
                    historyId,
                    name: tabularExample.name,
                    ext: tabularExample.ftype,
                }),
            ],
            {
                success: expect.any(Function),
                error: expect.any(Function),
            },
        );
    });

    it("announces the selected example when its upload succeeds", async () => {
        const wrapper = mountExamples();
        await selectExample(wrapper, tabularExample.name);
        expect(uploadDatasets).toHaveBeenCalledOnce();
        const [, { success }] = nth(vi.mocked(uploadDatasets).mock.calls, 0);

        success();

        expect(Toast.success).toHaveBeenCalledWith("The sample dataset 'Example 1' is being uploaded to your history.");
    });

    it("reports the selected example when its upload fails", async () => {
        const wrapper = mountExamples();
        await selectExample(wrapper, autoDetectedExample.name);
        expect(uploadDatasets).toHaveBeenCalledOnce();
        const [, { error }] = nth(vi.mocked(uploadDatasets).mock.calls, 0);

        error();

        expect(Toast.error).toHaveBeenCalledWith("Uploading the sample dataset 'Example 2' has failed.");
    });

    it("hides the upload dropdown when example data is missing", () => {
        const wrapper = mountExamples({});

        expect(wrapper.findComponent(GDropdown).exists()).toBe(false);
    });

    it("replaces the loading spinner with example options once a history becomes available", async () => {
        historyStore.currentHistoryId = null;
        const wrapper = mountExamples();
        expect(wrapper.find("svg[data-icon='spinner']").exists()).toBe(true);

        historyStore.currentHistoryId = "new-history-id";
        await nextTick();

        expect(wrapper.findAllComponents(GDropdownItem)).toHaveLength(examples.length);
        expect(wrapper.find("svg[data-icon='spinner']").exists()).toBe(false);
    });
});
