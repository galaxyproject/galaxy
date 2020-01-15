import { mount } from "@vue/test-utils";
import Tool from "./Tool";

describe("Tool", () => {
    it("test tool", () => {
        const wrapper = mount(Tool, {
            propsData: {
                tool: {}
            }
        });
        const labelsElement = wrapper.find(".labels");
        const operationElement = wrapper.find(".operation");
        const nameElement = wrapper.findAll(".name");
        expect(labelsElement.children).to.equal(undefined);
        expect(operationElement.classes()).to.include("operation");
        expect(nameElement.at(0).text()).to.equal("");
        operationElement.trigger("click");
        expect(wrapper.emitted().onOperation).to.not.be.undefined;
    });
    it("test tool operation", () => {
        const wrapper = mount(Tool, {
            propsData: {
                tool: {
                    name: "name"
                },
                operationIcon: "operationIconClass",
                operationTitle: "operationTitle"
            }
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
                    description: "description"
                },
                hideName: true
            }
        });
        const nameElement = wrapper.findAll(".name");
        expect(nameElement.length).to.equal(0);
        const descriptionElement = wrapper.find(".description");
        expect(descriptionElement.text()).to.equal("description");
    });
});
