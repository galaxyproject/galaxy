import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";
import { SELECTION_STATES, type SelectionItem, type SelectionState } from "@/components/SelectionDialog/selectionTypes";

import type { RemoteFilesList } from "./testingData";
import { rootId, rootResponse } from "./testingData";

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

interface RowElement extends SelectionItem, Element {
    _rowVariant: SelectionState;
}

const sourceId = "paginated";
const sourceRoot = `gxfiles://${sourceId}`;
// two pages of 25 rows, mostly files with a few folders among them
const totalEntries = 30;
const isFolder = (index: number) => index % 10 === 5;

const plugins: BrowsableFilesSourcePlugin[] = [
    {
        ...rootResponse.find(({ id }) => id === rootId)!,
        id: sourceId,
        label: "Paginated",
        uri_root: sourceRoot,
        supports: { pagination: true, search: true, sorting: false },
    },
];

function sourceListing(offset: number, limit: number): RemoteFilesList {
    const entries: RemoteFilesList = [];
    for (let i = offset; i < Math.min(offset + limit, totalEntries); i++) {
        const name = isFolder(i) ? `folder${i}` : `file${i}`;
        const entry = { name, path: `/${name}`, uri: `${sourceRoot}/${name}` };
        entries.push(isFolder(i) ? { ...entry, class: "Directory" } : { ...entry, class: "File", size: 0, ctime: "" });
    }
    return entries;
}

function folderListing(folderUri: string): RemoteFilesList {
    return ["file1", "file2"].map((name) => ({
        class: "File",
        name,
        path: `${folderUri}/${name}`,
        uri: `${folderUri}/${name}`,
        size: 0,
        ctime: "",
    }));
}

describe("FilesDialog, paginated file source", () => {
    let wrapper: Wrapper<any>;
    let slowFolders: string[];

    beforeEach(async () => {
        slowFolders = [];
        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => response(200).json(plugins)),
            http.get("/api/file_source_templates", ({ response }) => response(200).json([])),
            http.get("/api/remote_files", async ({ response, query }) => {
                const target = query.get("target")!;
                if (target === sourceRoot) {
                    const offset = Number(query.get("offset") ?? 0);
                    const limit = Number(query.get("limit") ?? totalEntries);
                    return response(200).json(sourceListing(offset, limit), {
                        headers: { total_matches: String(totalEntries) },
                    });
                }
                if (slowFolders.includes(target)) {
                    await new Promise((resolve) => setTimeout(resolve, 50));
                }
                const files = folderListing(target);
                return response(200).json(files, { headers: { total_matches: String(files.length) } });
            }),
        );
        wrapper = mount(FilesDialog as object, {
            localVue: getLocalVue(),
            propsData: { multiple: true, modalStatic: true },
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
        });
        await flushPromises();
        selectionDialog().vm.$emit("onOpen", findRow(sourceId));
        await flushPromises();
    });

    function selectionDialog(): any {
        return wrapper.findComponent(SelectionDialog);
    }

    function rows(): RowElement[] {
        return selectionDialog().props("items") as RowElement[];
    }

    function findRow(id: string): RowElement {
        const row = rows().find((item) => item.id === id);
        if (!row) {
            throw new Error(`Row with id ${id} not found`);
        }
        return row;
    }

    async function clickOn(row: RowElement) {
        selectionDialog().vm.$emit("onClick", row);
        await flushPromises();
    }

    async function selectAll() {
        selectionDialog().vm.$emit("onSelectAll");
        await flushPromises();
    }

    async function goToPage(page: number) {
        await wrapper.find(`[aria-label='Go to page ${page}']`).trigger("click");
        await flushPromises();
    }

    function expectRowsSelected(selected: boolean) {
        const expected = selected ? SELECTION_STATES.SELECTED : SELECTION_STATES.UNSELECTED;
        rows().forEach((row) => expect(row._rowVariant).toBe(expected));
    }

    function isOkDisabled(): boolean {
        return Boolean(wrapper.find("[data-description='selection dialog ok']").attributes("disabled"));
    }

    it("should keep the pager after selecting a folder", async () => {
        expect(wrapper.find(".pagination").exists()).toBe(true);
        await clickOn(findRow(`${sourceRoot}/folder5`));
        expect(wrapper.find(".pagination").exists()).toBe(true);
    });

    it("should keep the selection of other pages when selecting all on a page", async () => {
        await selectAll();
        expectRowsSelected(true);

        await goToPage(2);
        await selectAll();
        expectRowsSelected(true);

        await goToPage(1);
        expectRowsSelected(true);

        // unselecting all on a page leaves the other page selected
        await selectAll();
        expectRowsSelected(false);
        await goToPage(2);
        expectRowsSelected(true);
    });

    it("should keep OK disabled until the files of every selected folder are listed", async () => {
        slowFolders = [`${sourceRoot}/folder15`];
        await selectAll();
        expect(isOkDisabled()).toBe(true);

        await vi.waitFor(() => expect(isOkDisabled()).toBe(false));
    });
});
