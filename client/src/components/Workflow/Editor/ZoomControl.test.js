import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ZoomControl from "./ZoomControl.vue";

vi.mock("app");

describe("ZoomControl", () => {
    it("test zoom control", async () => {
        const localVue = getLocalVue();
        const wrapper = mount(ZoomControl, {
            props: {
                zoomLevel: 1,
            },
            global: localVue,
        });
        const buttons = wrapper.findAll("button");
        expect(buttons.length).toBe(3);
        await buttons.at(0).trigger("click");
        expect(emittedArg(wrapper, "onZoom")).toBe(0.9);
        await buttons.at(1).trigger("click");
        expect(emittedArg(wrapper, "onZoom", 1)).toBe(1);
        await buttons.at(2).trigger("click");
        expect(emittedArg(wrapper, "onZoom", 2)).toBe(1.1);
    });
});
