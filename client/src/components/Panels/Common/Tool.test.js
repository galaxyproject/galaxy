import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import Tool from "./Tool";

describe("Tool", () => {
    test("test tool", () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(Tool, {
            props: {
                tool: {},
            },
            global: globalConfig.global,
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement[0].text()).toBe("");
        nameElement[0].trigger("click");
        expect(wrapper.emitted().onClick).toBeDefined();
        const labelsElement = wrapper.find(".labels");
        expect(labelsElement.children).toBeUndefined();
        const operationElement = wrapper.find(".operation");
        expect(operationElement.classes()).toEqual(expect.arrayContaining(["operation"]));
        operationElement.trigger("click");
        expect(wrapper.emitted().onOperation).toBeDefined();
    });
    test("test tool operation", () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(Tool, {
            props: {
                tool: {
                    name: "name",
                },
                operationIcon: "operationIconClass",
                operationTitle: "operationTitle",
            },
            global: globalConfig.global,
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement[0].text()).toBe("name");
        const operationElement = wrapper.find(".operation");
        expect(operationElement.classes()).toEqual(expect.arrayContaining(["operationIconClass"]));
        const title = operationElement.attributes("title");
        expect(title).toBe("operationTitle");
    });
    test("test tool hide name, test description", () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(Tool, {
            props: {
                tool: {
                    name: "name",
                    description: "description",
                },
                hideName: true,
            },
            global: globalConfig.global,
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.length).toBe(0);
        const descriptionElement = wrapper.find(".description");
        expect(descriptionElement.text()).toBe("description");
    });
});
