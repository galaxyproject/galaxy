import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
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
};

const DETAILS_BUTTON = '[data-testid="loc-details-btn"]';
const LIBRARY_TABLE = '[data-testid="library-table"]';
const FOLDER_TABLE = '[data-testid="folder-table"]';
const ERROR_ALERT = '[data-testid="error-alert"]';

describe("Libraries/LibraryFolder/FolderDetails/FolderDetails.vue", () => {
    const axiosMock = new MockAdapter(axios);

    beforeEach(() => {
        axiosMock.reset();
    });

    it("Should display details button", async () => {
        const wrapper = mount(FolderDetails, { propsData: INPUT_PROP_DATA });
        const button = wrapper.find(DETAILS_BUTTON);
        expect(button.exists()).toBeTruthy();
    });

    it("Should display the modal dialog with both tables when the button is clicked", async () => {
        axiosMock.onGet(API_URL).replyOnce(200, apiResponse);
        const wrapper = mount(FolderDetails, { propsData: INPUT_PROP_DATA });

        await openDetailsModal(wrapper);

        console.log(wrapper.html());

        expect(wrapper.find(LIBRARY_TABLE).exists()).toBeTruthy();
        expect(wrapper.find(FOLDER_TABLE).exists()).toBeTruthy();
        expect(wrapper.find(ERROR_ALERT).exists()).toBeFalsy();
    });

    it("Should display error when the library details cannot be retrieved", async () => {
        axiosMock.onGet(API_URL).networkError();
        const wrapper = mount(FolderDetails, { propsData: INPUT_PROP_DATA });

        await openDetailsModal(wrapper);

        expect(wrapper.find(LIBRARY_TABLE).exists()).toBeFalsy();
        expect(wrapper.find(FOLDER_TABLE).exists()).toBeTruthy();
        expect(wrapper.find(ERROR_ALERT).exists()).toBeTruthy();
    });

    async function openDetailsModal(wrapper) {
        const button = wrapper.find(DETAILS_BUTTON);
        await button.trigger("click");
        await wrapper.vm.$nextTick();
        await flushPromises();
    }
});
