import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import ZoomControl from "./ZoomControl";

jest.mock("app");

describe("ZoomControl", () => {
    it("test zoom control", async () => {
        const localVue = getLocalVue();
        const wrapper = mount(ZoomControl, {
            propsData: {
                zoomLevel: 1,
            },
            localVue,
        });
        const buttons = wrapper.findAll("button");
        expect(buttons.length).toBe(3);
        await buttons.at(0).trigger("click");
        expect(wrapper.emitted().onZoom[0][0]).toBe(0.9);
        await buttons.at(1).trigger("click");
        expect(wrapper.emitted().onZoom[1][0]).toBe(1);
        await buttons.at(2).trigger("click");
        expect(wrapper.emitted().onZoom[2][0]).toBe(1.1);
    });
});
