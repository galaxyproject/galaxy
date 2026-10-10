import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { LibraryFolderMetadata } from "@/api/libraries";

import libraryResponse from "./response.test.json";

import FolderDetails from "./FolderDetails.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();

const LIBRARY_ID = "lib_test_id";
const FOLDER_ID = "folder_test_id";
const FOLDER_METADATA: LibraryFolderMetadata = {
    folder_name: "Folder test name",
    folder_description: "Folder test description",
    parent_library_id: LIBRARY_ID,
    full_path: [[FOLDER_ID, "Folder test name"]],
    can_add_library_item: false,
    can_modify_folder: false,
    total_rows: 0,
};

const SELECTORS = {
    DETAILS_BUTTON: '[data-testid="loc-details-btn"]',
    MODAL_DIALOG: "dialog",
    LIBRARY_TABLE: '[data-testid="library-table"]',
    FOLDER_TABLE: '[data-testid="folder-table"]',
    ERROR_ALERT: '[data-testid="error-alert"]',
};

enableAutoUnmount(afterEach);

/** Answers library detail requests with `reply()` and returns the library IDs requested. */
function serveLibrary(reply: () => Response) {
    const requestedIds: string[] = [];
    server.use(
        http.get("/api/libraries/{id}", ({ params, response }) => {
            requestedIds.push(params.id);
            return response.untyped(reply());
        }),
    );
    return requestedIds;
}

async function mountFolderDetails() {
    const wrapper = mount(FolderDetails, {
        global: localVue,
        props: { id: FOLDER_ID, metadata: FOLDER_METADATA },
    });
    await flushPromises();
    return wrapper;
}

async function openDetailsModal(wrapper: VueWrapper) {
    await wrapper.find(SELECTORS.DETAILS_BUTTON).trigger("click");
    await flushPromises();
}

function isModalOpen(wrapper: VueWrapper) {
    return (wrapper.find(SELECTORS.MODAL_DIALOG).element as HTMLDialogElement).open;
}

describe("FolderDetails", () => {
    it("shows the details button", async () => {
        const wrapper = await mountFolderDetails();

        expect(wrapper.find(SELECTORS.DETAILS_BUTTON).exists()).toBe(true);
    });

    it("opens the modal with the parent library and folder details when the button is clicked", async () => {
        const requestedIds = serveLibrary(() => HttpResponse.json(libraryResponse));
        const wrapper = await mountFolderDetails();
        expect(isModalOpen(wrapper)).toBe(false);

        await openDetailsModal(wrapper);

        expect(isModalOpen(wrapper)).toBe(true);
        expect(requestedIds).toEqual([LIBRARY_ID]);
        const libraryTable = wrapper.find(SELECTORS.LIBRARY_TABLE);
        expect(libraryTable.html()).toContain(LIBRARY_ID);
        expect(libraryTable.text()).toContain("Library Name");
        const folderTable = wrapper.find(SELECTORS.FOLDER_TABLE);
        expect(folderTable.html()).toContain(FOLDER_ID);
        expect(folderTable.text()).toContain(FOLDER_METADATA.folder_name);
    });

    it("shows an error and only the folder details when the library details cannot be retrieved", async () => {
        serveLibrary(() => HttpResponse.error());
        const wrapper = await mountFolderDetails();

        await openDetailsModal(wrapper);

        expect(wrapper.find(SELECTORS.LIBRARY_TABLE).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.FOLDER_TABLE).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.ERROR_ALERT).text()).toContain("Failed to retrieve library details.");
    });
});
