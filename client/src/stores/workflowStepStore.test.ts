import { beforeEach, describe, expect, it } from "vitest";

import { createTestStep } from "@/components/Workflow/Editor/test_fixtures";
import {
    getCombinedStepInputs,
    type InputTerminalSource,
    type NewStep,
    type StepInputConnection,
    useWorkflowStepStore,
} from "@/stores/workflowStepStore";

import { setupTestPinia } from "./testUtils";
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

describe("Workflow Step Store", () => {
    beforeEach(() => {
        setupTestPinia();
    });

    it("adds a step to an empty workflow", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        expect(stepStore.steps).toStrictEqual({});
        stepStore.addStep(workflowStepZero);
        expect(stepStore.getStep(0)).toStrictEqual(workflowStepZero);
        expect(workflowStepZero.id).toBe(0);
    });
    it("removes an existing step by id", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const addedStep = stepStore.addStep(workflowStepZero);
        expect(addedStep.id).toBe(0);
        stepStore.removeStep(addedStep.id);
        expect(stepStore.getStep(0)).toBeUndefined();
    });
    it("creates a connection when a step declares an input connection", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const connectionStore = useConnectionStore("mock-workflow");
        stepStore.addStep(workflowStepZero);
        stepStore.addStep(workflowStepOne);
        expect(connectionStore.connections).toHaveLength(1);
    });
    it("removes a step's input connection when the step is removed", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const connectionStore = useConnectionStore("mock-workflow");
        stepStore.addStep(workflowStepZero);
        const stepOne = stepStore.addStep(workflowStepOne);
        expect(connectionStore.connections).toHaveLength(1);
        stepStore.removeStep(stepOne.id);
        expect(connectionStore.connections).toHaveLength(0);
    });
});

describe("getCombinedStepInputs", () => {
    beforeEach(() => {
        setupTestPinia();
    });

    const regularInput: InputTerminalSource = {
        name: "input_dataset",
        label: "Input Dataset",
        multiple: false,
        optional: false,
        extensions: ["txt"],
        input_type: "dataset",
    };

    const stepWithRegularInputs = createTestStep(0, {
        inputs: [regularInput],
        outputs: [],
    });

    const stepWithWhen = createTestStep(1, {
        inputs: [regularInput],
        outputs: [],
        when: "$(inputs.check_value)",
        inputConnections: {
            check_value: { output_name: "output", id: 0 },
        },
    });

    it("returns only regular inputs when step has no extra inputs", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const step = stepStore.addStep(stepWithRegularInputs);

        const combinedInputs = getCombinedStepInputs(step, stepStore);

        expect(combinedInputs).toHaveLength(1);
        expect(combinedInputs[0]?.name).toBe("input_dataset");
    });

    it("includes extra inputs when step has conditional parameters", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        stepStore.addStep(workflowStepZero);
        const step = stepStore.addStep(stepWithWhen);

        const combinedInputs = getCombinedStepInputs(step, stepStore);

        expect(combinedInputs.length).toBeGreaterThan(1);
        const inputNames = combinedInputs.map((input) => input.name);
        expect(inputNames).toContain("check_value");
        expect(inputNames).toContain("input_dataset");
    });

    it("places extra inputs before regular inputs", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        stepStore.addStep(workflowStepZero);
        const step = stepStore.addStep(stepWithWhen);

        const combinedInputs = getCombinedStepInputs(step, stepStore);

        expect(combinedInputs[0]?.name).toBe("check_value");
        expect(combinedInputs[1]?.name).toBe("input_dataset");
    });

    it("does not confuse a connection name with a longer referenced input", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        stepStore.addStep(workflowStepZero);
        const step = stepStore.addStep(
            createTestStep(1, {
                when: "$(inputs.check_value)",
                inputConnections: { check: { output_name: "output", id: 0 } },
            }),
        );

        expect(getCombinedStepInputs(step, stepStore)).toHaveLength(0);
    });

    it("returns no inputs for a step without regular or conditional inputs", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const step = stepStore.addStep(workflowStepZero);

        const combinedInputs = getCombinedStepInputs(step, stepStore);

        expect(combinedInputs).toHaveLength(0);
    });
});
