import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ZoomControl from "./ZoomControl.vue";

const localVue = getLocalVue();

describe("ZoomControl", () => {
    it("keeps the displayed zoom percentage in the reset button's accessible name", async () => {
        const wrapper = mount(ZoomControl, { props: { zoomLevel: 0.75 }, global: localVue });
        const reset = wrapper.get(".zoom-reset");

        expect(reset.text()).toContain("75%");
        expect(reset.attributes("aria-label")).toBe("75% zoom. Reset Zoom Level");
        await reset.trigger("click");
        expect(wrapper.emitted("onZoom")).toEqual([[1]]);

        await wrapper.setProps({ zoomLevel: 1.25 });
        expect(reset.attributes("aria-label")).toBe("125% zoom. Reset Zoom Level");
    });
});
