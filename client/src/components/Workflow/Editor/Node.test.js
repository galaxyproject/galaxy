import Vue from "vue";
import { mount } from "@vue/test-utils";
import Node from "./Node";
import { setupTestGalaxy } from "qunit/test-app";
import { getNewAttachNode } from "jest/helpers";

describe("Node", () => {
    beforeEach(() => {
        // TODO: Move setupTestGalaxy to a single pretest setup, mock, or fix all the test requiring it.
        setupTestGalaxy();
    });

    setupTestGalaxy();
    it("test attributes", async () => {
        const wrapper = mount(Node, {
            propsData: {
                id: "node-id",
                name: "node-name",
                type: "tool",
                step: {},
                getManager: () => {},
                getCanvasManager: () => {},
            },
            attachTo: getNewAttachNode(),
        });
        const icon = wrapper.findAll("i");
        expect(icon.at(2).classes()).toEqual(expect.arrayContaining(["fa-wrench"]));
        const toolLinks = wrapper.findAll("i");
        expect(toolLinks.length).toBe(3);
        wrapper.setProps({ type: "subworkflow" });
        await Vue.nextTick();
        expect(icon.at(2).classes()).toEqual(expect.arrayContaining(["fa-sitemap"]));
        const subworkflowLinks = wrapper.findAll("i");
        expect(subworkflowLinks.length).toBe(2);
        const workflowTitle = wrapper.find(".node-title");
        expect(workflowTitle.text()).toBe("node-name");
    });
});
