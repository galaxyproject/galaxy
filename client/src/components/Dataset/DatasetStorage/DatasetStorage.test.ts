import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue, suppressDebugConsole } from "tests/jest/helpers";

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
const TEST_ERROR_MESSAGE = "Opps all errors.";

const { server, http } = useServerMock();

describe("DatasetStorage.vue", () => {
    let wrapper: any;

    function mount(options: { simulateError: boolean } = { simulateError: false }) {
        server.use(
            http.get("/api/datasets/{dataset_id}/storage", ({ response }) => {
                if (options.simulateError) {
                    return response("5XX").json({ err_msg: TEST_ERROR_MESSAGE, err_code: 500 }, { status: 500 });
                }
                return response(200).json(TEST_STORAGE_API_RESPONSE_WITHOUT_ID);
            })
        );

        wrapper = shallowMount(DatasetStorage as object, {
            propsData: { datasetId: TEST_DATASET_ID },
            localVue,
        });
    }

    it("test loading...", async () => {
        mount();
        // Do not await flushPromises here so the API call is not resolved
        expect(wrapper.findAll("loadingspan-stub").length).toBe(1);
        expect(wrapper.findAll("describeobjectstore-stub").length).toBe(0);

        await flushPromises();
        expect(wrapper.findAll("loadingspan-stub").length).toBe(0);
        expect(wrapper.findAll("describeobjectstore-stub").length).toBe(1);
    });

    it("test error rendering...", async () => {
        suppressDebugConsole();
        mount({ simulateError: true });
        await flushPromises();
        expect(wrapper.findAll(".error").length).toBe(1);
        expect(wrapper.findAll(".error").at(0).text()).toBe(TEST_ERROR_MESSAGE);
        expect(wrapper.findAll("loadingspan-stub").length).toBe(0);
    });

    it("test dataset storage with object store without id", async () => {
        mount();
        await flushPromises();
        expect(wrapper.findAll("loadingspan-stub").length).toBe(0);
        expect(wrapper.findAll("describeobjectstore-stub").length).toBe(1);
    });
});
