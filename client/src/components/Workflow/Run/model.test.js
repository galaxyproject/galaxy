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
