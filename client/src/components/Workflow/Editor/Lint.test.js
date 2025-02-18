import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

import { getUntypedWorkflowParameters } from "./modules/parameters";

import Lint from "./Lint.vue";

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
        const pinia = createTestingPinia({ stubActions: false });
        setActivePinia(pinia);

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
            pinia,
            provide: { workflowId: "mock-workflow" },
        });

        stepStore = useWorkflowStepStore("mock-workflow");
        Object.values(steps).map((step) => stepStore.addStep(step));
    });

    it("test checked vs unchecked issues", async () => {
        const numLintChecksPassing = 4;
        const numLintChecksFailing = 5;
        const checked = wrapper.findAll("[data-icon='check']");
        expect(checked.length).toBe(numLintChecksPassing);

        const unchecked = wrapper.findAll("[data-icon='exclamation-triangle']");
        expect(unchecked.length).toBe(numLintChecksFailing);

        const links = wrapper.findAll("a");
        expect(links.length).toBe(numLintChecksFailing);
        expect(links.at(0).text()).toContain("Provide Creator Details.");
        expect(links.at(1).text()).toContain("Specify a License.");
        expect(links.at(2).text()).toContain("untyped_parameter");
        expect(links.at(3).text()).toContain("data input: Missing an annotation");
        expect(links.at(4).text()).toContain("step label: output");
    });

    it("should fire refactor event to extract untyped parameter and remove unlabeled workflows", async () => {
        await wrapper.find(".refactor-button").trigger("click");
        expect(wrapper.emitted().onRefactor.length).toBe(1);
        const actions = wrapper.emitted().onRefactor[0][0];
        expect(actions.length).toBe(2);
        expect(actions[0].action_type).toBe("extract_untyped_parameter");
        expect(actions[0].name).toBe("untyped_parameter");
        expect(actions[1].action_type).toBe("remove_unlabeled_workflow_outputs");
    });

    it("should include connect input action when input disconnected", async () => {
        stepStore.removeStep(0);
        await wrapper.find(".refactor-button").trigger("click");
        expect(wrapper.emitted().onRefactor.length).toBe(1);
        const actions = wrapper.emitted().onRefactor[0][0];
        expect(actions.length).toBe(3);
        expect(actions[0].action_type).toBe("extract_untyped_parameter");
        expect(actions[0].name).toBe("untyped_parameter");
        expect(actions[1].action_type).toBe("extract_input");
        expect(actions[2].action_type).toBe("remove_unlabeled_workflow_outputs");
    });
});
