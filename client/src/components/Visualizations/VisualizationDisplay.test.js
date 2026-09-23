import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import VisualizationDisplay from "./VisualizationDisplay.vue";

vi.mock("vue-router/composables", () => ({ onBeforeRouteLeave: vi.fn() }));
vi.mock("@/api", () => ({
    GalaxyApi: () => ({
        GET: async () => ({ data: { title: "Saved chart", latest_revision: { config: { a: 1 } } }, error: null }),
    }),
}));
vi.mock("@/components/Visualizations/VisualizationFrame.vue", () => ({
    default: {
        name: "VisualizationFrame",
        props: ["config", "name", "title", "visualizationId"],
        render: (h) => h("div"),
    },
}));

const FRAME = { name: "VisualizationFrame" };

let wrapper;

async function mountDisplay(propsData = { visualization: "example", datasetId: "d1" }) {
    wrapper = mount(VisualizationDisplay, {
        propsData,
        stubs: { LoadingSpan: true, BAlert: true },
    });
    await flushPromises();
    return wrapper;
}

const report = (payload) => wrapper.findComponent(FRAME).vm.$emit("change", payload);

function unloadIsBlocked() {
    return !window.dispatchEvent(new Event("beforeunload", { cancelable: true }));
}

describe("VisualizationDisplay.vue", () => {
    beforeEach(() => {
        wrapper = undefined;
    });

    afterEach(() => {
        wrapper?.destroy();
    });

    it("does not warn before the visualization reports anything", async () => {
        await mountDisplay();
        expect(unloadIsBlocked()).toBe(false);
    });

    it("warns once the visualization reports an unsaved change", async () => {
        await mountDisplay();
        await report({ visualization_config: { a: 1 }, visualization_saved: false });
        expect(unloadIsBlocked()).toBe(true);
    });

    it("stops warning once the visualization reports it saved", async () => {
        await mountDisplay();
        await report({ visualization_config: { a: 1 }, visualization_saved: false });
        await report({ visualization_config: { a: 1 }, visualization_saved: true });
        expect(unloadIsBlocked()).toBe(false);
    });

    it("warns again after a change that follows a save", async () => {
        await mountDisplay();
        await report({ visualization_config: { a: 1 }, visualization_saved: true });
        await report({ visualization_config: { a: 2 }, visualization_saved: false });
        expect(unloadIsBlocked()).toBe(true);
    });

    it("hands the plugin the title the saved visualization was stored under", async () => {
        await mountDisplay({ visualization: "example", visualizationId: "v1" });
        expect(wrapper.findComponent(FRAME).props("title")).toBe("Saved chart");
    });

    it("does not warn for a plugin that never reports its saved state", async () => {
        await mountDisplay();
        await report({ visualization_config: { a: 1 } });
        expect(unloadIsBlocked()).toBe(false);
    });

    it("stops warning for a visualization that has been left", async () => {
        await mountDisplay();
        await report({ visualization_config: { a: 1 }, visualization_saved: false });
        wrapper.destroy();
        expect(unloadIsBlocked()).toBe(false);
    });
});
