import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getAppRoot } from "onload/loadConfig";
import { createPinia } from "pinia";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";

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
        return this.$slots.default
            ? this.$slots.default({
                  loading: false,
                  item: ["xml"],
              })
            : null;
    },
};
const mockDbKeyProvider = {
    render() {
        return this.$slots.default
            ? this.$slots.default({
                  loading: false,
                  item: ["?"],
              })
            : null;
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

async function mountLibraryDatasetWrapper(globalConfig, expectDatasetId, isAdmin = false) {
    const pinia = createPinia();
    const props = {
        dataset_id: expectDatasetId,
        folder_id: FOLDER_ID,
    };
    const wrapper = mount(LibraryDataset, {
        global: {
            ...globalConfig.global,
            plugins: [...(globalConfig.global?.plugins || []), pinia],
            stubs: {
                DatatypesProvider: mockDatatypesProvider,
                DbKeyProvider: mockDbKeyProvider,
                SingleItemSelector: { template: "<div>selector</div>" },
                "b-table": {
                    template: `<table>
                        <tbody>
                            <tr v-for="item in items" :key="item.name">
                                <td>
                                    <slot name="cell(name)" :item="item">
                                        <strong v-if="item.name">{{ item.name }}</strong>
                                    </slot>
                                </td>
                                <td>
                                    <slot name="cell(value)" :item="item" :row="{item}">
                                        {{ item.value }}
                                    </slot>
                                </td>
                            </tr>
                        </tbody>
                    </table>`,
                    props: ["fields", "items", "class", "thead-class", "striped", "small"],
                },
                "b-form-input": {
                    template:
                        '<input :value="modelValue || value" @input="$emit(\'update:modelValue\', $event.target.value)" />',
                    props: ["modelValue", "value"],
                    emits: ["update:modelValue"],
                },
                "b-button": {
                    template: "<button @click=\"$emit('click')\"><slot></slot></button>",
                    emits: ["click"],
                },
            },
        },
        props,
    });
    const userStore = useUserStore();
    userStore.currentUser = { is_admin: isAdmin };
    await flushPromises();
    return wrapper;
}

describe("Libraries/LibraryFolder/LibraryFolderDataset/LibraryDataset.vue", () => {
    const globalConfig = getLocalVue();

    it("should display all buttons when user is Admin", async () => {
        const isAdmin = true;
        const wrapper = await mountLibraryDatasetWrapper(globalConfig, UNRESTRICTED_DATASET_ID, isAdmin);

        expect(wrapper.find(MODIFY_BUTTON).exists()).toBe(true);
        expect(wrapper.find(AUTO_DETECT_BUTTON).exists()).toBe(true);
        expect(wrapper.find(PERMISSIONS_BUTTON).exists()).toBe(true);
    });

    it("should not display 'Modify' and 'Auto-detect datatype' buttons when user cannot modify dataset", async () => {
        const wrapper = await mountLibraryDatasetWrapper(globalConfig, CANNOT_MODIFY_DATASET_ID);

        expect(wrapper.find(MODIFY_BUTTON).exists()).toBe(false);
        expect(wrapper.find(AUTO_DETECT_BUTTON).exists()).toBe(false);
    });

    it("should not display 'Permissions' button when user is not an administrator", async () => {
        const isAdmin = false;
        const wrapper = await mountLibraryDatasetWrapper(globalConfig, CANNOT_MANAGE_DATASET_ID, isAdmin);

        expect(wrapper.find(PERMISSIONS_BUTTON).exists()).toBe(false);
    });

    it("should display unrestricted dataset message when dataset is unrestricted", async () => {
        const wrapper = await mountLibraryDatasetWrapper(globalConfig, UNRESTRICTED_DATASET_ID);

        expect(wrapper.find(UNRESTRICTED_MESSAGE).exists()).toBe(true);
    });

    it("should not display unrestricted dataset message when dataset is restricted", async () => {
        const wrapper = await mountLibraryDatasetWrapper(globalConfig, RESTRICTED_DATASET_ID);

        expect(wrapper.find(UNRESTRICTED_MESSAGE).exists()).toBe(false);
    });

    it("should display dataset details in the table", async () => {
        const wrapper = await mountLibraryDatasetWrapper(globalConfig, UNRESTRICTED_DATASET_ID);

        // Wait for table to be fully rendered
        await flushPromises();
        await wrapper.vm.$nextTick();

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
        const wrapper = await mountLibraryDatasetWrapper(globalConfig, UNRESTRICTED_DATASET_ID);
        const peek = wrapper.find(PEEK_VIEW);

        expect(peek.text()).toBe(EXPECTED_DATASET_DATA.peek);
    });

    it.skip("should display input fields when `Modify` button is clicked", async () => {
        // TODO: This test needs more complex slot handling for edit mode
        // The Bootstrap-Vue rendering issue has been resolved for the other tests
        const wrapper = await mountLibraryDatasetWrapper(globalConfig, UNRESTRICTED_DATASET_ID);

        // Wait for initial render
        await flushPromises();
        await wrapper.vm.$nextTick();

        const modify_button = wrapper.find(MODIFY_BUTTON);

        expect(wrapper.find(DATASET_TABLE).html()).not.toContain("<input");
        expect(wrapper.vm.isEditMode).toBe(false);

        await modify_button.trigger("click");
        await flushPromises();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.isEditMode).toBe(true);
        expect(wrapper.find(DATASET_TABLE).html()).toContain("<input");
    });
});
