import Vue from "vue";
import { mount } from "@vue/test-utils";
import Node from "./Node";

describe("Node", () => {
    it("test attributes", async () => {
        const wrapper = mount(Node, {
            propsData: {
                id: "node-id",
                title: "node-title",
                type: "tool",
            },
        });
        const icon = wrapper.findAll("i");
        expect(icon.at(2).classes()).to.contain("fa-wrench");
        const toolLinks = wrapper.findAll("i");
        expect(toolLinks.length).to.equal(3);
        wrapper.setProps({ type: "subworkflow" });
        await Vue.nextTick();
        expect(icon.at(2).classes()).to.contain("fa-sitemap");
        const subworkflowLinks = wrapper.findAll("i");
        expect(subworkflowLinks.length).to.equal(2);
        const workflowTitle = wrapper.find(".node-title");
        expect(workflowTitle.text()).to.equal("node-title");
    });
});
