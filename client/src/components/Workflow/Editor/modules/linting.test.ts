import { describe, expect, it } from "vitest";

import type { Step, Steps } from "@/stores/workflowStepStore";

import { getDanglingGates, hasGatedSteps } from "./linting";

function makeStep(overrides: Partial<Step> = {}): Step {
    return {
        id: 1,
        name: "Concatenate datasets",
        label: "gated",
        type: "tool",
        content_id: "cat1",
        inputs: [
            {
                name: "input1",
                label: "First input",
                multiple: false,
                extensions: ["txt"],
                optional: false,
                input_type: "dataset",
            },
        ],
        outputs: [{ name: "out_file1", extensions: ["txt"], optional: false }],
        input_connections: {},
        position: { left: 0, top: 0 },
        tool_state: { cond: { cond_test: "first" } },
        workflow_outputs: [],
        ...overrides,
    } as unknown as Step;
}

function steps(step: Step): Steps {
    return { 1: step } as unknown as Steps;
}

const CONNECTED_INPUT1 = { input1: { id: 0, output_name: "output" } };

describe("getDanglingGates", () => {
    it("ignores an ungated step", () => {
        expect(getDanglingGates(steps(makeStep()))).toEqual([]);
    });

    it("accepts a boolean gate whose port is connected", () => {
        const step = makeStep({
            when: "$(inputs.when)",
            input_connections: { when: { id: 0, output_name: "output" } },
        });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("flags a boolean gate with nothing connected to its port", () => {
        const step = makeStep({ when: "$(inputs.when)" });
        const dangling = getDanglingGates(steps(step));
        expect(dangling).toHaveLength(1);
        expect(dangling[0]).toMatchObject({
            stepId: 1,
            stepLabel: "gated",
            inputName: "when",
            autofix: false,
            highlightType: "input",
        });
    });

    it("accepts a presence gate on a connected parameter", () => {
        const step = makeStep({
            when: "$(inputs.input1 !== null)",
            input_connections: CONNECTED_INPUT1,
        });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("flags a presence gate whose parameter lost its connection", () => {
        const step = makeStep({ when: "$(inputs.input1 !== null)" });
        expect(getDanglingGates(steps(step))).toHaveLength(1);
    });

    it("accepts a gate reading a parameter that carries its value in step state", () => {
        const step = makeStep({
            when: '$(inputs.cond.cond_test === "first")',
            input_connections: CONNECTED_INPUT1,
        });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("accepts a gate reading a connection nested under a conditional", () => {
        const step = makeStep({
            when: "$(inputs.cond.input1 !== null)",
            input_connections: { "cond|input1": { id: 0, output_name: "output" } },
        });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("accepts a gate reading a connection nested under a repeat", () => {
        const step = makeStep({
            when: "$(inputs.queries[0].input2 !== null)",
            input_connections: { "queries_0|input2": { id: 0, output_name: "output" } },
            tool_state: { queries: '[{"__index__": 0, "input2": {}}]' },
        });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("does not confuse a literal pipe in an access with a nested connection path", () => {
        const step = makeStep({
            when: '$(inputs["cond|input1"] !== null)',
            input_connections: { "cond|input1": { id: 0, output_name: "output" } },
        });
        expect(getDanglingGates(steps(step))).toHaveLength(1);
    });

    it("accepts an inverse probe gate whose probe is connected", () => {
        const step = makeStep({
            when: "$(inputs.probe === null)",
            input_connections: { probe: { id: 0, output_name: "output" } },
        });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("says nothing about a step whose tool could not be loaded", () => {
        // An uninstalled tool has no inputs and no usable state, so every reference
        // would look unsatisfied. The missing tool is the problem to report, not the gate.
        const step = makeStep({ when: "$(inputs.input1 !== null)", inputs: [], tool_state: {}, errors: ["boom"] });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("says nothing about an expression it cannot resolve statically", () => {
        const step = makeStep({ when: "$(inputs[name] !== null)" });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("reports each missing name once", () => {
        const step = makeStep({ when: "$(inputs.probe !== null && inputs.probe !== undefined)" });
        expect(getDanglingGates(steps(step))).toHaveLength(1);
    });

    it("reports only the missing half of a mixed expression", () => {
        const step = makeStep({
            when: "$(inputs.input1 !== null && inputs.probe !== null)",
            input_connections: CONNECTED_INPUT1,
        });
        const dangling = getDanglingGates(steps(step));
        expect(dangling.map((item) => item.inputName)).toEqual(["probe"]);
    });
});

describe("hasGatedSteps", () => {
    it("is false without gates", () => {
        expect(hasGatedSteps(steps(makeStep()))).toBe(false);
    });

    it("is true with a gate", () => {
        expect(hasGatedSteps(steps(makeStep({ when: "$(inputs.when)" })))).toBe(true);
    });

    it("is false for an empty workflow", () => {
        expect(hasGatedSteps({})).toBe(false);
    });
});
