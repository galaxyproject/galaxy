import { getFakeTool } from "@tests/test-data/tools";
import { emittedArg, getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { Tool, ToolSection as ToolSectionType, ToolSectionLabel } from "@/stores/toolStore";

import ToolSection from "./ToolSection.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: ref({ toolbox_auto_sort: true }),
        isConfigLoaded: ref(true),
    })),
}));

enableAutoUnmount(afterEach);

function createSection(elems: (ToolSectionType | ToolSectionLabel | Tool)[]): ToolSectionType {
    return {
        model_class: "ToolSection",
        id: "tool_section",
        name: "tool_section",
        title: "tool_section",
        // Labels render in sections although the store's elems type omits them.
        elems: elems as ToolSectionType["elems"],
    };
}

function mountCategory(category: Tool | ToolSectionType, props: { queryFilter?: string; sortItems?: boolean } = {}) {
    return mount(ToolSection, {
        props: { category, ...props },
        global: withPlugins(getLocalVue(), createPinia()),
    });
}

function toolAndLabel() {
    return createSection([
        getFakeTool({ name: "name" }),
        { model_class: "ToolSectionLabel", id: "label", text: "text" },
    ]);
}

function sectionIsOpened(wrapper: VueWrapper) {
    return wrapper.find("[data-description='opened tool panel section']").exists();
}

describe("ToolSection", () => {
    it("forwards a clicked tool through the onClick event", async () => {
        const tool = getFakeTool({ name: "name" });
        const wrapper = mountCategory(tool);
        const nameElement = wrapper.get(".name");
        expect(nameElement.text()).toBe("name");
        await nameElement.trigger("click");
        expect(emittedArg(wrapper, "onClick")).toEqual(tool);
    });

    it("shows a section title and collapses its tools after toggling", async () => {
        const wrapper = mountCategory(toolAndLabel());
        expect(sectionIsOpened(wrapper)).toBe(false);
        const $sectionName = wrapper.find(".name");
        expect($sectionName.text()).toBe("tool_section");
        await $sectionName.trigger("click");
        const $names = wrapper.findAll(".name");
        expect(nth($names, 1).text()).toBe("name");
        const $label = wrapper.find(".title-link");
        expect($label.text()).toBe("tool_section");
        await $sectionName.trigger("click");
        expect(wrapper.findAll(".name").length).toBe(1);
    });

    it("updates expanded state when the filter changes or the section is toggled", async () => {
        const wrapper = mountCategory(toolAndLabel(), { queryFilter: "test" });
        expect(sectionIsOpened(wrapper)).toBe(true);
        const $sectionName = wrapper.find(".name");
        await $sectionName.trigger("click");
        expect(sectionIsOpened(wrapper)).toBe(false);
        await wrapper.setProps({ queryFilter: "" });
        expect(sectionIsOpened(wrapper)).toBe(false);
        await wrapper.setProps({ queryFilter: "test" });
        expect(sectionIsOpened(wrapper)).toBe(true);
        await wrapper.setProps({ disableFilter: true });
        expect(sectionIsOpened(wrapper)).toBe(true);
        await wrapper.setProps({ queryFilter: "" });
        expect(sectionIsOpened(wrapper)).toBe(false);
        await $sectionName.trigger("click");
        expect(sectionIsOpened(wrapper)).toBe(true);
        await wrapper.setProps({ queryFilter: "test" });
        expect(sectionIsOpened(wrapper)).toBe(false);
    });
});

describe("ToolSection element ordering", () => {
    function makeTools() {
        return [
            getFakeTool({ id: "z_tool", name: "Zebra" }),
            getFakeTool({ id: "a_tool", name: "Apple" }),
            getFakeTool({ id: "m_tool", name: "Mango" }),
        ];
    }

    function getRenderedToolIds(wrapper: VueWrapper) {
        return wrapper.findAll("[data-tool-id]").map((w) => w.attributes("data-tool-id"));
    }

    it("renders tools alphabetically by default", async () => {
        const wrapper = mountCategory(createSection(makeTools()));
        await wrapper.find(".name").trigger("click");
        expect(getRenderedToolIds(wrapper)).toEqual(["a_tool", "m_tool", "z_tool"]);
    });

    it("preserves original order when sortItems is false", async () => {
        const wrapper = mountCategory(createSection(makeTools()), { sortItems: false });
        await wrapper.find(".name").trigger("click");
        expect(getRenderedToolIds(wrapper)).toEqual(["z_tool", "a_tool", "m_tool"]);
    });

    it("does not render ToolSectionLabels as tools", async () => {
        const elemsWithLabel: (ToolSectionLabel | Tool)[] = [
            getFakeTool({ id: "z_tool", name: "Zebra" }),
            { model_class: "ToolSectionLabel", id: "label_1", text: "A Label" },
            getFakeTool({ id: "a_tool", name: "Apple" }),
        ];
        const wrapper = mountCategory(createSection(elemsWithLabel));
        await wrapper.find(".name").trigger("click");
        expect(getRenderedToolIds(wrapper)).toEqual(["z_tool", "a_tool"]);
    });
});
