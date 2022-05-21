import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import ToolSection from "./ToolSection";

const localVue = getLocalVue();

describe("ToolSection", () => {
    test("test tool section", () => {
        const wrapper = mount(ToolSection, {
            propsData: {
                category: {
                    name: "name",
                },
            },
            localVue,
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.at(0).text()).toBe("name");
        nameElement.trigger("click");
        expect(wrapper.emitted().onClick).toBeDefined();
    });

    test("test tool section title", async () => {
        const wrapper = mount(ToolSection, {
            propsData: {
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
            localVue,
        });
        expect(wrapper.vm.opened).toBe(false);
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
        const wrapper = mount(ToolSection, {
            propsData: {
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
            localVue,
        });
        expect(wrapper.vm.opened).toBe(true);
        const $sectionName = wrapper.find(".name");
        await $sectionName.trigger("click");
        expect(wrapper.vm.opened).toBe(false);
        await wrapper.setProps({ queryFilter: "" });
        expect(wrapper.vm.opened).toBe(false);
        await wrapper.setProps({ queryFilter: "test" });
        expect(wrapper.vm.opened).toBe(true);
        await wrapper.setProps({ disableFilter: true });
        expect(wrapper.vm.opened).toBe(true);
        await wrapper.setProps({ queryFilter: "" });
        expect(wrapper.vm.opened).toBe(false);
        await $sectionName.trigger("click");
        expect(wrapper.vm.opened).toBe(true);
        await wrapper.setProps({ queryFilter: "test" });
        expect(wrapper.vm.opened).toBe(false);
    });
});
