import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import DescribeObjectStore from "./DescribeObjectStore";

const localVue = getLocalVue();

const DESCRIPTION = "My cool **markdown**";

const TEST_STORAGE_API_RESPONSE_WITHOUT_ID = {
    object_store_id: null,
    private: false,
    description: DESCRIPTION,
    badges: [],
};

const TEST_STORAGE_API_RESPONSE_WITH_ID = {
    object_store_id: "foobar",
    private: false,
    description: DESCRIPTION,
    badges: [],
};
const TEST_STORAGE_API_RESPONSE_WITH_NAME = {
    object_store_id: "foobar",
    name: "my cool storage",
    description: DESCRIPTION,
    private: true,
    badges: [],
};

describe("DescribeObjectStore.vue", () => {
    let wrapper;

    async function mountWithResponse(response) {
        wrapper = shallowMount(DescribeObjectStore, {
            propsData: { storageInfo: response, what: "where i am throwing my test dataset" },
            localVue,
        });
    }

    it("test dataset storage with object store without id", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITHOUT_ID);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
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
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(1);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(0);
        expect(wrapper.vm.isPrivate).toBeFalsy();
    });

    it("test dataset storage with object store name", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_NAME);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.vm.storageInfo.object_store_id).toBe("foobar");
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(0);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(1);
        expect(wrapper.vm.isPrivate).toBeTruthy();
        const configurationMarkupEl = wrapper.find("[markdown]");
        expect(configurationMarkupEl.attributes("markdown")).toBe(DESCRIPTION);
    });
});
