import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
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

function sectionIsOpened(wrapper: Wrapper<Vue>) {
    return wrapper.find("[data-description='opened tool panel section']").exists();
}

describe("ToolSection", () => {
    test("test tool section", () => {
        const wrapper = mount(ToolSection as object, {
            propsData: {
                category: {
                    name: "name",
                },
            },
            localVue,
            pinia,
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.at(0).text()).toBe("name");
        nameElement.trigger("click");
        expect(wrapper.emitted().onClick).toBeDefined();
    });

    test("test tool section title", async () => {
        const wrapper = mount(ToolSection as object, {
            propsData: {
                category: {
                    title: "tool_section",
                    elems: [
                        {
                            name: "name",
                        },
                        {
                            model_class: "ToolSectionLabel",
                            id: "label",
                            text: "text",
                        },
                    ],
                },
            },
            localVue,
            pinia,
        });
        expect(sectionIsOpened(wrapper)).toBe(false);
        const $sectionName = wrapper.find(".name");
        expect($sectionName.text()).toBe("tool_section");
        await $sectionName.trigger("click");
        const $names = wrapper.findAll(".name");
        expect($names.at(1).text()).toBe("name");
        const $label = wrapper.find(".title-link");
        expect($label.text()).toBe("tool_section");
        await $sectionName.trigger("click");
        expect(wrapper.findAll(".name").length).toBe(1);
    });

    test("test tool slider state", async () => {
        const wrapper = mount(ToolSection as object, {
            propsData: {
                category: {
                    title: "tool_section",
                    elems: [
                        {
                            name: "name",
                        },
                        {
                            model_class: "ToolSectionLabel",
                            id: "label",
                            text: "text",
                        },
                    ],
                },
                queryFilter: "test",
            },
            localVue,
            pinia,
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
        return mount(ToolSection as object, {
            propsData: {
                category: {
                    title: "test_section",
                    elems,
                },
                ...propsOverrides,
            },
            localVue,
            pinia,
        });
    }

    const tools = [
        { id: "z_tool", name: "Zebra" },
        { id: "a_tool", name: "Apple" },
        { id: "m_tool", name: "Mango" },
    ] as Tool[];

    function getRenderedToolIds(wrapper: Wrapper<Vue>) {
        return wrapper.findAll("[data-tool-id]").wrappers.map((w) => w.attributes("data-tool-id"));
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
        const elemsWithLabel = [
            { id: "z_tool", name: "Zebra" },
            { model_class: "ToolSectionLabel", id: "label_1", text: "A Label" },
            { id: "a_tool", name: "Apple" },
        ] as (ToolSectionLabel | Tool)[];
        const wrapper = mountSection(elemsWithLabel);
        await wrapper.find(".name").trigger("click");
        expect(getRenderedToolIds(wrapper)).toEqual(["z_tool", "a_tool"]);
    });
});
