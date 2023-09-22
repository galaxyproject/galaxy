import { shallowMount } from "@vue/test-utils";
import DatasetStorage from "./DatasetStorage";
import { getLocalVue } from "tests/jest/helpers";
import flushPromises from "flush-promises";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";

const localVue = getLocalVue();

const TEST_STORAGE_API_RESPONSE_WITHOUT_ID = {
    object_store_id: null,
    private: false,
};
const TEST_DATASET_ID = "1";
const TEST_STORAGE_URL = `/api/datasets/${TEST_DATASET_ID}/storage`;
const TEST_ERROR_MESSAGE = "Opps all errors.";

describe("DatasetStorage.vue", () => {
    let axiosMock;
    let wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    function mount() {
        wrapper = shallowMount(DatasetStorage, {
            propsData: { datasetId: TEST_DATASET_ID },
            localVue,
        });
    }

    async function mountWithResponse(response) {
        axiosMock.onGet(TEST_STORAGE_URL).reply(200, response);
        mount();
        await flushPromises();
    }

    it("test loading...", async () => {
        mount();
        await wrapper.vm.$nextTick();
        expect(wrapper.findAll("loading-span-stub").length).toBe(1);
        expect(wrapper.findAll("describe-object-store-stub").length).toBe(0);
    });

    it("test error rendering...", async () => {
        axiosMock.onGet(TEST_STORAGE_URL).reply(400, {
            err_msg: TEST_ERROR_MESSAGE,
        });
        mount();
        await flushPromises();
        expect(wrapper.findAll(".error").length).toBe(1);
        expect(wrapper.findAll(".error").at(0).text()).toBe(TEST_ERROR_MESSAGE);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
    });

    it("test dataset storage with object store without id", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITHOUT_ID);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.findAll("describe-object-store-stub").length).toBe(1);
        expect(wrapper.vm.storageInfo.private).toEqual(false);
    });

    afterEach(() => {
        axiosMock.restore();
    });
});
