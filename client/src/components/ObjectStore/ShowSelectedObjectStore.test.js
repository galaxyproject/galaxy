import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import ShowSelectedObjectStore from "./ShowSelectedObjectStore";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";

const localVue = getLocalVue(true);
const TEST_OBJECT_ID = "os123";
const OBJECT_STORE_DATA = {
    object_store_id: TEST_OBJECT_ID,
    badges: [],
};

describe("ShowSelectedObjectStore", () => {
    let wrapper;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(async () => {
        axiosMock.restore();
    });

    it("should show a loading message and then a DescribeObjectStore component", async () => {
        axiosMock.onGet(`/api/object_stores/${TEST_OBJECT_ID}`).reply(200, OBJECT_STORE_DATA);
        wrapper = mount(ShowSelectedObjectStore, {
            propsData: { preferredObjectStoreId: TEST_OBJECT_ID, forWhat: "Data goes into..." },
            localVue,
            stubs: {
                LoadingSpan: true,
                DescribeObjectStore: true,
            },
        });
        let loadingEl = wrapper.find("loadingspan-stub");
        expect(loadingEl.exists()).toBeTruthy();
        expect(loadingEl.attributes("message")).toBeLocalizationOf("Loading object store details");
        await flushPromises();
        loadingEl = wrapper.find("loadingspan-stub");
        expect(loadingEl.exists()).toBeFalsy();
        expect(wrapper.find("describeobjectstore-stub").exists()).toBeTruthy();
    });
});
