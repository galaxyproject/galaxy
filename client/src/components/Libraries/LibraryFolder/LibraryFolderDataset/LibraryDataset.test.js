import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";
import { useUserStore } from "@/stores/userStore";

import cannotManageDatasetResponse from "./testData/cannotManageDataset.json";
import cannotModifyDatasetResponse from "./testData/cannotModifyDataset.json";
import restrictedDatasetResponse from "./testData/restrictedDataset.json";
import unrestrictedDatasetResponse from "./testData/unrestrictedDataset.json";

import LibraryDataset from "./LibraryDataset.vue";

const FOLDER_ID = "test_folder_id";
const UNRESTRICTED_DATASET_ID = "unrestricted_dataset_id";
const RESTRICTED_DATASET_ID = "restricted_dataset_id";
const CANNOT_MODIFY_DATASET_ID = "cannot_modify_dataset_id";
const CANNOT_MANAGE_DATASET_ID = "cannot_manage_dataset_id";
const EXPECTED_DATASET_DATA = unrestrictedDatasetResponse;

const responseMap = new Map([
    [UNRESTRICTED_DATASET_ID, unrestrictedDatasetResponse],
    [RESTRICTED_DATASET_ID, restrictedDatasetResponse],
    [CANNOT_MODIFY_DATASET_ID, cannotModifyDatasetResponse],
    [CANNOT_MANAGE_DATASET_ID, cannotManageDatasetResponse],
]);

vi.mock("../services", () => ({
    Services: class Services {
        async getDataset(datasetId) {
            return responseMap.get(datasetId);
        }
        async updateDataset(_datasetId, data) {
            return data;
        }
    },
}));

const SELECTORS = {
    MODIFY_BUTTON: '[data-test-id="modify-btn"]',
    AUTO_DETECT_BUTTON: '[data-test-id="auto-detect-btn"]',
    PERMISSIONS_BUTTON: '[data-test-id="permissions-btn"]',
    UNRESTRICTED_MESSAGE: '[data-test-id="unrestricted-msg"]',
    DATASET_TABLE: '[data-test-id="dataset-table"]',
    PEEK_VIEW: '[data-test-id="peek-view"]',
};

/** The dataset fields the details table lists, read off the unrestricted dataset */
const TABLE_FIELDS = [
    "name",
    "file_ext",
    "genome_build",
    "file_size",
    "update_time",
    "date_uploaded",
    "uploaded_by",
    "misc_blurb",
    "misc_info",
    "uuid",
];

// setup() (not an options-API `render() { this.$slots }` method) -- the latter gets
// routed through Vue compat's legacy `with(this)` render-context wrapping
// (RENDER_FUNCTION compat), which breaks a hand-built component like this.
function loadedProviderStub(item, error) {
    return {
        setup(_props, { slots }) {
            return () => slots.default?.({ loading: false, item, error });
        },
    };
}

const localVue = getLocalVue();

async function mountLibraryDataset(
    datasetId,
    { isAdmin = false, datatypesProvider = loadedProviderStub(["xml"]) } = {},
) {
    const wrapper = mount(LibraryDataset, {
        props: {
            dataset_id: datasetId,
            folder_id: FOLDER_ID,
        },
        global: {
            ...withPlugins(localVue, createPinia()),
            stubs: {
                ...localVue.stubs,
                DatatypesProvider: datatypesProvider,
                DbKeyProvider: loadedProviderStub(["?"]),
            },
        },
    });
    useUserStore().currentUser = getFakeRegisteredUser({ is_admin: isAdmin });
    await flushPromises();
    return wrapper;
}

describe("LibraryDataset", () => {
    it("shows the modify, auto-detect and permissions buttons to an admin", async () => {
        const wrapper = await mountLibraryDataset(UNRESTRICTED_DATASET_ID, { isAdmin: true });

        expect(wrapper.find(SELECTORS.MODIFY_BUTTON).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.AUTO_DETECT_BUTTON).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.PERMISSIONS_BUTTON).exists()).toBe(true);
    });

    it("hides the modify and auto-detect buttons when the user cannot modify the dataset", async () => {
        const wrapper = await mountLibraryDataset(CANNOT_MODIFY_DATASET_ID);

        expect(wrapper.find(SELECTORS.MODIFY_BUTTON).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.AUTO_DETECT_BUTTON).exists()).toBe(false);
    });

    it("hides the permissions button from a user who is not an admin", async () => {
        const wrapper = await mountLibraryDataset(CANNOT_MANAGE_DATASET_ID, { isAdmin: false });

        expect(wrapper.find(SELECTORS.PERMISSIONS_BUTTON).exists()).toBe(false);
    });

    it("says an unrestricted dataset is unrestricted", async () => {
        const wrapper = await mountLibraryDataset(UNRESTRICTED_DATASET_ID);

        expect(wrapper.find(SELECTORS.UNRESTRICTED_MESSAGE).exists()).toBe(true);
    });

    it("omits the unrestricted message for a restricted dataset", async () => {
        const wrapper = await mountLibraryDataset(RESTRICTED_DATASET_ID);

        expect(wrapper.find(SELECTORS.UNRESTRICTED_MESSAGE).exists()).toBe(false);
    });

    it("lists the dataset details in the table", async () => {
        const wrapper = await mountLibraryDataset(UNRESTRICTED_DATASET_ID);

        const tableHtml = wrapper.find(SELECTORS.DATASET_TABLE).html();
        for (const field of TABLE_FIELDS) {
            expect(tableHtml).toContain(EXPECTED_DATASET_DATA[field]);
        }
    });

    it("shows the dataset peek", async () => {
        const wrapper = await mountLibraryDataset(UNRESTRICTED_DATASET_ID);

        expect(wrapper.find(SELECTORS.PEEK_VIEW).text()).toBe(EXPECTED_DATASET_DATA.peek);
    });

    it("renders the dataset peek through v-sanitize-html", async () => {
        vi.mocked(sanitizeHtml).mockClear();

        await mountLibraryDataset(UNRESTRICTED_DATASET_ID);

        expect(sanitizeHtml).toHaveBeenCalledWith(EXPECTED_DATASET_DATA.peek, "default");
    });

    it("turns the table into input fields when Modify is clicked", async () => {
        const wrapper = await mountLibraryDataset(UNRESTRICTED_DATASET_ID);
        expect(wrapper.find(SELECTORS.DATASET_TABLE).html()).not.toContain("<input");

        await wrapper.find(SELECTORS.MODIFY_BUTTON).trigger("click");
        await flushPromises();

        expect(wrapper.find(SELECTORS.DATASET_TABLE).html()).toContain("<input");
    });

    it("shows the current datatype and a load error when datatypes fail to load", async () => {
        const wrapper = await mountLibraryDataset(UNRESTRICTED_DATASET_ID, {
            datatypesProvider: loadedProviderStub([], "unavailable"),
        });
        await wrapper.find(SELECTORS.MODIFY_BUTTON).trigger("click");
        await flushPromises();

        const error = wrapper.find('[data-test-id="datatypes-error"]');
        expect(error.exists()).toBe(true);
        expect(error.text()).toContain(EXPECTED_DATASET_DATA.file_ext);
        expect(error.text()).toContain("Unable to load datatypes");
    });
});
