import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import {
    getCombinedStepInputs,
    type InputTerminalSource,
    type NewStep,
    type StepInputConnection,
    useWorkflowStepStore,
} from "@/stores/workflowStepStore";

import { useConnectionStore } from "./workflowConnectionStore";

const stepInputConnection: StepInputConnection = {
    "1": {
        output_name: "output",
        id: 0,
    },
};

const workflowStepZero: NewStep = {
    id: 0,
    input_connections: {},
    inputs: [],
    name: "a step",
    outputs: [],
    post_job_actions: {},
    tool_state: {},
    type: "tool",
    workflow_outputs: [],
};

const workflowStepOne: NewStep = { ...workflowStepZero, input_connections: stepInputConnection };

describe("Connection Store", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("adds step", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        expect(stepStore.steps).toStrictEqual({});
        stepStore.addStep(workflowStepZero);
        expect(stepStore.getStep(0)).toStrictEqual(workflowStepZero);
        expect(workflowStepZero.id).toBe(0);
    });
    it("removes step", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const addedStep = stepStore.addStep(workflowStepZero);
        expect(addedStep.id).toBe(0);
        stepStore.removeStep(addedStep.id);
        expect(stepStore.getStep(0)).toBe(undefined);
    });
    it("creates connection if step has connection", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const connectionStore = useConnectionStore("mock-workflow");
        stepStore.addStep(workflowStepZero);
        stepStore.addStep(workflowStepOne);
        expect(connectionStore.connections.length).toBe(1);
    });
    it("removes connection if step has connection", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const connectionStore = useConnectionStore("mock-workflow");
        stepStore.addStep(workflowStepZero);
        const stepOne = stepStore.addStep(workflowStepOne);
        expect(connectionStore.connections.length).toBe(1);
        stepStore.removeStep(stepOne.id);
        expect(connectionStore.connections.length).toBe(0);
    });
});

describe("getCombinedStepInputs", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    const regularInput: InputTerminalSource = {
        name: "input_dataset",
        label: "Input Dataset",
        multiple: false,
        optional: false,
        extensions: ["txt"],
        input_type: "dataset",
    };

    const stepWithRegularInputs: NewStep = {
        id: 0,
        input_connections: {},
        inputs: [regularInput],
        name: "tool step",
        outputs: [],
        post_job_actions: {},
        tool_state: {},
        type: "tool",
        workflow_outputs: [],
    };

    const stepWithWhen: NewStep = {
        ...stepWithRegularInputs,
        id: 1,
        when: "${check_value}",
        input_connections: {
            check_value: { output_name: "output", id: 0 },
        },
    };

    it("returns only regular inputs when step has no extra inputs", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const step = stepStore.addStep(stepWithRegularInputs);

        const combinedInputs = getCombinedStepInputs(step, stepStore);

        expect(combinedInputs).toHaveLength(1);
        expect(combinedInputs[0]?.name).toBe("input_dataset");
    });

    it("includes extra inputs when step has conditional parameters", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        stepStore.addStep(workflowStepZero); // Add step 0 as output source
        const step = stepStore.addStep(stepWithWhen);

        const combinedInputs = getCombinedStepInputs(step, stepStore);

        expect(combinedInputs.length).toBeGreaterThan(1);
        const inputNames = combinedInputs.map((i) => i.name);
        expect(inputNames).toContain("check_value");
        expect(inputNames).toContain("input_dataset");
    });

    it("places extra inputs before regular inputs", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        stepStore.addStep(workflowStepZero);
        const step = stepStore.addStep(stepWithWhen);

        const combinedInputs = getCombinedStepInputs(step, stepStore);

        // Extra inputs should come first
        expect(combinedInputs[0]?.name).toBe("check_value");
        expect(combinedInputs[1]?.name).toBe("input_dataset");
    });

    it("handles step with no inputs gracefully", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const step = stepStore.addStep(workflowStepZero); // Step with empty inputs

        const combinedInputs = getCombinedStepInputs(step, stepStore);

        expect(combinedInputs).toHaveLength(0);
    });
});
