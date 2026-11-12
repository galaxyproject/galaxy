import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import VisualizationEmbed from "./VisualizationEmbed.vue";

function mountVisualizationEmbed() {
    return mount(VisualizationEmbed as object, {
        props: { id: "viz-id" },
        global: { ...getLocalVue(), stubs: { SavedVisualization: true } },
    });
}

function embedCode(wrapper: ReturnType<typeof mountVisualizationEmbed>) {
    return (wrapper.get("input.embed-code-input").element as HTMLInputElement).value;
}

describe("VisualizationEmbed", () => {
    it("embeds the visualization widget at the default size", () => {
        const wrapper = mountVisualizationEmbed();
        expect(embedCode(wrapper)).toMatch(
            /^<iframe title="Galaxy Visualization" width="800px" height="600px" style="border: none;" src=".*widgets\/visualizations\/viz-id"><\/iframe>$/,
        );
    });

    it("puts the typed size into the embed code", async () => {
        const wrapper = mountVisualizationEmbed();
        const [width, height] = wrapper.findAll(".dimension-controls input");
        await width!.setValue("1000");
        await height!.setValue("450");
        expect(embedCode(wrapper)).toContain('width="1000px" height="450px"');
    });

    it("leaves out the size without default styling", async () => {
        const wrapper = mountVisualizationEmbed();
        await wrapper.get(".settings input[type=checkbox]").setValue(false);
        expect(wrapper.find(".dimension-controls").exists()).toBe(false);
        expect(embedCode(wrapper)).toMatch(/^<iframe title="Galaxy Visualization" src=".*"><\/iframe>$/);
    });

    it("previews the visualization in embed mode, as the widget shows it", async () => {
        const wrapper = mountVisualizationEmbed();
        await wrapper.findAll(".preview input[type=checkbox]").at(-1)!.setValue(true);
        expect(wrapper.findComponent({ name: "SavedVisualization" }).props("embed")).toBe(true);
    });
});
