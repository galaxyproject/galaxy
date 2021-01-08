import { shallowMount } from "@vue/test-utils";
import Index from "./Index.vue";
import { getLocalVue } from "jest/helpers";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";

const TEST_PLUGINS_URL = "/api/remote_files/plugins";

const localVue = getLocalVue();

describe("Index.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(TEST_PLUGINS_URL).reply(200, [{ id: "foo", writable: false }]);
    });

    it("should render tabs", () => {
        // just make sure the component renders to catch obvious big errors
        const wrapper = shallowMount(Index, {
            propsData: {
                historyId: "test_id",
            },
            localVue,
        });
        expect(wrapper.exists("b-tabs-stub")).toBeTruthy();
    });

    afterEach(() => {
        axiosMock.restore();
    });
});
