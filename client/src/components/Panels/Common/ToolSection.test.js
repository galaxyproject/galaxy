import { mount } from "@vue/test-utils";
import ToolSection from "./ToolSection";

describe("ToolSection", () => {
    test("test tool section", () => {
        const wrapper = mount(ToolSection, {
            propsData: {
                category: {
                    name: "name",
                },
            },
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
        });
        expect(wrapper.vm.opened).toBe(false);
        const $sectionName = wrapper.find(".name");
        expect($sectionName.text()).toBe("tool_section");
        $sectionName.trigger("click");
        await wrapper.vm.$nextTick();
        const $names = wrapper.findAll(".name");
        expect($names.at(1).text()).toBe("name");
        const $label = wrapper.find(".tool-panel-label");
        expect($label.text()).toBe("text");
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
