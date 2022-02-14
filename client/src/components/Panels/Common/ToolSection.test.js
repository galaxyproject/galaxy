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
        $sectionName.trigger("click");
        await wrapper.vm.$nextTick();
        const $names = wrapper.findAll(".name");
        expect($names.at(1).text()).toBe("name");
        const $label = wrapper.find(".title-link");
        expect($label.text()).toBe("tool_section");
        $sectionName.trigger("click");
        await wrapper.vm.$nextTick();
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
        $sectionName.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.opened).toBe(false);
        wrapper.setProps({ queryFilter: "" });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.opened).toBe(false);
        wrapper.setProps({ queryFilter: "test" });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.opened).toBe(true);
        wrapper.setProps({ disableFilter: true });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.opened).toBe(true);
        wrapper.setProps({ queryFilter: "" });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.opened).toBe(false);
        $sectionName.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.opened).toBe(true);
        wrapper.setProps({ queryFilter: "test" });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.opened).toBe(false);
    });
});
