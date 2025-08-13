import { mount } from "@vue/test-utils";
import { useConfig } from "composables/config";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import ToolSection from "./ToolSection";

jest.mock("composables/config");
useConfig.mockReturnValue({
    config: {
        toolbox_auto_sort: true,
    },
    isConfigLoaded: true,
});


function sectionIsOpened(wrapper) {
    return wrapper.find("[data-description='opened tool panel section']").exists();
}

const globalConfig = getLocalVue();
const pinia = createPinia();

describe("ToolSection", () => {
    test("test tool section", () => {
        const wrapper = mount(ToolSection, {
            props: {
                category: {
                    name: "name",
                },
            },
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, pinia],
            },
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement[0].text()).toBe("name");
        nameElement[0].trigger("click");
        expect(wrapper.emitted().onClick).toBeDefined();
    });

    test("test tool section title", async () => {
        const wrapper = mount(ToolSection, {
            props: {
                category: {
                    title: "tool_section",
                    elems: [
                        {
                            name: "name",
                        },
                        {
                            text: "text",
                        },
                    ],
                },
            },
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, pinia],
            },
        });
        expect(sectionIsOpened(wrapper)).toBe(false);
        const $sectionName = wrapper.find(".name");
        expect($sectionName.text()).toBe("tool_section");
        await $sectionName.trigger("click");
        const $names = wrapper.findAll(".name");
        expect($names[1].text()).toBe("name");
        const $label = wrapper.find(".title-link");
        expect($label.text()).toBe("tool_section");
        await $sectionName.trigger("click");
        expect(wrapper.findAll(".name").length).toBe(1);
    });

    test("test tool slider state", async () => {
        const wrapper = mount(ToolSection, {
            props: {
                category: {
                    title: "tool_section",
                    elems: [
                        {
                            name: "name",
                        },
                        {
                            text: "text",
                        },
                    ],
                },
                queryFilter: "test",
            },
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, pinia],
            },
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
