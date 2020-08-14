import { mount } from "@vue/test-utils";
import Tool from "./Tool";

describe("Tool", () => {
    it("test tool", () => {
        const wrapper = mount(Tool, {
            propsData: {
                tool: {},
            },
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.at(0).text()).to.equal("");
        nameElement.trigger("click");
        expect(wrapper.emitted().onClick).to.not.be.undefined;
        const labelsElement = wrapper.find(".labels");
        expect(labelsElement.children).to.equal(undefined);
        const operationElement = wrapper.find(".operation");
        expect(operationElement.classes()).to.include("operation");
        operationElement.trigger("click");
        expect(wrapper.emitted().onOperation).to.not.be.undefined;
    });
    it("test tool operation", () => {
        const wrapper = mount(Tool, {
            propsData: {
                tool: {
                    name: "name",
                },
                operationIcon: "operationIconClass",
                operationTitle: "operationTitle",
            },
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.at(0).text()).to.equal("name");
        const operationElement = wrapper.find(".operation");
        expect(operationElement.classes()).to.include("operationIconClass");
        const title = operationElement.attributes("title");
        expect(title).to.equal("operationTitle");
    });
    it("test tool hide name, test description", () => {
        const wrapper = mount(Tool, {
            propsData: {
                tool: {
                    name: "name",
                    description: "description",
                },
                hideName: true,
            },
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.length).to.equal(0);
        const descriptionElement = wrapper.find(".description");
        expect(descriptionElement.text()).to.equal("description");
    });
});
