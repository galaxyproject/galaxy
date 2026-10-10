import { describe, expect, it } from "vitest";

import { getReplacements, WorkflowRunModel } from "./model";
import sampleRunData1 from "./testdata/run1.json";

describe("test basic parameter replacement", () => {
    it("should replace", async () => {
        const step_1 = {
            inputs: [
                { name: "input_1", value: "${wp_1}", wp_linked: true },
                { name: "input_2", value: "input_2", step_linked: [{ index: 0, step_type: "data" }] },
            ],
        };
        const stepData = [{ input: { values: ["input_new_data"] } }];
        const wpData = { wp_1: "input_new_wp" };
        const result = getReplacements(step_1.inputs, stepData, wpData);
        expect(result.input_1).toEqual("input_new_wp");
        expect(result.input_2.values[0]).toEqual("input_new_data");
    });
});

describe("WorkflowRunModel status", () => {
    it("expands tool steps with disconnected data inputs", async () => {
        const runModel = new WorkflowRunModel(sampleRunData1);
        expect(runModel.hasOpenToolSteps).toBe(true);
    });
    it("collapses tool steps with optional disconnected data inputs", async () => {
        const optionalDataSteps = {
            ...sampleRunData1,
            steps: [
                {
                    id: "cat",
                    inputs: [
                        {
                            label: "Concatenate Dataset",
                            model_class: "DataToolParameter",
                            multiple: false,
                            name: "input1",
                            optional: true,
                            options: {
                                hda: [],
                                hdca: [],
                            },
                            text_value: "Not available.",
                            type: "data",
                            value: {
                                __class__: "RuntimeValue",
                            },
                        },
                    ],
                    model_class: "Tool",
                    name: "Concatenate datasets (for test workflows)",
                    replacement_parameters: [],
                    step_index: 0,
                    step_label: "",
                    step_name: "Concatenate datasets (for test workflows)",
                    step_type: "tool",
                    step_version: "1.0.0",
                },
            ],
        };
        const runModel = new WorkflowRunModel(optionalDataSteps);
        expect(runModel.hasOpenToolSteps).toBe(false);
    });
});

describe("WorkflowRunModel inputs", () => {
    function dataInputStep(stepIndex, outputConnections) {
        return {
            inputs: [],
            output_connections: outputConnections,
            step_index: stepIndex,
            step_name: "Input dataset",
            step_type: "data_input",
        };
    }

    function toolStep(stepIndex, inputs) {
        return {
            inputs,
            step_index: stepIndex,
            step_name: "Concatenate datasets",
            step_type: "tool",
        };
    }

    it("lists every connection of a data input connected to several steps in its help", () => {
        const connectionToCat = { input_step_index: 2, input_name: "input1", output_name: "output" };
        const runModel = new WorkflowRunModel({
            steps: [
                dataInputStep(0, [connectionToCat]),
                dataInputStep(1, [connectionToCat]),
                toolStep(2, [{ name: "input1", type: "data", multiple: true, optional: false, help: "" }]),
            ],
        });

        const input = runModel.parms[2].input1;
        expect(input.type).toBe("hidden");
        expect(input.help).toBe("Connected to 'output' from Step 1, Connected to 'output' from Step 2");
        expect(input.step_linked).toEqual([
            { index: "0", step_type: "data_input" },
            { index: "1", step_type: "data_input" },
        ]);
    });

    it("previews filled tool parameters collapsed but leaves empty required ones open", () => {
        const runModel = new WorkflowRunModel({
            steps: [
                toolStep(0, [
                    { name: "label", type: "text", optional: false, value: "sample" },
                    { name: "threshold", type: "text", optional: false, value: "" },
                ]),
            ],
        });

        const { label, threshold } = runModel.parms[0];
        expect(label.collapsible_value).toBe("sample");
        expect(label.collapsible_preview).toBe(true);
        expect(threshold.collapsible_value).toBeUndefined();
        expect(threshold.collapsible_preview).toBeUndefined();
    });
});
