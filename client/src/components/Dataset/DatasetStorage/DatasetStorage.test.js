import { shallowMount } from "@vue/test-utils";
import DatasetStorage from "./DatasetStorage";
import { getLocalVue } from "jest/helpers";
import flushPromises from "flush-promises";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import MarkdownIt from "markdown-it";

const localVue = getLocalVue();

const TEST_STORAGE_API_RESPONSE_WITHOUT_ID = {
    object_store_id: null,
};
const TEST_STORAGE_API_RESPONSE_WITH_ID = {
    object_store_id: "foobar",
};
const TEST_STORAGE_API_RESPONSE_WITH_NAME = {
    object_store_id: "foobar",
    name: "my cool storage",
    description: "My cool **markdown**",
};
const TEST_DATASET_ID = "1";
const TEST_STORAGE_URL = `/api/datasets/${TEST_DATASET_ID}/storage`;
const TEST_RENDERED_MARKDOWN_AS_HTML = "<p>My cool <strong>markdown</strong>\n";
const TEST_ERROR_MESSAGE = "Opps all errors.";

// works fine without mocking but I guess it is more JS unit-y with the mock?
jest.mock("markdown-it");
MarkdownIt.mockImplementation(() => {
    return {
        render(markdown) {
            return TEST_RENDERED_MARKDOWN_AS_HTML;
        },
    };
});

describe("Dataset Storage", () => {
    let axiosMock;
    let wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    function mount() {
        wrapper = shallowMount(DatasetStorage, {
            propsData: { datasetId: TEST_DATASET_ID },
            localVue,
            stubs: {
                "loading-span": true,
            },
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
        expect(wrapper.vm.descriptionRendered).toBeNull();
        const header = wrapper.findAll("h3");
        expect(header.length).toBe(1);
        expect(header.at(0).text()).toBe("Dataset Storage");
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(0);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(0);
        const byDefaultSpan = wrapper.findAll(".display-os-default");
        expect(byDefaultSpan.length).toBe(1);
    });

    it("test dataset storage with object store id", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_ID);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.vm.storageInfo.object_store_id).toBe("foobar");
        expect(wrapper.vm.descriptionRendered).toBeNull();
        const header = wrapper.findAll("h3");
        expect(header.length).toBe(1);
        expect(header.at(0).text()).toBe("Dataset Storage");
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(1);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(0);
    });

    it("test dataset storage with object store name", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_NAME);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.vm.storageInfo.object_store_id).toBe("foobar");
        expect(wrapper.vm.descriptionRendered).toBe(TEST_RENDERED_MARKDOWN_AS_HTML);
        const header = wrapper.findAll("h3");
        expect(header.length).toBe(1);
        expect(header.at(0).text()).toBe("Dataset Storage");
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(0);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(1);
    });

    afterEach(() => {
        axiosMock.restore();
    });
});
