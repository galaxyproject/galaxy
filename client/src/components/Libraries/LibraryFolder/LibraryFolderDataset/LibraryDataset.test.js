import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";
import { getAppRoot } from "onload/loadConfig";
import { Services } from "../services";
import LibraryDataset from "./LibraryDataset";
import cannotManageDatasetResponse from "./testData/cannotManageDataset.json";
import cannotModifyDatasetResponse from "./testData/cannotModifyDataset.json";
import restrictedDatasetResponse from "./testData/restrictedDataset.json";
import unrestrictedDatasetResponse from "./testData/unrestrictedDataset.json";

jest.mock("app");
jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");
jest.mock("../services");

const FOLDER_ID = "test_folder_id";
const UNRESTRICTED_DATASET_ID = "unrestricted_dataset_id";
const RESTRICTED_DATASET_ID = "restricted_dataset_id";
const CANNOT_MODIFY_DATASET_ID = "cannot_modify_dataset_id";
const CANNOT_MANAGE_DATASET_ID = "cannot_manage_dataset_id";
const EXPECTED_DATASET_DATA = unrestrictedDatasetResponse;

const mockDatatypesProvider = {
    render() {
        return this.$scopedSlots.default({
            loading: false,
            item: ["xml"],
        });
    },
};
const mockDbKeyProvider = {
    render() {
        return this.$scopedSlots.default({
            loading: false,
            item: ["?"],
        });
    },
};

Services.mockImplementation(() => {
    const responseMap = new Map([
        [UNRESTRICTED_DATASET_ID, unrestrictedDatasetResponse],
        [RESTRICTED_DATASET_ID, restrictedDatasetResponse],
        [CANNOT_MODIFY_DATASET_ID, cannotModifyDatasetResponse],
        [CANNOT_MANAGE_DATASET_ID, cannotManageDatasetResponse],
    ]);
    return {
        async getDataset(datasetID, onError) {
            return responseMap.get(datasetID);
        },
        async updateDataset(datasetID, data, onSucess, onError) {
            return data;
        },
    };
});

const MODIFY_BUTTON = '[data-test-id="modify-btn"]';
const AUTO_DETECT_BUTTON = '[data-test-id="auto-detect-btn"]';
const PERMISSIONS_BUTTON = '[data-test-id="permissions-btn"]';
const UNRESTRICTED_MESSAGE = '[data-test-id="unrestricted-msg"]';
const DATASET_TABLE = '[data-test-id="dataset-table"]';
const PEEK_VIEW = '[data-test-id="peek-view"]';

async function mountLibraryDatasetWrapper(localVue, expectDatasetId, isAdmin = false) {
    const propsData = {
        dataset_id: expectDatasetId,
        folder_id: FOLDER_ID,
    };
    const wrapper = mount(LibraryDataset, {
        localVue,
        propsData,
        stubs: {
            DatatypesProvider: mockDatatypesProvider,
            DbKeyProvider: mockDbKeyProvider,
            CurrentUser: {
                render() {
                    return this.$scopedSlots.default({
                        user: { is_admin: isAdmin },
                    });
                },
            },
        },
    });
    await flushPromises();
    return wrapper;
}

describe("Libraries/LibraryFolder/LibraryFolderDataset/LibraryDataset.vue", () => {
    const localVue = getLocalVue();

    it("should display all buttons when user is Admin", async () => {
        const isAdmin = true;
        const wrapper = await mountLibraryDatasetWrapper(localVue, UNRESTRICTED_DATASET_ID, isAdmin);

        expect(wrapper.find(MODIFY_BUTTON).exists()).toBe(true);
        expect(wrapper.find(AUTO_DETECT_BUTTON).exists()).toBe(true);
        expect(wrapper.find(PERMISSIONS_BUTTON).exists()).toBe(true);
    });

    it("should not display 'Modify' and 'Auto-detect datatype' buttons when user cannot modify dataset", async () => {
        const wrapper = await mountLibraryDatasetWrapper(localVue, CANNOT_MODIFY_DATASET_ID);

        expect(wrapper.find(MODIFY_BUTTON).exists()).toBe(false);
        expect(wrapper.find(AUTO_DETECT_BUTTON).exists()).toBe(false);
    });

    it("should not display 'Permissions' button when user is not an administrator", async () => {
        const isAdmin = false;
        const wrapper = await mountLibraryDatasetWrapper(localVue, CANNOT_MANAGE_DATASET_ID, isAdmin);

        expect(wrapper.find(PERMISSIONS_BUTTON).exists()).toBe(false);
    });

    it("should display unrestricted dataset message when dataset is unrestricted", async () => {
        const wrapper = await mountLibraryDatasetWrapper(localVue, UNRESTRICTED_DATASET_ID);

        expect(wrapper.find(UNRESTRICTED_MESSAGE).exists()).toBe(true);
    });

    it("should not display unrestricted dataset message when dataset is restricted", async () => {
        const wrapper = await mountLibraryDatasetWrapper(localVue, RESTRICTED_DATASET_ID);

        expect(wrapper.find(UNRESTRICTED_MESSAGE).exists()).toBe(false);
    });

    it("should display dataset details in the table", async () => {
        const wrapper = await mountLibraryDatasetWrapper(localVue, UNRESTRICTED_DATASET_ID);
        const table = wrapper.find(DATASET_TABLE);
        const tableHtml = table.html();

        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.name);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.file_ext);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.genome_build);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.file_size);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.update_time);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.date_uploaded);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.uploaded_by);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.misc_blurb);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.misc_info);
        expect(tableHtml).toContain(EXPECTED_DATASET_DATA.uuid);
    });

    it("should display dataset peek content", async () => {
        const wrapper = await mountLibraryDatasetWrapper(localVue, UNRESTRICTED_DATASET_ID);
        const peek = wrapper.find(PEEK_VIEW);

        expect(peek.text()).toBe(EXPECTED_DATASET_DATA.peek);
    });

    it("should display input fields when `Modify` button is clicked", async () => {
        const wrapper = await mountLibraryDatasetWrapper(localVue, UNRESTRICTED_DATASET_ID);
        const modify_button = wrapper.find(MODIFY_BUTTON);

        expect(wrapper.find(DATASET_TABLE).html()).not.toContain("<input");

        await modify_button.trigger("click");
        await flushPromises();

        expect(wrapper.find(DATASET_TABLE).html()).toContain("<input");
    });
});
