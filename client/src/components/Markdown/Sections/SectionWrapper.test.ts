import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { MARKDOWN_CELL_TYPES } from "@/components/Markdown/directives";

import SectionWrapper from "./SectionWrapper.vue";

describe("SectionWrapper.vue", () => {
    it.each(MARKDOWN_CELL_TYPES)("renders the %s cell type", (name) => {
        const wrapper = shallowMount(SectionWrapper as object, { propsData: { content: "", name } });
        expect(wrapper.findComponent({ name: "GAlert" }).exists()).toBe(false);
    });

    it("reports unknown cell types", () => {
        const wrapper = shallowMount(SectionWrapper as object, { propsData: { content: "", name: "python" } });
        expect(wrapper.findComponent({ name: "GAlert" }).exists()).toBe(true);
    });
});
