import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

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

async function mountFolderDetailsWrapper(globalConfig) {
    const wrapper = mount(FolderDetails, {
        props: INPUT_PROP_DATA,
        global: {
            ...globalConfig.global,
            stubs: {
                LibraryBreadcrumb: true,
                DatasetLibraryView: true,
                FolderLibraryView: true,
                PermissionsView: true,
                "b-modal": {
                    template: "<div :id=\"id\" :aria-hidden=\"modalVisible ? 'false' : 'true'\"><slot></slot></div>",
                    props: ["id", "title", "ok-title", "cancel-title", "visible", "static"],
                    emits: ["ok", "cancel", "show", "hide"],
                    data() {
                        return {
                            modalVisible: false,
                        };
                    },
                    mounted() {
                        // Simulate the v-b-modal directive functionality
                        this.$el.ownerDocument.addEventListener("click", (e) => {
                            if (e.target.closest('[data-testid="loc-details-btn"]')) {
                                this.modalVisible = true;
                                this.$emit("show");
                            }
                        });
                    },
                },
                "b-table-lite": {
                    template:
                        '<table :data-testid="$attrs[\'data-testid\']"><tbody><tr v-for="item in items" :key="item.id"><td v-for="field in fields" :key="field.key">{{ item[field.key] }}</td></tr></tbody></table>',
                    props: ["fields", "items", "class", "striped", "small"],
                },
                "b-alert": {
                    template: '<div v-if="show" data-testid="error-alert"><slot></slot></div>',
                    props: ["variant", "show", "dismissible"],
                },
                "b-button": {
                    template: "<button @click=\"$emit('click')\"><slot></slot></button>",
                    emits: ["click"],
                },
            },
        },
    });
    await flushPromises();
    return wrapper;
}
describe("Libraries/LibraryFolder/FolderDetails/FolderDetails.vue", () => {
    const axiosMock = new MockAdapter(axios);
    let wrapper;
    const globalConfig = getLocalVue();

    beforeEach(async () => {
        axiosMock.reset();
        wrapper = await mountFolderDetailsWrapper(globalConfig);
    });

    afterEach(async () => {
        wrapper.unmount();
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
