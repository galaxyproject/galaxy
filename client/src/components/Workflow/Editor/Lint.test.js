import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import Lint from "./Lint.vue";
import { getUntypedWorkflowParameters } from "./modules/parameters";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { PiniaVuePlugin } from "pinia";
import { createTestingPinia } from "@pinia/testing";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

const steps = {
    0: {
        id: 0,
        type: "data_input",
        label: "data input",
        content_id: null,
        name: "Input dataset",
        errors: null,
        inputs: [],
        outputs: [
            {
                name: "output",
                extensions: ["input"],
                optional: false,
            },
        ],
        annotation: "",
    },
    1: {
        id: 1,
        label: "step label",
        annotation: "",
        config_form: {
            inputs: [
                {
                    name: "input",
                    type: "text",
                    value: "${untyped_parameter}",
                },
            ],
        },
        inputs: [
            {
                label: "input_label",
                name: "data_input",
                multiple: false,
                extensions: ["txt"],
                optional: false,
                input_type: "dataset",
            },
        ],
        input_connections: {
            data_input: {
                output_name: "output",
                id: 0,
            },
        },
        outputs: [
            {
                name: "output",
                extensions: ["input"],
                optional: false,
            },
        ],
        workflow_outputs: [
            {
                output_name: "output",
            },
        ],
    },
    2: {
        id: 2,
        title: "",
        label: "",
        annotation: "",
        outpus: {},
        inputs: [],
    },
};

describe("Lint", () => {
    let wrapper;
    let stepStore;

    beforeEach(() => {
        wrapper = mount(Lint, {
            propsData: {
                untypedParameters: getUntypedWorkflowParameters(steps),
                steps: steps,
                annotation: "annotation",
                license: null,
                creator: null,
                datatypesMapper: testDatatypesMapper,
            },
            localVue,
            pinia: createTestingPinia({ stubActions: false }),
        });
        stepStore = useWorkflowStepStore();
        Object.values(steps).map((step) => stepStore.addStep(step));
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
        // 5. Missing an annotation
        // 6. Unlabeled output found
        expect(unchecked.length).toBe(5);
        const links = wrapper.findAll("a");
        expect(links.length).toBe(6);
        expect(links.at(0).text()).toContain("Try to automatically fix issues.");
        expect(links.at(1).text()).toContain("Provide Creator Details.");
        expect(links.at(2).text()).toContain("Specify a License.");
        expect(links.at(3).text()).toContain("untyped_parameter");
        expect(links.at(4).text()).toContain("data input: Missing an annotation");
        expect(links.at(5).text()).toContain("step label: output");
    });

    it("should fire refactor event to extract untyped parameter and remove unlabeled workflows", async () => {
        wrapper.vm.onRefactor();
        expect(wrapper.emitted().onRefactor.length).toBe(1);
        const actions = wrapper.emitted().onRefactor[0][0];
        expect(actions.length).toBe(2);
        expect(actions[0].action_type).toBe("extract_untyped_parameter");
        expect(actions[0].name).toBe("untyped_parameter");
        expect(actions[1].action_type).toBe("remove_unlabeled_workflow_outputs");
    });
    it("should include connect input action when input disconnected", async () => {
        stepStore.removeStep(0);
        wrapper.vm.onRefactor();
        expect(wrapper.emitted().onRefactor.length).toBe(1);
        const actions = wrapper.emitted().onRefactor[0][0];
        expect(actions.length).toBe(3);
        expect(actions[0].action_type).toBe("extract_untyped_parameter");
        expect(actions[0].name).toBe("untyped_parameter");
        expect(actions[1].action_type).toBe("extract_input");
        expect(actions[2].action_type).toBe("remove_unlabeled_workflow_outputs");
    });
});
