import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { mockFetcher } from "@/api/schema/__mocks__";

import DatasetStorage from "./DatasetStorage";

jest.mock("@/api/schema");

const localVue = getLocalVue();

const TEST_STORAGE_API_RESPONSE_WITHOUT_ID = {
    object_store_id: null,
    private: false,
};
const TEST_DATASET_ID = "1";
const STORAGE_FETCH_URL = "/api/datasets/{dataset_id}/storage";
const TEST_ERROR_MESSAGE = "Opps all errors.";

describe("DatasetStorage.vue", () => {
    let wrapper;

    function mount() {
        wrapper = shallowMount(DatasetStorage, {
            propsData: { datasetId: TEST_DATASET_ID },
            localVue,
        });
    }

    async function mountWithResponse(response) {
        mockFetcher.path(STORAGE_FETCH_URL).method("get").mock({ data: response });
        mount();
        await flushPromises();
    }

    it("test loading...", async () => {
        mount();
        await wrapper.vm.$nextTick();
        expect(wrapper.findAll("loadingspan-stub").length).toBe(1);
        expect(wrapper.findAll("describeobjectstore-stub").length).toBe(0);
    });

    it("test error rendering...", async () => {
        mockFetcher
            .path(STORAGE_FETCH_URL)
            .method("get")
            .mock(() => {
                throw Error(TEST_ERROR_MESSAGE);
            });
        mount();
        await flushPromises();
        expect(wrapper.findAll(".error").length).toBe(1);
        expect(wrapper.findAll(".error").at(0).text()).toBe(TEST_ERROR_MESSAGE);
        expect(wrapper.findAll("loadingspan-stub").length).toBe(0);
    });

    it("test dataset storage with object store without id", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITHOUT_ID);
        expect(wrapper.findAll("loadingspan-stub").length).toBe(0);
        expect(wrapper.findAll("describeobjectstore-stub").length).toBe(1);
    });
});
