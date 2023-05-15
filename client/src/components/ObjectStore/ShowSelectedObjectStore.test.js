import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import ShowSelectedObjectStore from "./ShowSelectedObjectStore";
import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";
import flushPromises from "flush-promises";
import { mockFetcher } from "@/schema/__mocks__";

jest.mock("@/schema");

const localVue = getLocalVue(true);
const TEST_OBJECT_ID = "os123";
const OBJECT_STORE_DATA = {
    description: null,
    object_store_id: TEST_OBJECT_ID,
    badges: [],
};

describe("ShowSelectedObjectStore", () => {
    let wrapper;

    it("should show a loading message and then a DescribeObjectStore component", async () => {
        mockFetcher.path("/api/object_stores/{object_store_id}").method("get").mock({ data: OBJECT_STORE_DATA });
        wrapper = mount(ShowSelectedObjectStore, {
            propsData: { preferredObjectStoreId: TEST_OBJECT_ID, forWhat: "Data goes into..." },
            localVue,
            stubs: {
                LoadingSpan: true,
                DescribeObjectStore: true,
            },
        });
        let loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeTruthy();
        expect(loadingEl.find(".loading-message").text()).toContainLocalizationOf("Loading object store details");
        await flushPromises();
        loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeFalsy();
        expect(wrapper.findComponent(DescribeObjectStore).exists()).toBeTruthy();
    });
});
