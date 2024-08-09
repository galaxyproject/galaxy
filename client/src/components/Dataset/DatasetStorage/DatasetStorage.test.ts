import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { type DatasetStorageDetails } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import DatasetStorage from "./DatasetStorage.vue";

const localVue = getLocalVue();

const TEST_STORAGE_API_RESPONSE_WITHOUT_ID: DatasetStorageDetails = {
    object_store_id: null,
    name: "Test name",
    description: "Test description",
    dataset_state: "ok",
    quota: { enabled: false, source: null },
    relocatable: false,
    shareable: false,
    badges: [],
    hashes: [],
    sources: [],
    percent_used: 0,
};
const TEST_DATASET_ID = "1";
const STORAGE_FETCH_URL = "/api/datasets/{dataset_id}/storage";
const TEST_ERROR_MESSAGE = "Opps all errors.";

const { server, http } = useServerMock();

describe("DatasetStorage.vue", () => {
    let wrapper: any;

    function mount() {
        wrapper = shallowMount(DatasetStorage, {
            propsData: { datasetId: TEST_DATASET_ID },
            localVue,
        });
    }

    async function mountWithResponse(resp: DatasetStorageDetails) {
        server.use(
            http.get(STORAGE_FETCH_URL, ({ response }) => {
                return response(200).json(resp);
            })
        );
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
        server.use(
            http.get(STORAGE_FETCH_URL, ({ response }) => {
                return response("5XX").json({ err_msg: TEST_ERROR_MESSAGE, err_code: 500 }, { status: 500 });
            })
        );

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
