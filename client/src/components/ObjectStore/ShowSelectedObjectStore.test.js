import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { mockFetcher } from "@/api/schema/__mocks__";

import ShowSelectedObjectStore from "./ShowSelectedObjectStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";

jest.mock("@/api/schema");

const localVue = getLocalVue(true);
const TEST_OBJECT_ID = "os123";
const TEST_USER_OBJECT_STORE_ID = "user_objects://34";

const OBJECT_STORE_DATA = {
    description: null,
    object_store_id: TEST_OBJECT_ID,
    badges: [],
};

const USER_OBJECT_STORE_DATA = {
    description: null,
    object_store_id: TEST_USER_OBJECT_STORE_ID,
    badges: [],
};

describe("ShowSelectedObjectStore", () => {
    let wrapper;

    it("should show a loading message and then a DescribeObjectStore component", async () => {
        mockFetcher.path("/api/object_stores/{object_store_id}").method("get").mock({ data: OBJECT_STORE_DATA });
        wrapper = mount(ShowSelectedObjectStore, {
            propsData: { preferredObjectStoreId: TEST_OBJECT_ID, forWhat: "Data goes into..." },
            localVue,
        });
        let loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeTruthy();
        expect(loadingEl.find(".loading-message").text()).toContainLocalizationOf("Loading storage location details");
        await flushPromises();
        loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeFalsy();
        expect(wrapper.findComponent(DescribeObjectStore).exists()).toBeTruthy();
    });

    it("should fetch from the user based object store APIs for dynamic ids that are uris", async () => {
        mockFetcher
            .path("/api/object_store_instances/{user_object_store_id}")
            .method("get")
            .mock({ data: USER_OBJECT_STORE_DATA });
        // mockFetcher.path("/api/object_stores/{object_store_id}").method("get").mock({ data: OBJECT_STORE_DATA });

        wrapper = mount(ShowSelectedObjectStore, {
            propsData: { preferredObjectStoreId: TEST_USER_OBJECT_STORE_ID, forWhat: "Data goes into..." },
            localVue,
        });
        let loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeTruthy();
        expect(loadingEl.find(".loading-message").text()).toContainLocalizationOf("Loading storage location details");
        await flushPromises();
        loadingEl = wrapper.findComponent(LoadingSpan);
        expect(loadingEl.exists()).toBeFalsy();
        expect(wrapper.findComponent(DescribeObjectStore).exists()).toBeTruthy();
    });
});
