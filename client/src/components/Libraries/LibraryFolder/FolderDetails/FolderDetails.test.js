import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import FolderDetails from "./FolderDetails";
import apiResponse from "./response.test.json";

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
        localVue,
        propsData: INPUT_PROP_DATA,
    });
    await flushPromises();
    return wrapper;
}
describe("Libraries/LibraryFolder/FolderDetails/FolderDetails.vue", () => {
    const axiosMock = new MockAdapter(axios);
    let wrapper;
    const localVue = getLocalVue();

    beforeEach(async () => {
        axiosMock.reset();
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
        // Using replyOnce to make sure we made only one request
        axiosMock.onGet(API_URL).replyOnce(200, apiResponse);

        expectModalToBeHidden();

        await openDetailsModal();

        expectModalToBeVisible();

        expect(wrapper.find(LIBRARY_TABLE).html()).toContain(LIBRARY_ID);
        expect(wrapper.find(FOLDER_TABLE).html()).toContain(FOLDER_ID);
        expect(wrapper.find(ERROR_ALERT).text()).toBeFalsy();
    });

    it("Should display error when the library details cannot be retrieved", async () => {
        axiosMock.onGet(API_URL).networkError();

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
