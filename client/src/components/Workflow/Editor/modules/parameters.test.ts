import { describe, expect, it } from "vitest";

import type { PostJobActions, Step, Steps } from "@/stores/workflowStepStore";

import { createTestStep } from "../test_fixtures";
import { getUntypedWorkflowParameters } from "./parameters";

function parameterInput(id: number, label: string): Step {
    return createTestStep(id, { type: "parameter_input", label });
}

function toolStep(id: number, options: { value?: string; postJobActions?: PostJobActions }): Step {
    const configForm = options.value
        ? { inputs: [{ name: "param", label: "Param", value: options.value }] }
        : undefined;
    return createTestStep(id, { configForm, postJobActions: options.postJobActions });
}

function rename(newname: string): PostJobActions {
    return {
        RenameDatasetActionout_file1: {
            action_type: "RenameDatasetAction",
            output_name: "out_file1",
            action_arguments: { newname },
        },
    };
}

function asSteps(...steps: Step[]): Steps {
    return Object.fromEntries(steps.map((step) => [step.id, step]));
}

function parameterNames(steps: Steps) {
    return getUntypedWorkflowParameters(steps).parameters.map((parameter) => parameter.name);
}

describe("getUntypedWorkflowParameters", () => {
    it("flags a rename parameter with no matching parameter input", () => {
        const steps = asSteps(toolStep(0, { postJobActions: rename("${sample} reads") }));
        expect(parameterNames(steps)).toEqual(["sample"]);
    });

    it("flags tool state parameters even when a parameter input has that label", () => {
        const steps = asSteps(parameterInput(0, "sample"), toolStep(1, { value: "${sample}" }));
        expect(parameterNames(steps)).toEqual(["sample"]);
    });
});
