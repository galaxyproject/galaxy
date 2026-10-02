import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import PasteLinksUpload from "./PasteLinksUpload.vue";

vi.mock("@/composables/upload/uploadDefaults", () => ({
    useUploadDefaults: () => ({
        effectiveExtensions: ref([]),
        listDbKeys: ref([]),
        configurationsReady: ref(true),
        createItemDefaults: () => ({
            extension: "auto",
            dbkey: "?",
            spaceToTab: false,
            toPosixLines: false,
            autoDecompress: true,
        }),
    }),
}));

const localVue = getLocalVue();

const SELECTORS = {
    textarea: "#paste-links-textarea",
    addUrls: '[data-test-id="add-urls"]',
    invalidWarning: '[data-test-id="invalid-urls-warning"]',
    rowUrl: (row: number) => `[data-test-id="upload-row-${row}-url"]`,
};

function mountPasteLinksUpload() {
    setActivePinia(createPinia());
    return mount(PasteLinksUpload as object, {
        localVue,
        pinia: createPinia(),
        propsData: {
            method: { id: "paste-links" },
            targetHistoryId: "hist_1",
            transient: true,
        },
    });
}

async function pasteUrlsAndAdd(wrapper: ReturnType<typeof mount>, urls: string[]) {
    await wrapper.find(SELECTORS.textarea).setValue(urls.join("\n"));
    await wrapper.find(SELECTORS.addUrls).trigger("click");
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
}

function lastReadyState(wrapper: ReturnType<typeof mount>): boolean | undefined {
    const emitted = wrapper.emitted("ready") as boolean[][] | undefined;
    return emitted?.[emitted.length - 1]?.[0];
}

describe("PasteLinksUpload", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("flags invalid URLs and explains why the upload cannot start", async () => {
        const wrapper = mountPasteLinksUpload();

        await pasteUrlsAndAdd(wrapper, ["not-a-valid-url", "https://example.org/data.txt"]);

        expect(wrapper.find(SELECTORS.rowUrl(1)).classes()).toContain("is-invalid");
        expect(wrapper.find(SELECTORS.rowUrl(2)).classes()).not.toContain("is-invalid");

        // A banner explains why Start stays disabled.
        expect(wrapper.find(SELECTORS.invalidWarning).exists()).toBe(true);

        // Invalid URLs block readiness.
        expect(lastReadyState(wrapper)).toBe(false);
    });

    it("marks valid URLs as ready without warnings", async () => {
        const wrapper = mountPasteLinksUpload();

        await pasteUrlsAndAdd(wrapper, ["https://example.org/data1.txt", "https://example.org/data2.txt"]);

        expect(wrapper.findAll(".is-invalid")).toHaveLength(0);
        expect(wrapper.find(SELECTORS.invalidWarning).exists()).toBe(false);
        expect(lastReadyState(wrapper)).toBe(true);
    });
});
