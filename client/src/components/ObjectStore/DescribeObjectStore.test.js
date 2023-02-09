import { shallowMount } from "@vue/test-utils";
import DescribeObjectStore from "./DescribeObjectStore";
import { getLocalVue } from "tests/jest/helpers";
import MarkdownIt from "markdown-it";

const localVue = getLocalVue();

const TEST_STORAGE_API_RESPONSE_WITHOUT_ID = {
    object_store_id: null,
    private: false,
    badges: [],
};
const TEST_RENDERED_MARKDOWN_AS_HTML = "<p>My cool <strong>markdown</strong>\n";

const TEST_STORAGE_API_RESPONSE_WITH_ID = {
    object_store_id: "foobar",
    private: false,
    badges: [],
};
const TEST_STORAGE_API_RESPONSE_WITH_NAME = {
    object_store_id: "foobar",
    name: "my cool storage",
    description: "My cool **markdown**",
    private: true,
    badges: [],
};

// works fine without mocking but I guess it is more JS unit-y with the mock?
jest.mock("markdown-it");
MarkdownIt.mockImplementation(() => {
    return {
        render(markdown) {
            return TEST_RENDERED_MARKDOWN_AS_HTML;
        },
    };
});

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
        expect(wrapper.vm.descriptionRendered).toBeNull();
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
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(1);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(0);
        expect(wrapper.find("object-store-restriction-span-stub").props("isPrivate")).toBeFalsy();
    });

    it("test dataset storage with object store name", async () => {
        await mountWithResponse(TEST_STORAGE_API_RESPONSE_WITH_NAME);
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.vm.storageInfo.object_store_id).toBe("foobar");
        expect(wrapper.vm.descriptionRendered).toBe(TEST_RENDERED_MARKDOWN_AS_HTML);
        const byIdSpan = wrapper.findAll(".display-os-by-id");
        expect(byIdSpan.length).toBe(0);
        const byNameSpan = wrapper.findAll(".display-os-by-name");
        expect(byNameSpan.length).toBe(1);
        expect(wrapper.find("object-store-restriction-span-stub").props("isPrivate")).toBeTruthy();
    });
});
