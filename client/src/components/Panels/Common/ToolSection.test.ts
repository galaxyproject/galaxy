import { getFakeTool } from "@tests/test-data/tools";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, test, vi } from "vitest";
import { ref } from "vue";

import type { Tool, ToolSection as ToolSectionType, ToolSectionLabel } from "@/stores/toolStore";

import ToolSection from "./ToolSection.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: ref({ toolbox_auto_sort: true }),
        isConfigLoaded: ref(true),
    })),
}));

const localVue = getLocalVue();
const pinia = createPinia();

function sectionIsOpened(wrapper: VueWrapper) {
    return wrapper.find("[data-description='opened tool panel section']").exists();
}

describe("ToolSection", () => {
    test("test tool section", () => {
        const wrapper = mount(ToolSection, {
            props: {
                category: getFakeTool({ name: "name" }),
            },
            global: withPlugins(localVue, pinia),
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement[0]?.text()).toBe("name");
        nameElement[0]?.trigger("click");
        expect(wrapper.emitted("onClick")).toBeDefined();
    });

    test("test tool section title", async () => {
        const wrapper = mount(ToolSection, {
            props: {
                category: {
                    model_class: "ToolSection",
                    id: "tool_section",
                    name: "tool_section",
                    title: "tool_section",
                    // The store types elems without labels, but ToolSection.vue renders them.
                    elems: [
                        getFakeTool({ name: "name" }),
                        {
                            model_class: "ToolSectionLabel",
                            id: "label",
                            text: "text",
                        } as ToolSectionLabel,
                    ] as ToolSectionType["elems"],
                },
            },
            global: withPlugins(localVue, pinia),
        });
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

    test("test tool slider state", async () => {
        const wrapper = mount(ToolSection, {
            props: {
                category: {
                    model_class: "ToolSection",
                    id: "tool_section",
                    name: "tool_section",
                    title: "tool_section",
                    elems: [
                        getFakeTool({ name: "name" }),
                        {
                            model_class: "ToolSectionLabel",
                            id: "label",
                            text: "text",
                        } as ToolSectionLabel,
                    ] as ToolSectionType["elems"],
                },
                queryFilter: "test",
            },
            global: withPlugins(localVue, pinia),
        });
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
    function mountSection(
        elems: (ToolSectionType | ToolSectionLabel | Tool)[],
        propsOverrides: { sortItems?: boolean } = {},
    ) {
        return mount(ToolSection, {
            props: {
                category: {
                    model_class: "ToolSection",
                    id: "test_section",
                    name: "test_section",
                    title: "test_section",
                    // Labels aren't in the store's elems type; see above.
                    elems: elems as ToolSectionType["elems"],
                },
                ...propsOverrides,
            },
            global: withPlugins(localVue, pinia),
        });
    }

    const tools = [
        getFakeTool({ id: "z_tool", name: "Zebra" }),
        getFakeTool({ id: "a_tool", name: "Apple" }),
        getFakeTool({ id: "m_tool", name: "Mango" }),
    ];

    function getRenderedToolIds(wrapper: VueWrapper) {
        return wrapper.findAll("[data-tool-id]").map((w) => w.attributes("data-tool-id"));
    }

    test("renders tools alphabetically by default", async () => {
        const wrapper = mountSection(tools);
        await wrapper.find(".name").trigger("click");
        expect(getRenderedToolIds(wrapper)).toEqual(["a_tool", "m_tool", "z_tool"]);
    });

    test("preserves original order when sortItems is false", async () => {
        const wrapper = mountSection(tools, { sortItems: false });
        await wrapper.find(".name").trigger("click");
        expect(getRenderedToolIds(wrapper)).toEqual(["z_tool", "a_tool", "m_tool"]);
    });

    test("does not render ToolSectionLabels as tools", async () => {
        const elemsWithLabel: (ToolSectionLabel | Tool)[] = [
            getFakeTool({ id: "z_tool", name: "Zebra" }),
            { model_class: "ToolSectionLabel", id: "label_1", text: "A Label" },
            getFakeTool({ id: "a_tool", name: "Apple" }),
        ];
        const wrapper = mountSection(elemsWithLabel);
        await wrapper.find(".name").trigger("click");
        expect(getRenderedToolIds(wrapper)).toEqual(["z_tool", "a_tool"]);
    });
});
