import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import { computed, nextTick, ref } from "vue";

import PasteContentUpload from "./PasteContentUpload.vue";

vi.mock("@/composables/upload/uploadDefaults", () => ({
    useUploadDefaults: () => ({
        effectiveExtensions: computed(() => []),
        listDbKeys: computed(() => []),
        configurationsReady: ref(true),
        createItemDefaults: () => ({
            extension: "auto",
            dbkey: "?",
            spaceToTab: false,
            toPosixLines: false,
        }),
    }),
}));

const localVue = getLocalVue();

async function mountPaste() {
    const wrapper = mount(PasteContentUpload as object, {
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
        propsData: {
            method: { id: "paste-content", name: "Paste Content" },
            targetHistoryId: "history-id",
            allowCollections: false,
            transient: true,
        },
    });
    await flushPromises();
    return wrapper;
}

async function addDatasets(wrapper: Wrapper<Vue>, count: number) {
    const addButton = wrapper.findAll("button").filter((btn) => btn.text().includes("Add Another Dataset"));
    expect(addButton.length).toBe(1);
    for (let i = 0; i < count; i++) {
        await addButton.at(0).trigger("click");
        await flushPromises();
        await nextTick();
    }
}

function nameHeader(wrapper: Wrapper<Vue>) {
    const headers = wrapper.findAll("thead th").filter((th) => th.text().includes("Name"));
    expect(headers.length).toBe(1);
    return headers.at(0);
}

async function ensureRowExpanded(wrapper: Wrapper<Vue>, displayIndex: number, itemId: number) {
    const textareaSelector = `#paste-content-${itemId}`;
    if (wrapper.find(textareaSelector).exists()) {
        return;
    }

    await wrapper.find(`[data-test-id="paste-content-toggle-${displayIndex}"]`).trigger("click");
    await flushPromises();
    await nextTick();
    expect(wrapper.find(textareaSelector).exists()).toBe(true);
}

describe("PasteContentUpload", () => {
    it("keeps expanded row details with the same item after sorting by name", async () => {
        const wrapper = await mountPaste();
        await addDatasets(wrapper, 1);

        await wrapper.find('[data-test-id="upload-row-1-name"]').setValue("bravo");
        await wrapper.find('[data-test-id="upload-row-2-name"]').setValue("alpha");
        await flushPromises();

        await ensureRowExpanded(wrapper, 1, 1);

        const marker = "paste-content-for-item-1";
        await wrapper.find("#paste-content-1").setValue(marker);

        await nameHeader(wrapper).trigger("click");
        await flushPromises();
        await nextTick();

        const markerTextareas = wrapper
            .findAll("textarea")
            .filter((field) => field.isVisible() && (field.element as HTMLTextAreaElement).value === marker);
        expect(markerTextareas).toHaveLength(1);
    });

    it("keeps expanded row details with the same item after removing another row", async () => {
        const wrapper = await mountPaste();
        await addDatasets(wrapper, 1);

        await ensureRowExpanded(wrapper, 2, 2);

        const marker = "paste-content-stays-with-item-2";
        await wrapper.find("#paste-content-2").setValue(marker);

        await wrapper.find('[data-test-id="upload-row-1-remove"]').trigger("click");
        await flushPromises();
        await nextTick();

        const markerTextareas = wrapper
            .findAll("textarea")
            .filter((field) => field.isVisible() && (field.element as HTMLTextAreaElement).value === marker);
        expect(markerTextareas).toHaveLength(1);
    });
});
