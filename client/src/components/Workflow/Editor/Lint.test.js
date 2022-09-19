import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import Lint from "./Lint";
import { getUntypedWorkflowParameters } from "./modules/parameters";

jest.mock("app");

const localVue = getLocalVue();

const nodes = {
    1: {
        id: "1",
        title: "node_title",
        label: "",
        annotation: "",
        config_form: {
            inputs: [
                {
                    name: "name",
                    type: "text",
                    value: "${untyped_parameter}",
                },
            ],
        },
        inputTerminals: {
            input: {
                attributes: {
                    input: {
                        label: "input_label",
                    },
                },
            },
        },
        outputTerminals: {},
        activeOutputs: {
            getAll() {
                return [
                    {
                        output_name: "output_1",
                    },
                ];
            },
        },
    },
    2: {
        id: "2",
        title: "",
        label: "",
        annotation: "",
        inputTerminals: {},
        activeOutputs: {
            getAll() {
                return [];
            },
        },
    },
};

describe("Lint", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(Lint, {
            propsData: {
                untypedParameters: getUntypedWorkflowParameters(nodes),
                getManager: () => {
                    return { nodes: nodes };
                },
                annotation: "annotation",
                license: null,
                creator: null,
            },
            localVue,
        });
    });

    it("test checked vs unchecked issues", async () => {
        const checked = wrapper.findAll("[data-icon='check']");
        // Expecting 5 checks:
        // 1. Workflow is annotated
        // 2. Non-optional inputs (if available) are formal inputs
        // 3. Inputs (if available) have labels and annotations
        expect(checked.length).toBe(2);
        const unchecked = wrapper.findAll("[data-icon='exclamation-triangle']");
        // Expecting 3 warnings:
        // 1. Workflow creator is not specified
        // 2. Workflow license is not specified
        // 3. Workflow has no labeled outputs
        // 4. Untyped parameter found
        // 5. Missing input connection
        // 6. Unlabeled output found
        expect(unchecked.length).toBe(5);
        const links = wrapper.findAll("a");
        expect(links.length).toBe(6);
        expect(links.at(0).text()).toContain("Try to automatically fix issues.");
        expect(links.at(1).text()).toContain("Provide Creator Details.");
        expect(links.at(2).text()).toContain("Specify a License.");
        expect(links.at(3).text()).toContain("untyped_parameter");
        expect(links.at(4).text()).toContain("node_title: input_label");
        expect(links.at(5).text()).toContain("output_1");
    });

    it("should fire refactor event to extract untyped paramater and remove unlabeld workflows", async () => {
        wrapper.vm.onRefactor();
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted().onRefactor.length).toBe(1);
        const actions = wrapper.emitted().onRefactor[0][0];
        expect(actions.length).toBe(3);
        expect(actions[0].action_type).toBe("extract_untyped_parameter");
        expect(actions[0].name).toBe("untyped_parameter");
        expect(actions[1].action_type).toBe("extract_input");
        expect(actions[2].action_type).toBe("remove_unlabeled_workflow_outputs");
    });
});
