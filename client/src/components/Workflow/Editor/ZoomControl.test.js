import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { maxZoom, minZoom } from "@/utils/zoomLevels";

import ZoomControl from "./ZoomControl.vue";

const SELECTORS = {
    ZOOM_OUT: "button[aria-label='Zoom Out']",
    RESET: "button.zoom-reset",
    ZOOM_IN: "button[aria-label='Zoom In']",
};

function mountZoomControl(zoomLevel) {
    return mount(ZoomControl, { props: { zoomLevel }, global: getLocalVue() });
}

describe("ZoomControl", () => {
    it("renders zoom out, reset and zoom in buttons with the current percentage", () => {
        const wrapper = mountZoomControl(1);

        const labels = wrapper.findAll("button").map((button) => button.attributes("aria-label"));
        expect(labels).toEqual(["Zoom Out", "100% zoom. Reset Zoom Level", "Zoom In"]);
        expect(wrapper.find(SELECTORS.RESET).text()).toContain("100%");
    });

    it.each([
        ["zoom out", 1, 0.9, SELECTORS.ZOOM_OUT],
        ["reset", 1, 1, SELECTORS.RESET],
        ["reset", 2, 1, SELECTORS.RESET],
        ["zoom in", 1, 1.1, SELECTORS.ZOOM_IN],
    ])("%s at zoom %s emits %s", async (_button, zoomLevel, expected, selector) => {
        const wrapper = mountZoomControl(zoomLevel);

        await wrapper.find(selector).trigger("click");

        expect(wrapper.emitted("onZoom")).toEqual([[expected]]);
    });

    it.each([
        ["zoom out", minZoom, SELECTORS.ZOOM_OUT],
        ["zoom in", maxZoom, SELECTORS.ZOOM_IN],
    ])("disables %s at zoom %s", async (_button, zoomLevel, selector) => {
        const wrapper = mountZoomControl(zoomLevel);
        const button = wrapper.find(selector);

        await button.trigger("click");

        expect(button.attributes("aria-disabled")).toBe("true");
        expect(wrapper.emitted("onZoom")).toBeUndefined();
    });
});
