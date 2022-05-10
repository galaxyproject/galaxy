import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import exportsMixin from "./exportsMixin";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
const TEST_PLUGINS_URL = "/api/remote_files/plugins";

const localVue = getLocalVue();

const Component = {
    render() {},
    mixins: [exportsMixin],
};

describe("exportsMixin.js", () => {
    let wrapper;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        const propsData = {};
        wrapper = shallowMount(Component, propsData, localVue);
    });

    function mockGet(writable) {
        axiosMock.onGet(TEST_PLUGINS_URL).reply(200, [{ id: "foo", writable: writable }]);
    }

    afterEach(async () => {
        axiosMock.restore();
    });

    it("should be initially uninitialized", async () => {
        expect(wrapper.vm.initializingFileSources).toBeTruthy();
    });

    it("should be initialized after fetching configuration", async () => {
        mockGet(false);
        await wrapper.vm.initializeFilesSources();
        expect(wrapper.vm.initializingFileSources).toBeFalsy();
        expect(wrapper.vm.hasWritableFileSources).toBeFalsy();
    });

    it("should be have writable sources if any are writable", async () => {
        mockGet(true);
        await wrapper.vm.initializeFilesSources();
        expect(wrapper.vm.initializingFileSources).toBeFalsy();
        expect(wrapper.vm.hasWritableFileSources).toBeTruthy();
    });
});
