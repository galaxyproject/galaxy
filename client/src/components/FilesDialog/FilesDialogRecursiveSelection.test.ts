import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { SELECTION_STATES, type SelectionItem, type SelectionState } from "@/components/SelectionDialog/selectionTypes";

import type { RemoteFilesList } from "./testingData";
import {
    directory1RecursiveResponse,
    directory1Response,
    directoryId,
    pdbResponse,
    rootId,
    rootResponse,
    subDirectoryId,
    subsubdirectoryResponse,
} from "./testingData";

import FilesDialog from "./FilesDialog.vue";
import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

vi.mock("app");

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: {},
        isConfigLoaded: true,
    })),
}));

const { server, http } = useServerMock();

interface Row extends SelectionItem {
    _rowVariant: SelectionState;
}

// object stores list keys, so a recursive listing need not return the folders in between
const filesOnly = directory1RecursiveResponse.filter((entry) => entry.class === "File");

describe("FilesDialog, recursive listing without folders", () => {
    let wrapper: Wrapper<any>;
    let recursiveListing: RemoteFilesList;

    const dialog = () => wrapper.findComponent(SelectionDialog);
    const rows = () => dialog().props("items") as Row[];
    const row = (id: string) => rows().find((item) => item.id === id)!;

    async function emit(event: string, ...args: unknown[]) {
        dialog().vm.$emit(event, ...args);
        await flushPromises();
    }

    async function goBack() {
        await wrapper.find("[data-description='selection dialog undo']").trigger("click");
        await flushPromises();
    }

    beforeEach(async () => {
        recursiveListing = filesOnly;
        const listings: Record<string, RemoteFilesList> = {
            [`gxfiles://${rootId}`]: pdbResponse,
            [directoryId]: directory1Response,
            [subDirectoryId]: subsubdirectoryResponse,
        };
        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => response(200).json(rootResponse)),
            http.get("/api/file_source_templates", ({ response }) => response(200).json([])),
            http.get("/api/remote_files", ({ response, query }) => {
                const target = query.get("target")!;
                const entries = query.get("recursive") === "true" ? recursiveListing : (listings[target] ?? []);
                return response(200).json(entries, { headers: { total_matches: `${entries.length}` } });
            }),
        );
        wrapper = mount(FilesDialog as object, {
            localVue: getLocalVue(),
            propsData: { multiple: true, modalStatic: true },
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
        });
        await flushPromises();
        await emit("onOpen", row(rootId));
    });

    it("should show every level of a selected folder as selected", async () => {
        await emit("onClick", row(directoryId));
        expect(row(directoryId)._rowVariant).toBe(SELECTION_STATES.SELECTED);

        await emit("onOpen", row(directoryId));
        for (const item of rows()) {
            expect(item._rowVariant).toBe(SELECTION_STATES.SELECTED);
        }
        expect(dialog().props("selectAllVariant")).toBe(SELECTION_STATES.SELECTED);

        await emit("onOpen", row(subDirectoryId));
        for (const item of rows()) {
            expect(item._rowVariant).toBe(SELECTION_STATES.SELECTED);
        }

        await goBack();
        await goBack();
        expect(row(directoryId)._rowVariant).toBe(SELECTION_STATES.SELECTED);
    });

    it("should show a selected folder as mixed after unselecting a folder below it", async () => {
        await emit("onClick", row(directoryId));
        await emit("onOpen", row(directoryId));
        await emit("onClick", row(subDirectoryId));
        expect(row(subDirectoryId)._rowVariant).toBe(SELECTION_STATES.UNSELECTED);

        await goBack();
        expect(row(directoryId)._rowVariant).toBe(SELECTION_STATES.MIXED);
    });

    it("should not count a file the listing did not return as selected", async () => {
        recursiveListing = filesOnly.slice(1);
        await emit("onClick", row(directoryId));
        await emit("onOpen", row(directoryId));

        const [omitted] = filesOnly;
        for (const item of rows().filter((item) => item.isLeaf)) {
            const expected = item.id === omitted!.uri ? SELECTION_STATES.UNSELECTED : SELECTION_STATES.SELECTED;
            expect(item._rowVariant).toBe(expected);
        }
        expect(dialog().props("selectAllVariant")).toBe(SELECTION_STATES.MIXED);
    });

    it("should unselect all in a folder of empty folders below a selected folder", async () => {
        recursiveListing = directory1RecursiveResponse.filter((entry) => entry.class === "Directory");
        await emit("onClick", row(directoryId));
        await emit("onOpen", row(directoryId));
        await emit("onOpen", row(subDirectoryId));
        expect(dialog().props("selectAllVariant")).toBe(SELECTION_STATES.SELECTED);

        await emit("onSelectAll");
        for (const item of rows()) {
            expect(item._rowVariant).toBe(SELECTION_STATES.UNSELECTED);
        }
        expect(dialog().props("selectAllVariant")).toBe(SELECTION_STATES.UNSELECTED);
    });
});
