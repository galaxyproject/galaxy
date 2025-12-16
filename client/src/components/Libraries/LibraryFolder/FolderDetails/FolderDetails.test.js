import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import apiResponse from "./response.test.json";

import FolderDetails from "./FolderDetails.vue";

const { server, http } = useServerMock();

const LIBRARY_ID = "lib_test_id";
const FOLDER_ID = "folder_test_id";
const API_URL = `/api/libraries/${LIBRARY_ID}`;

const FOLDER_METADATA = {
    folder_name: "Folder test name",
    folder_description: "Folder test description",
    parent_library_id: LIBRARY_ID,
};
const INPUT_PROP_DATA = {
    id: FOLDER_ID,
    metadata: FOLDER_METADATA,
    isStatic: true,
};

const DETAILS_BUTTON = '[data-testid="loc-details-btn"]';
const LIBRARY_TABLE = '[data-testid="library-table"]';
const DETAILS_MODAL = "#details-modal";
const FOLDER_TABLE = '[data-testid="folder-table"]';
const ERROR_ALERT = '[data-testid="error-alert"]';

async function mountFolderDetailsWrapper(localVue) {
    const wrapper = mount(FolderDetails, {
        global: localVue,
        props: INPUT_PROP_DATA,
    });
    await flushPromises();
    return wrapper;
}
describe("Libraries/LibraryFolder/FolderDetails/FolderDetails.vue", () => {
    let wrapper;
    const localVue = getLocalVue();

    beforeEach(async () => {
        wrapper = await mountFolderDetailsWrapper(localVue);
    });

    afterEach(async () => {
        wrapper.destroy();
    });

    it("Should display details button", async () => {
        const button = wrapper.find(DETAILS_BUTTON);
        expect(button.exists()).toBe(true);
    });

    it("Should display the modal dialog with both tables when the button is clicked", async () => {
        server.use(
            http.untyped.get(API_URL, () => {
                return HttpResponse.json(apiResponse);
            }),
        );

        expectModalToBeHidden();

        await openDetailsModal();

        expectModalToBeVisible();

        expect(wrapper.find(LIBRARY_TABLE).html()).toContain(LIBRARY_ID);
        expect(wrapper.find(FOLDER_TABLE).html()).toContain(FOLDER_ID);
        expect(wrapper.find(ERROR_ALERT).text()).toBeFalsy();
    });

    it("Should display error when the library details cannot be retrieved", async () => {
        server.use(
            http.untyped.get(API_URL, () => {
                return HttpResponse.error();
            }),
        );

        await openDetailsModal();

        expect(wrapper.find(LIBRARY_TABLE).exists()).toBe(false);
        expect(wrapper.find(FOLDER_TABLE).exists()).toBe(true);
        expect(wrapper.find(ERROR_ALERT).text()).toContain("Failed to retrieve library details.");
    });

    async function openDetailsModal() {
        const button = wrapper.find(DETAILS_BUTTON);

        await button.trigger("click");

        await flushPromises();
    }

    function expectModalToBeHidden() {
        expect(wrapper.find(DETAILS_MODAL).attributes("aria-hidden")).toBeTruthy();
    }

    function expectModalToBeVisible() {
        expect(wrapper.find(DETAILS_MODAL).attributes("aria-hidden")).toBeFalsy();
    }
});
