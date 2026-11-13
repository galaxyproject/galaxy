import { describe, expect, it, vi } from "vitest";

import { mockToolStep } from "@/components/Workflow/Editor/Actions/mockData";
import type { WorkflowSearchStore } from "@/stores/workflowSearchStore";
import type { Step } from "@/stores/workflowStepStore";

import { convertOpenConnections } from "./convertOpenConnections";
import { getModule } from "./services";

vi.mock("@/components/Workflow/Editor/modules/services", () => ({
    getModule: vi.fn(async () => ({
        tool_state: {},
        inputs: [],
        outputs: [{ name: "output", extensions: ["input"], optional: false }],
        config_form: {},
    })),
}));

const searchStore = { findOutputPosition: () => ({ x: 0, y: 0 }) } as unknown as WorkflowSearchStore;

function toolStepWithOutputs(id: number, outputNames: string[]): Step {
    return {
        ...mockToolStep(id),
        outputs: outputNames.map((name) => ({ name, extensions: ["input"], type: "data", optional: false })),
    };
}

describe("convertOpenConnections", () => {
    it("rewrites open input connections on copies, leaving the editor's steps untouched", async () => {
        const allSteps: Record<number, Step> = {
            0: mockToolStep(0),
            1: { ...mockToolStep(1), input_connections: { input1: [{ id: 0, output_name: "out_file1" }] } },
        };
        const before = structuredClone(allSteps);

        const { stepArray, inputReconnectionMap } = await convertOpenConnections([1], allSteps, searchStore);

        expect(allSteps).toEqual(before);
        const copiedStep = stepArray.find((step) => step.id === 1);
        const inputStepId = inputReconnectionMap[0]?.stepId;
        expect(copiedStep?.input_connections.input1).toEqual([{ id: inputStepId, output_name: "output" }]);
    });

    it("creates one input per distinct outside output and reconnects each to its own source", async () => {
        const allSteps: Record<number, Step> = {
            0: toolStepWithOutputs(0, ["a", "b"]),
            1: {
                ...mockToolStep(1),
                input_connections: { in_a: [{ id: 0, output_name: "a" }], in_b: [{ id: 0, output_name: "b" }] },
            },
            2: { ...mockToolStep(2), input_connections: { input1: [{ id: 0, output_name: "a" }] } },
        };

        const { stepArray, inputReconnectionMap } = await convertOpenConnections([1, 2], allSteps, searchStore);

        const inputSteps = stepArray.filter((step) => step.type === "data_input");
        expect(inputSteps).toHaveLength(2);
        expect(inputReconnectionMap.map(({ connection }) => connection)).toEqual([
            { id: 0, output_name: "a" },
            { id: 0, output_name: "b" },
        ]);

        const [inputA, inputB] = inputReconnectionMap;
        expect(inputSteps.map((step) => step.id)).toEqual([inputA?.stepId, inputB?.stepId]);
        expect(inputSteps.map((step) => step.label)).toEqual([inputA?.label, inputB?.label]);

        const step1 = stepArray.find((step) => step.id === 1);
        const step2 = stepArray.find((step) => step.id === 2);
        expect(step1?.input_connections.in_a).toEqual([{ id: inputA?.stepId, output_name: "output" }]);
        expect(step1?.input_connections.in_b).toEqual([{ id: inputB?.stepId, output_name: "output" }]);
        expect(step2?.input_connections.input1).toEqual([{ id: inputA?.stepId, output_name: "output" }]);
    });

    it("reconnects outputs by workflow output label, labeling unlabeled ones", async () => {
        const allSteps: Record<number, Step> = {
            0: {
                ...toolStepWithOutputs(0, ["labeled", "unlabeled"]),
                workflow_outputs: [
                    { output_name: "labeled", label: "my_label" },
                    { output_name: "unlabeled", label: null },
                ],
            },
            1: {
                ...mockToolStep(1),
                input_connections: {
                    in_labeled: [{ id: 0, output_name: "labeled" }],
                    in_unlabeled: [{ id: 0, output_name: "unlabeled" }],
                },
            },
        };

        const { stepArray, outputReconnectionMap } = await convertOpenConnections([0], allSteps, searchStore);

        const [labeled, unlabeled] = outputReconnectionMap;
        expect(labeled?.connection.output_name).toBe("my_label");

        const generatedLabel = unlabeled?.connection.output_name;
        const copiedOutputs = stepArray.find((step) => step.id === 0)?.workflow_outputs;
        expect(copiedOutputs?.find((output) => output.output_name === "unlabeled")?.label).toBe(generatedLabel);
        expect(generatedLabel).not.toBe("unlabeled");
    });

    it("leaves outgoing connections alone when convertOutputs is false", async () => {
        const allSteps: Record<number, Step> = {
            0: mockToolStep(0),
            1: { ...mockToolStep(1), input_connections: { input1: [{ id: 0, output_name: "out_file1" }] } },
        };

        const { stepArray, outputReconnectionMap } = await convertOpenConnections([0], allSteps, searchStore, {
            convertOutputs: false,
        });

        expect(outputReconnectionMap).toEqual([]);
        expect(stepArray.find((step) => step.id === 0)?.workflow_outputs).toEqual(allSteps[0]?.workflow_outputs);
    });

    it("keeps the collection type of a collection feeding the selection", async () => {
        const collectionOutput = {
            name: "pairs",
            extensions: ["input"],
            optional: false,
            collection: true,
            collection_type: "list:paired",
            collection_type_source: null,
        };
        const allSteps: Record<number, Step> = {
            0: { ...mockToolStep(0), outputs: [collectionOutput] },
            1: { ...mockToolStep(1), input_connections: { input1: [{ id: 0, output_name: "pairs" }] } },
        };

        await convertOpenConnections([1], allSteps, searchStore);

        expect(vi.mocked(getModule)).toHaveBeenCalledWith(
            expect.objectContaining({
                type: "data_collection_input",
                tool_state: expect.objectContaining({ collection_type: "list:paired" }),
            }),
            expect.anything(),
            expect.anything(),
        );
    });
});
