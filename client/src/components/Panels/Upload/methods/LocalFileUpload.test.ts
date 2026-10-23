import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { PreparedUpload, UploadMethodComponent } from "../types";

import LocalFileUpload from "./LocalFileUpload.vue";

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
    sortableHeaders: "th.g-table-sortable",
    rowNames: '[data-test-id^="upload-row-"][data-test-id$="-name"]',
    rowRemove: (row: number) => `[data-test-id="upload-row-${row}-remove"]`,
    fileInput: "#local-file-input",
    collectionToggle: '[data-test-id="collection-toggle"] input',
    collectionName: "#collection-name-input",
    collectionType: "#collection-type-select",
    pairItems: ".pairing-preview .pair-item",
};

function makeFiles(names: string[]): File[] {
    return names.map((name, index) => new File(["x".repeat(index + 1)], name));
}

function mountLocalFileUpload(initialFiles: File[]) {
    return mount(LocalFileUpload as object, {
        localVue,
        pinia: createPinia(),
        propsData: {
            method: { id: "local-file" },
            targetHistoryId: "hist_1",
            transient: true,
            initialFiles,
        },
    });
}

type Wrapper = ReturnType<typeof mountLocalFileUpload>;

function displayedNames(wrapper: Wrapper): string[] {
    return wrapper.findAll(SELECTORS.rowNames).map((input) => (input.element as HTMLInputElement).value);
}

async function sortByName(wrapper: Wrapper) {
    await wrapper.find(SELECTORS.sortableHeaders).trigger("click");
}

async function browseFiles(wrapper: Wrapper, files: File[]) {
    const input = wrapper.find(SELECTORS.fileInput);
    Object.defineProperty(input.element, "files", { value: files, configurable: true });
    await input.trigger("change");
}

/** Builds the upload the same way the upload panel does when Start is clicked. */
function prepareUpload(wrapper: Wrapper): PreparedUpload | null {
    return (wrapper.vm as unknown as UploadMethodComponent).prepareUpload();
}

function uploadedNames(wrapper: Wrapper): string[] {
    return (prepareUpload(wrapper)?.uploadItems ?? []).map((item) => item.name ?? "");
}

describe("LocalFileUpload", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("uploads files in the order the sorted table shows", async () => {
        const wrapper = mountLocalFileUpload(makeFiles(["c.txt", "a.txt", "b.txt"]));

        await sortByName(wrapper);
        expect(displayedNames(wrapper)).toEqual(["a.txt", "b.txt", "c.txt"]);
        expect(uploadedNames(wrapper)).toEqual(["a.txt", "b.txt", "c.txt"]);

        await sortByName(wrapper);
        expect(displayedNames(wrapper)).toEqual(["c.txt", "b.txt", "a.txt"]);
        expect(uploadedNames(wrapper)).toEqual(["c.txt", "b.txt", "a.txt"]);
    });

    it("removes the file of the clicked row after sorting", async () => {
        const wrapper = mountLocalFileUpload(makeFiles(["c.txt", "a.txt", "b.txt"]));

        await sortByName(wrapper);
        await wrapper.find(SELECTORS.rowRemove(1)).trigger("click");

        expect(displayedNames(wrapper)).toEqual(["b.txt", "c.txt"]);
        expect(uploadedNames(wrapper)).toEqual(["b.txt", "c.txt"]);
    });

    it("keeps files added after sorting in sorted order", async () => {
        const wrapper = mountLocalFileUpload(makeFiles(["c.txt", "a.txt"]));

        await sortByName(wrapper);
        await browseFiles(wrapper, makeFiles(["b.txt"]));

        expect(displayedNames(wrapper)).toEqual(["a.txt", "b.txt", "c.txt"]);
        expect(uploadedNames(wrapper)).toEqual(["a.txt", "b.txt", "c.txt"]);
    });

    it("keeps sorting new files after the table is emptied and shown again", async () => {
        const wrapper = mountLocalFileUpload(makeFiles(["b.txt", "a.txt"]));

        await sortByName(wrapper);
        await wrapper.find(SELECTORS.rowRemove(1)).trigger("click");
        await wrapper.find(SELECTORS.rowRemove(1)).trigger("click");
        await browseFiles(wrapper, makeFiles(["z.txt", "x.txt", "y.txt"]));

        expect(wrapper.find(SELECTORS.sortableHeaders).attributes("aria-sort")).toBe("ascending");
        expect(displayedNames(wrapper)).toEqual(["x.txt", "y.txt", "z.txt"]);
        expect(uploadedNames(wrapper)).toEqual(["x.txt", "y.txt", "z.txt"]);
    });

    it("pairs files for a list of pairs in the sorted order", async () => {
        const wrapper = mountLocalFileUpload(makeFiles(["s1_R2.fastq", "s2_R1.fastq", "s1_R1.fastq", "s2_R2.fastq"]));

        await sortByName(wrapper);
        await wrapper.find(SELECTORS.collectionToggle).setValue(true);
        await wrapper.find(SELECTORS.collectionName).setValue("pairs");
        await wrapper.find(SELECTORS.collectionType).setValue("list:paired");

        const pairs = wrapper.findAll(SELECTORS.pairItems).map((pair) => pair.text());
        expect(pairs).toHaveLength(2);
        expect(pairs[0]).toMatch(/s1_R1\.fastq.*s1_R2\.fastq/);
        expect(pairs[1]).toMatch(/s2_R1\.fastq.*s2_R2\.fastq/);

        const prepared = prepareUpload(wrapper);
        expect(prepared?.collectionConfig?.type).toBe("list:paired");
        expect(uploadedNames(wrapper)).toEqual(["s1_R1.fastq", "s1_R2.fastq", "s2_R1.fastq", "s2_R2.fastq"]);
    });
});
