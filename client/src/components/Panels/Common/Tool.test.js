import { mount } from "@vue/test-utils";
import Tool from "./Tool";
import { getNewAttachNode } from "jest/helpers";

describe("Tool", () => {
    test("test tool", () => {
        const wrapper = mount(Tool, {
            propsData: {
                tool: {},
            },
            attachTo: getNewAttachNode(),
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.at(0).text()).toBe("");
        nameElement.trigger("click");
        expect(wrapper.emitted().onClick).toBeDefined();
        const labelsElement = wrapper.find(".labels");
        expect(labelsElement.children).toBeUndefined();
        const operationElement = wrapper.find(".operation");
        expect(operationElement.classes()).toEqual(expect.arrayContaining(["operation"]));
        operationElement.trigger("click");
        expect(wrapper.emitted().onOperation).toBeDefined();
    });
    test("test tool operation", () => {
        const wrapper = mount(Tool, {
            propsData: {
                tool: {
                    name: "name",
                },
                operationIcon: "operationIconClass",
                operationTitle: "operationTitle",
            },
            attachTo: getNewAttachNode(),
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.at(0).text()).toBe("name");
        const operationElement = wrapper.find(".operation");
        expect(operationElement.classes()).toEqual(expect.arrayContaining(["operationIconClass"]));
        const title = operationElement.attributes("title");
        expect(title).toBe("operationTitle");
    });
    test("test tool hide name, test description", () => {
        const wrapper = mount(Tool, {
            propsData: {
                tool: {
                    name: "name",
                    description: "description",
                },
                hideName: true,
            },
            attachTo: getNewAttachNode(),
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.length).toBe(0);
        const descriptionElement = wrapper.find(".description");
        expect(descriptionElement.text()).toBe("description");
    });
});
