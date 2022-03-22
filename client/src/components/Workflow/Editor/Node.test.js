import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import Node from "./Node";
import flushPromises from "flush-promises";

jest.mock("app");

const localVue = getLocalVue();

describe("Node", () => {
    it("test attributes", async () => {
        const wrapper = shallowMount(Node, {
            propsData: {
                id: "node-id",
                name: "node-name",
                type: "tool",
                step: {},
                getManager: () => {},
                getCanvasManager: () => {},
                datatypesMapper: {},
            },
            localVue,
        });
        await flushPromises();
        const icon = wrapper.findAll("i");
        expect(icon.at(2).classes()).toEqual(expect.arrayContaining(["fa-wrench"]));
        const toolLinks = wrapper.findAll("i");
        expect(toolLinks.length).toBe(3);
        await wrapper.setProps({ type: "subworkflow" });
        expect(icon.at(2).classes()).toEqual(expect.arrayContaining(["fa-sitemap"]));
        const subworkflowLinks = wrapper.findAll("i");
        expect(subworkflowLinks.length).toBe(2);
        const workflowTitle = wrapper.find(".node-title");
        expect(workflowTitle.text()).toBe("node-name");
    });
});
