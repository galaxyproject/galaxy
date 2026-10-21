import { createTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { getUploadMethod } from "../uploadMethodRegistry";

import RemoteFilesUpload from "./RemoteFilesUpload.vue";

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

vi.mock("@/composables/fileSources", () => ({
    useFileSources: () => ({
        supportsPagination: () => false,
        supportsSearch: () => false,
    }),
}));

vi.mock("@/api/remoteFiles", () => ({
    fetchFileSources: vi.fn(async () => [
        { id: "source", label: "Test Source", doc: "", uri_root: "gxfiles://source" },
    ]),
    browseRemoteFiles: vi.fn(async () => ({
        entries: [
            { class: "Directory", name: "subdir", uri: "gxfiles://source/subdir", path: "subdir" },
            { class: "File", name: "a.txt", uri: "gxfiles://source/a.txt", path: "a.txt", size: 1, ctime: "" },
            { class: "File", name: "b.txt", uri: "gxfiles://source/b.txt", path: "b.txt", size: 1, ctime: "" },
        ],
        totalMatches: 3,
    })),
}));

const SELECT_ALL = 'input[data-test-id="remote-files-select-all"]';
const ROW_BOX = 'input[data-test-id="remote-files-browser-item-checkbox"]';

async function mountInSource() {
    const wrapper = mount(RemoteFilesUpload, {
        props: { method: getUploadMethod("remote-files")!, targetHistoryId: "hist_1", transient: true },
        global: { plugins: [createPinia(), createTestRouter()] },
    });
    await flushPromises();
    await wrapper
        .findAll("tbody tr")
        .find((row) => row.text().includes("Test Source"))!
        .trigger("click");
    await flushPromises();
    return wrapper;
}

function boxState(wrapper: Awaited<ReturnType<typeof mountInSource>>, selector: string) {
    const input = wrapper.find(selector).element as HTMLInputElement;
    return { checked: input.checked, indeterminate: input.indeterminate };
}

function rowStates(wrapper: Awaited<ReturnType<typeof mountInSource>>) {
    return wrapper.findAll(ROW_BOX).map((box) => (box.element as HTMLInputElement).checked);
}

describe("RemoteFilesUpload select all", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("shows a partly selected page and toggles every file on the page", async () => {
        const wrapper = await mountInSource();
        expect(rowStates(wrapper)).toEqual([false, false]);

        await wrapper.findAll(ROW_BOX)[0]!.setValue(true);
        expect(boxState(wrapper, SELECT_ALL)).toEqual({ checked: false, indeterminate: true });

        await wrapper.findAll(ROW_BOX)[1]!.setValue(true);
        expect(boxState(wrapper, SELECT_ALL)).toEqual({ checked: true, indeterminate: false });

        await wrapper.find(SELECT_ALL).setValue(false);
        expect(rowStates(wrapper)).toEqual([false, false]);
        expect(boxState(wrapper, SELECT_ALL)).toEqual({ checked: false, indeterminate: false });

        await wrapper.find(SELECT_ALL).setValue(true);
        expect(rowStates(wrapper)).toEqual([true, true]);

        await wrapper.findAll(ROW_BOX)[0]!.setValue(false);
        expect(boxState(wrapper, SELECT_ALL)).toEqual({ checked: false, indeterminate: true });
    });
});
