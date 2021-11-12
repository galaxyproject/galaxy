import { mount, shallowMount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import FolderDetails from "./FolderDetails";
import apiResponse from "./response.test.json";
import { getLocalVue } from "jest/helpers";
import { BModal } from "bootstrap-vue";

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
const FORLDER_MODAL = "#details-modal";
const FOLDER_TABLE = '[data-testid="folder-table"]';
const ERROR_ALERT = '[data-testid="error-alert"]';

async function mountFolderDetailsWrapper(localVue) {
    const wrapper = shallowMount(FolderDetails, {
        localVue,
        propsData: INPUT_PROP_DATA,
        stubs: {
            BModal: BModal,
        },
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
        axiosMock.onGet(API_URL).reply(200, apiResponse);
        wrapper = await mountFolderDetailsWrapper(localVue);
    });
    afterEach(async () => {
        wrapper.destroy();
    });

    it("Should display details button", async () => {
        const button = wrapper.find(DETAILS_BUTTON);
        expect(button.exists()).toBeTruthy();
    });

    it("Should display the modal dialog with both tables when the button is clicked", async () => {
        // make sure that modal is hidden
        expect(wrapper.find(FORLDER_MODAL).attributes("aria-hidden")).toEqual("true");
        await openDetailsModal(wrapper);
        // make sure that modal is visible
        expect(wrapper.find(FORLDER_MODAL).attributes("aria-hidden")).toEqual(undefined);
    });

    it("Should display error when the library details cannot be retrieved", async () => {
        axiosMock.onGet(API_URL).networkError();

        await openDetailsModal(wrapper);

        expect(wrapper.find(LIBRARY_TABLE).exists()).toBeFalsy();
        expect(wrapper.find(FOLDER_TABLE).exists()).toBeTruthy();
        expect(wrapper.find(ERROR_ALERT).exists()).toBeTruthy();
    });

    async function openDetailsModal(wrapper) {
        const button = wrapper.find(DETAILS_BUTTON);

        await button.trigger("click");

        await flushPromises();
    }
});
