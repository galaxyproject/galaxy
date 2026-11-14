import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import SavedVisualization from "./SavedVisualization.vue";

const { server, http } = useServerMock();

function serve(status: number, body: object) {
    server.use(http.untyped.get("/api/visualizations/viz-id", () => HttpResponse.json(body, { status })));
}

async function mountSaved(embed?: boolean) {
    const wrapper = mount(SavedVisualization as object, {
        props: { visualizationId: "viz-id", ...(embed ? { embed } : {}) },
        global: { ...getLocalVue(), stubs: { VisualizationFrame: true } },
    });
    await flushPromises();
    return wrapper;
}

describe("SavedVisualization", () => {
    it("shows Galaxy's error when the visualization cannot be loaded", async () => {
        serve(403, { err_msg: "You do not have access to this visualization.", err_code: 403002 });
        const wrapper = await mountSaved();
        expect(wrapper.text()).toContain("You do not have access to this visualization.");
        expect(wrapper.findComponent({ name: "VisualizationFrame" }).exists()).toBe(false);
    });

    it("says so when the visualization has no saved configuration", async () => {
        serve(200, { type: "example", title: "My Plot", latest_revision: null });
        const wrapper = await mountSaved();
        expect(wrapper.text()).toContain("This visualization has no saved configuration.");
        expect(wrapper.findComponent({ name: "VisualizationFrame" }).exists()).toBe(false);
    });

    it("mounts the plugin with the saved configuration", async () => {
        serve(200, { type: "example", title: "My Plot", latest_revision: { config: { dataset_id: "d1" } } });
        const wrapper = await mountSaved(true);
        expect(wrapper.findComponent({ name: "VisualizationFrame" }).props()).toMatchObject({
            name: "example",
            title: "My Plot",
            config: { dataset_id: "d1" },
            embed: true,
        });
    });
});
