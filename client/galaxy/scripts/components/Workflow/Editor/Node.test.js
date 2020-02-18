import Vue from "vue";
import { mount } from "@vue/test-utils";
import Node from "./Node";

describe("Node", () => {
    it("test attributes", async () => {
        const wrapper = mount(Node, {
            propsData: {
                id: "node-id",
                title: "node-title",
                type: "tool"
            }
        });
        const icon = wrapper.find("i");
        expect(icon.classes()).to.contain("fa-wrench");
        const toolLinks = wrapper.findAll("a");
        expect(toolLinks.length).to.equal(2);
        wrapper.setProps({ type: "subworkflow" });
        await Vue.nextTick();
        expect(icon.classes()).to.contain("fa-sitemap");
        const subworkflowLinks = wrapper.findAll("a");
        expect(subworkflowLinks.length).to.equal(1);
        const workflowTitle = wrapper.find(".node-title");
        expect(workflowTitle.text()).to.equal("node-title");
    });
});
