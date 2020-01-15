import Vue from "vue";
import { mount } from "@vue/test-utils";
import ToolSection from "./ToolSection";

describe("ToolSection", () => {
    it("test tool section", () => {
        const wrapper = mount(ToolSection, {
            propsData: {
                category: {
                    name: "name"
                }
            }
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.at(0).text()).to.equal("name");
        nameElement.trigger("click");
        expect(wrapper.emitted().onClick).to.not.be.undefined;
    });

    it("test tool section title", async () => {
        const wrapper = mount(ToolSection, {
            propsData: {
                category: {
                    title: "tool_section",
                    elems: [
                        {
                            name: "name"
                        },
                        {
                            text: "text"
                        }
                    ]
                }
            }
        });
        const $sectionName = wrapper.find(".name");
        expect($sectionName.text()).to.equal("tool_section");
        $sectionName.trigger("click");
        await Vue.nextTick();
        const $names = wrapper.findAll(".name");
        expect($names.at(1).text()).to.equal("name");
        const $label = wrapper.find(".label");
        expect($label.text()).to.equal("text");
        $sectionName.trigger("click");
        await Vue.nextTick();
        expect(wrapper.findAll(".name").length).to.equal(1);
    });
});
