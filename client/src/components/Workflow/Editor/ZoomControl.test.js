import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import ZoomControl from "./ZoomControl";

jest.mock("app");

describe("ZoomControl", () => {
    it("test zoom control", async () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(ZoomControl, {
            props: {
                zoomLevel: 1,
            },
            global: globalConfig.global,
        });
        const buttons = wrapper.findAll("button");
        expect(buttons.length).toBe(3);
        await buttons[0].trigger("click");
        expect(wrapper.emitted().onZoom[0][0]).toBe(0.9);
        await buttons[1].trigger("click");
        expect(wrapper.emitted().onZoom[1][0]).toBe(1);
        await buttons[2].trigger("click");
        expect(wrapper.emitted().onZoom[2][0]).toBe(1.1);
    });
});
