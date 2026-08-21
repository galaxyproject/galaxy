import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createTestStep } from "@/components/Workflow/Editor/test_fixtures";
import {
    getCombinedStepInputs,
    type InputTerminalSource,
    type NewStep,
    normalizeConnectionOutputLinks,
    presenceGateIsSpellable,
    type Step,
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

describe("normalizeConnectionOutputLinks", () => {
    const link = { output_name: "output", id: 0 };

    it("normalizes absent, single, and multiple persisted connections", () => {
        expect(normalizeConnectionOutputLinks(undefined)).toEqual([]);
        expect(normalizeConnectionOutputLinks(link)).toEqual([link]);
        expect(normalizeConnectionOutputLinks([link, { output_name: "other", id: 1 }])).toEqual([
            link,
            { output_name: "other", id: 1 },
        ]);
    });
});

describe("Connection Store", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    afterEach(() => {
        vi.restoreAllMocks();
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

    afterEach(() => {
        vi.restoreAllMocks();
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

describe("synthesized gate ports", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    const optionalDataInput: NewStep = {
        ...workflowStepZero,
        id: 0,
        type: "data_input",
        outputs: [{ name: "output", extensions: ["input"], optional: true }],
    };

    const booleanParameterInput: NewStep = {
        ...workflowStepZero,
        id: 0,
        type: "parameter_input",
        outputs: [{ name: "output", optional: false, type: "boolean", parameter: true, multiple: false }],
    } as NewStep;

    function gatePort(source: NewStep, when: string, connectionName = "probe") {
        const stepStore = useWorkflowStepStore("mock-workflow");
        stepStore.addStep(source);
        const gated = addProbeGatedStep(stepStore, when, connectionName);
        return stepStore.getStepExtraInputs(gated.id);
    }

    function addProbeGatedStep(
        stepStore: ReturnType<typeof useWorkflowStepStore>,
        when = "$(inputs.probe !== null)",
        connectionName = "probe",
    ) {
        return stepStore.addStep(
            createTestStep(1, {
                when,
                inputConnections: { [connectionName]: { output_name: "output", id: 0 } },
            }),
        );
    }

    it("types a data probe as a dataset terminal carrying its source's optionality", () => {
        const ports = gatePort(optionalDataInput, "$(inputs.probe !== null)");
        expect(ports).toHaveLength(1);
        expect(ports[0]).toMatchObject({
            name: "probe",
            input_type: "dataset",
            optional: true,
            extensions: ["input"],
        });
    });

    it("keeps a boolean parameter probe a boolean parameter", () => {
        const ports = gatePort(booleanParameterInput, "$(inputs.probe)");
        expect(ports).toHaveLength(1);
        expect(ports[0]).toMatchObject({
            name: "probe",
            input_type: "parameter",
            type: "boolean",
            optional: false,
        });
    });

    it("keeps a multiple parameter probe multiple", () => {
        const multipleParameterInput: NewStep = {
            ...booleanParameterInput,
            outputs: [{ name: "output", optional: false, type: "text", parameter: true, multiple: true }],
        } as NewStep;
        const ports = gatePort(multipleParameterInput, "$(inputs.probe)");
        expect(ports[0]).toMatchObject({
            input_type: "parameter",
            type: "text",
            multiple: true,
        });
    });

    it("marks a probe fed by a gated step optional", () => {
        const gatedSource: NewStep = { ...workflowStepZero, id: 0, when: "$(inputs.when)" };
        const ports = gatePort(gatedSource, "$(inputs.probe !== null)");
        expect(ports[0]).toMatchObject({ optional: true });
    });

    it("keeps the conventional when port a required boolean whatever feeds it", () => {
        const textParameterInput: NewStep = {
            ...workflowStepZero,
            id: 0,
            type: "parameter_input",
            outputs: [{ name: "output", optional: true, type: "text", parameter: true, multiple: false }],
        } as NewStep;
        const ports = gatePort(textParameterInput, "$(inputs.when)", "when");
        expect(ports).toHaveLength(1);
        expect(ports[0]).toMatchObject({
            name: "when",
            input_type: "parameter",
            type: "boolean",
            optional: false,
        });
    });

    it("does not synthesize a port for a connection the expression only appears to name", () => {
        const ports = gatePort(optionalDataInput, "$(inputs.probe !== null)", "pro");
        expect(ports).toHaveLength(0);
    });

    it("retypes a probe when its source is added after the gated step", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const gated = addProbeGatedStep(stepStore);

        stepStore.addStep(optionalDataInput);

        expect(stepStore.getStepExtraInputs(gated.id)[0]).toMatchObject({
            name: "probe",
            input_type: "dataset",
            optional: true,
            extensions: ["input"],
        });
    });

    it("retypes a probe when its source output changes", () => {
        const stepStore = useWorkflowStepStore("mock-workflow");
        const source = stepStore.addStep(booleanParameterInput);
        const gated = addProbeGatedStep(stepStore);
        expect(stepStore.getStepExtraInputs(gated.id)[0]).toMatchObject({
            input_type: "parameter",
            type: "boolean",
            optional: false,
        });

        stepStore.updateStep({ ...source, outputs: optionalDataInput.outputs });

        expect(stepStore.getStepExtraInputs(gated.id)[0]).toMatchObject({
            input_type: "dataset",
            optional: true,
            extensions: ["input"],
        });
    });

    it("updates probe optionality when its source becomes gated", () => {
        const requiredDataInput: NewStep = {
            ...optionalDataInput,
            outputs: [{ name: "output", extensions: ["input"], optional: false }],
        };
        const stepStore = useWorkflowStepStore("mock-workflow");
        const source = stepStore.addStep(requiredDataInput);
        const gated = addProbeGatedStep(stepStore);
        expect(stepStore.getStepExtraInputs(gated.id)[0]).toMatchObject({ optional: false });

        stepStore.updateStep({ ...source, when: "$(inputs.when)" });

        expect(stepStore.getStepExtraInputs(gated.id)[0]).toMatchObject({ optional: true });
    });

    it("updates a data probe when its source changes output datatype", () => {
        const requiredDataInput: NewStep = {
            ...optionalDataInput,
            outputs: [{ name: "output", extensions: ["txt"], optional: false }],
        };
        const stepStore = useWorkflowStepStore("mock-workflow");
        const source = stepStore.addStep(requiredDataInput);
        const gated = addProbeGatedStep(stepStore);
        expect(stepStore.getStepExtraInputs(gated.id)[0]).toMatchObject({ extensions: ["txt"] });

        stepStore.updateStep({
            ...source,
            post_job_actions: {
                ChangeDatatypeActionoutput: {
                    action_type: "ChangeDatatypeAction",
                    output_name: "output",
                    action_arguments: { newtype: "tabular" },
                },
            },
        });

        expect(stepStore.getStepExtraInputs(gated.id)[0]).toMatchObject({ extensions: ["tabular"] });
    });
});

describe("presenceGateIsSpellable", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    const toolStep = createTestStep(0, {
        inputs: [],
        outputs: [],
    }) as NewStep;

    function step(toolState: Record<string, unknown>): Step {
        return { ...toolStep, tool_state: toolState } as Step;
    }

    it("spells a top-level input", () => {
        expect(presenceGateIsSpellable(step({ input1: '{"__class__": "ConnectedValue"}' }), "input1")).toBe(true);
    });

    it("spells an input nested in a conditional", () => {
        expect(presenceGateIsSpellable(step({ cond: { input1: {} } }), "cond|input1")).toBe(true);
    });

    it("spells an input nested in a json-encoded conditional", () => {
        expect(presenceGateIsSpellable(step({ cond: '{"input1": {}}' }), "cond|input1")).toBe(true);
    });

    it("spells an input nested in a repeat", () => {
        const repeatState = { queries: '[{"__index__": 0, "input2": {}}]' };
        expect(presenceGateIsSpellable(step(repeatState), "queries_0|input2")).toBe(true);
    });

    it("refuses a flattened name with two valid interpretations", () => {
        const ambiguousState = { queries_0: { input2: {} }, queries: [{ input2: {} }] };
        expect(presenceGateIsSpellable(step(ambiguousState), "queries_0|input2")).toBe(false);
    });

    it("spells a probe, which is not a tool parameter at all", () => {
        expect(presenceGateIsSpellable(step({}), "probe")).toBe(true);
    });

    it("refuses a nested name when tool state is unavailable", () => {
        expect(presenceGateIsSpellable(step({}), "cond|input1")).toBe(false);
    });
});
