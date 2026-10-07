import { describe, expect, it } from "vitest";

import type { Step, Steps } from "@/stores/workflowStepStore";

import { getDanglingGates } from "./linting";

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
            highlightType: "step",
        });
    });

    it("accepts a null-check gate on a connected parameter", () => {
        const step = makeStep({
            when: "$(inputs.input1 !== null)",
            input_connections: CONNECTED_INPUT1,
        });
        expect(getDanglingGates(steps(step))).toEqual([]);
    });

    it("flags a null-check gate whose parameter lost its connection", () => {
        const step = makeStep({ when: "$(inputs.input1 !== null)" });
        const dangling = getDanglingGates(steps(step));
        expect(dangling).toHaveLength(1);
        expect(dangling[0]).toMatchObject({ inputName: "input1", name: "input1", highlightType: "input" });
    });

    it("names a disconnected repeat parameter by its connection name", () => {
        const step = makeStep({
            when: "$(inputs.queries[0].input2 !== null)",
            inputs: [{ name: "queries_0|input2", label: "Second input", multiple: false, extensions: ["txt"] }],
            tool_state: { queries: '[{"__index__": 0, "input2": {}}]' },
        } as unknown as Partial<Step>);
        expect(getDanglingGates(steps(step))[0]).toMatchObject({
            inputName: "queries_0|input2",
            highlightType: "input",
        });
    });

    it("names a missing nested reference as the expression wrote it", () => {
        const step = makeStep({ when: "$(inputs.queries[0].input2 !== null)" });
        expect(getDanglingGates(steps(step))[0]).toMatchObject({
            inputName: "queries[0].input2",
            highlightType: "step",
        });
    });

    it("flags a subworkflow step whose gate port is not connected", () => {
        const step = makeStep({
            type: "subworkflow",
            content_id: undefined,
            when: "$(inputs.when)",
            inputs: [],
            tool_state: {},
        } as unknown as Partial<Step>);
        expect(getDanglingGates(steps(step)).map((item) => item.inputName)).toEqual(["when"]);
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

    it("accepts a gate on an extra connection that is connected", () => {
        const step = makeStep({
            when: "$(inputs.extra === null)",
            input_connections: { extra: { id: 0, output_name: "output" } },
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
        const step = makeStep({ when: "$(inputs.extra !== null && inputs.extra !== undefined)" });
        expect(getDanglingGates(steps(step))).toHaveLength(1);
    });

    it("reports only the missing half of a mixed expression", () => {
        const step = makeStep({
            when: "$(inputs.input1 !== null && inputs.extra !== null)",
            input_connections: CONNECTED_INPUT1,
        });
        const dangling = getDanglingGates(steps(step));
        expect(dangling.map((item) => item.inputName)).toEqual(["extra"]);
    });
});
