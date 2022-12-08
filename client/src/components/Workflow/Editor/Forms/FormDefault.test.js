import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormDefault from "./FormDefault";
import { ActiveOutputs } from "components/Workflow/Editor/modules/outputs";

const localVue = getLocalVue();

describe("FormDefault", () => {
    let wrapper;
    const activeOutputs = new ActiveOutputs();
    const outputs = [
        { name: "output-name", label: "output-label" },
        { name: "other-name", label: "other-label" },
    ];

    beforeEach(() => {
        activeOutputs.initialize(outputs);
        wrapper = mount(FormDefault, {
            propsData: {
                datatypes: [],
                getManager: () => {
                    return {
                        nodes: [],
                    };
                },
                nodeId: "id",
                nodeContentId: "id",
                nodeLabel: "label",
                nodeName: "node-title",
                nodeType: "subworkflow",
                nodeOutputs: outputs,
                nodeActiveOutputs: activeOutputs,
                configForm: {
                    inputs: [],
                },
            },
            localVue,
        });
    });

    it("check initial value and value change", async () => {
        const title = wrapper.find(".portlet-title-text").text();
        expect(title).toBe("node-title");
        const inputCount = wrapper.findAll("input").length;
        expect(inputCount).toBe(3);
        const outputLabelCount = wrapper.findAll("#__label__output-name").length;
        expect(outputLabelCount).toBe(1);
        const otherLabelCount = wrapper.findAll("#__label__other-name").length;
        expect(otherLabelCount).toBe(1);
    });
});
