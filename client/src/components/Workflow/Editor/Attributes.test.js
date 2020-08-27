import Vue from "vue";
import { mount } from "@vue/test-utils";
import Attributes from "./Attributes";
import { __RewireAPI__ as rewire } from "./Attributes";

describe("Attributes", () => {
    beforeEach(() => {
        rewire.__Rewire__(
            "Services",
            class {
                async updateWorkflow() {
                    return {};
                }
            }
        );
    });
    it("test attributes", async () => {
        const wrapper = mount(Attributes, {
            propsData: {
                id: "workflow_id",
                name: "workflow_name",
                tags: ["workflow_tag_0", "workflow_tag_1"],
                parameters: ["workflow_parameter_0", "workflow_parameter_1"],
                versions: ["workflow_version_0"],
            },
        });
        const name = wrapper.find("#workflow-name");
        expect(name.element.value).to.equal("workflow_name");
        wrapper.setProps({ name: "new_workflow_name" });
        await Vue.nextTick();
        expect(name.element.value).to.equal("new_workflow_name");
        const parameters = wrapper.findAll(".list-group-item");
        expect(parameters.length).to.equal(2);
        expect(parameters.at(0).text()).to.equal("1: workflow_parameter_0");
        expect(parameters.at(1).text()).to.equal("2: workflow_parameter_1");
    });
});
