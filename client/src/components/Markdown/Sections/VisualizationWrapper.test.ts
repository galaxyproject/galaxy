import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { ref } from "vue";

import { embedKey } from "@/composables/embed";

import VisualizationWrapper from "./VisualizationWrapper.vue";

function frameEmbed(provide: Record<symbol, unknown> = {}) {
    const wrapper = mount(VisualizationWrapper as object, {
        props: { name: "example", config: {} },
        global: { provide, stubs: { VisualizationFrame: true, FontAwesomeIcon: true } },
    });
    return wrapper.findComponent({ name: "VisualizationFrame" }).props("embed");
}

describe("VisualizationWrapper", () => {
    it("embeds the visualization when the page around it is embedded", () => {
        expect(frameEmbed({ [embedKey]: ref(true) })).toBe(true);
        expect(frameEmbed()).toBe(false);
    });
});
