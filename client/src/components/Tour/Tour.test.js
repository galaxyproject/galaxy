import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import TourList from "./TourList.vue";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import flushPromises from "flush-promises";

const localVue = getLocalVue();
const TEST_TOUR_URI = "/api/tours";

jest.mock("app");

describe("Tour", () => {
    let axiosMock;
    let wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(TEST_TOUR_URI).reply(200, [{ id: "foo", writable: false }]);
        wrapper = shallowMount(TourList, {
            propsData: {},
            localVue,
        });
        await flushPromises();
    });

    it("test tours", async () => {
        expect(wrapper.find("#tourList").exists()).toBeTruthy();
    });
});
