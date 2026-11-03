import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import VisualizationWrapper from "./VisualizationWrapper.vue";
import VisualizationFrame from "@/components/Visualizations/VisualizationFrame.vue";

enableAutoUnmount(afterEach);

const MAXIMIZE_BUTTON = "button[title='Maximize']";
const MINIMIZE_BUTTON = "button[title='Minimize']";

const config = { dataset_id: "dataset-1" };

function mountVisualizationWrapper(props: { title?: string; height?: number } = {}) {
    return mount(VisualizationWrapper, {
        props: { config, name: "vitessce", ...props },
        global: {
            ...getLocalVue(),
            stubs: { VisualizationFrame: true },
        },
    });
}

describe("VisualizationWrapper.vue", () => {
    it("renders the named visualization at the default height", () => {
        const wrapper = mountVisualizationWrapper();

        const frame = wrapper.getComponent(VisualizationFrame);
        expect(frame.props()).toMatchObject({ name: "vitessce", config, title: "visualization" });
        expect(frame.attributes("style")).toContain("max-height: 400px");
        expect(frame.attributes("style")).toContain("min-height: 400px");
    });

    it("renders the visualization with the given title and height", () => {
        const wrapper = mountVisualizationWrapper({ title: "Cell atlas", height: 250 });

        const frame = wrapper.getComponent(VisualizationFrame);
        expect(frame.props("title")).toBe("Cell atlas");
        expect(frame.attributes("style")).toContain("max-height: 250px");
    });

    it("lets the user maximize the visualization and minimize it again", async () => {
        const wrapper = mountVisualizationWrapper();
        expect(wrapper.find(".visualization-popin").exists()).toBe(true);
        expect(wrapper.find(MINIMIZE_BUTTON).exists()).toBe(false);

        await wrapper.get(MAXIMIZE_BUTTON).trigger("click");

        expect(wrapper.find(".visualization-popout").exists()).toBe(true);
        expect(wrapper.getComponent(VisualizationFrame).attributes("style")).toBeUndefined();

        await wrapper.get(MINIMIZE_BUTTON).trigger("click");

        expect(wrapper.find(".visualization-popin").exists()).toBe(true);
        expect(wrapper.find(MINIMIZE_BUTTON).exists()).toBe(false);
        expect(wrapper.getComponent(VisualizationFrame).attributes("style")).toContain("max-height: 400px");
    });

    it("forwards change and load events from the visualization", () => {
        const wrapper = mountVisualizationWrapper();
        const frame = wrapper.getComponent(VisualizationFrame);

        frame.vm.$emit("change", { zoom: 2 });
        frame.vm.$emit("load");

        expect(wrapper.emitted("change")).toEqual([[{ zoom: 2 }]]);
        expect(wrapper.emitted("load")).toHaveLength(1);
    });
});
