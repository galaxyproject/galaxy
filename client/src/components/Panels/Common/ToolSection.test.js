import Vue from "vue";
import { mount } from "@vue/test-utils";
import ToolSection from "./ToolSection";
import { getNewAttachNode } from "jest/helpers";

describe("ToolSection", () => {
    test("test tool section", () => {
        const wrapper = mount(ToolSection, {
            propsData: {
                category: {
                    name: "name",
                },
            },
            attachTo: getNewAttachNode(),
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
            attachTo: getNewAttachNode(),
        });
        expect(wrapper.vm.opened).toBe(false);
        const $sectionName = wrapper.find(".name");
        expect($sectionName.text()).toBe("tool_section");
        $sectionName.trigger("click");
        await Vue.nextTick();
        const $names = wrapper.findAll(".name");
        expect($names.at(1).text()).toBe("name");
        const $label = wrapper.find(".tool-panel-label");
        expect($label.text()).toBe("text");
        $sectionName.trigger("click");
        await Vue.nextTick();
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
            attachTo: getNewAttachNode(),
        });
        expect(wrapper.vm.opened).toBe(true);
        const $sectionName = wrapper.find(".name");
        $sectionName.trigger("click");
        await Vue.nextTick();
        expect(wrapper.vm.opened).toBe(false);
        wrapper.setProps({ queryFilter: "" });
        await Vue.nextTick();
        expect(wrapper.vm.opened).toBe(false);
        wrapper.setProps({ queryFilter: "test" });
        await Vue.nextTick();
        expect(wrapper.vm.opened).toBe(true);
        wrapper.setProps({ disableFilter: true });
        await Vue.nextTick();
        expect(wrapper.vm.opened).toBe(true);
        wrapper.setProps({ queryFilter: "" });
        await Vue.nextTick();
        expect(wrapper.vm.opened).toBe(false);
        $sectionName.trigger("click");
        await Vue.nextTick();
        expect(wrapper.vm.opened).toBe(true);
        wrapper.setProps({ queryFilter: "test" });
        await Vue.nextTick();
        expect(wrapper.vm.opened).toBe(false);
    });
});
