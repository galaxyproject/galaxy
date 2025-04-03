import type { Invocation } from "@/components/Markdown/Editor/types";

import { getRequiredObject } from "./requirements";

interface ParsedAttributes {
    history_id?: string;
    history_target_id?: string;
    history_dataset_id?: string;
    history_dataset_collection_id?: string;
    input?: string;
    invocation: Invocation;
    implicit_collection_jobs_id?: string;
    job_id?: string;
    name: string;
    output?: string;
    step?: string;
    workflow_id?: string;
}

export function parseInput(invocation: Invocation, name: string | undefined) {
    if (name && invocation.inputs) {
        const inputs = Object.values(invocation.inputs);
        const input = inputs.find((i) => i.label && i.label === name);
        return input?.id;
    }
}

export function parseOutput(invocation: Invocation, name: string | undefined) {
    if (name && invocation.outputs) {
        const output = invocation.outputs[name];
        return output?.id;
    }
}

export function parseStep(invocation: Invocation, name: string | undefined) {
    if (name && invocation.steps) {
        const step = invocation.steps.find((s) => s.workflow_step_label === name);
        if (step) {
            return {
                job_id: step.job_id,
                implicit_collection_jobs_id: step.implicit_collection_jobs_id,
            };
        }
    }
}

export function parseInvocation(
    invocation: Invocation,
    workflowId: string,
    name: string,
    attributes: ParsedAttributes
): ParsedAttributes {
    const result: ParsedAttributes = { ...attributes, invocation };
    const inputId = parseInput(invocation, result.input);
    const outputId = parseOutput(invocation, result.output);
    const step = parseStep(invocation, result.step);
    const requiredObject = getRequiredObject(name);
    if (name === "history_link") {
        result.history_id = invocation.history_id;
    } else if (["workflow_display", "workflow_image", "workflow_license"].includes(name)) {
        result.workflow_id = workflowId;
    } else if (inputId && requiredObject) {
        if ("history_dataset_id" === requiredObject) {
            result.history_dataset_id = inputId;
        }
        if ("history_dataset_collection_id" === requiredObject) {
            result.history_dataset_collection_id = inputId;
        }
    } else if (outputId) {
        if ("history_dataset_id" === requiredObject) {
            result.history_dataset_id = outputId;
        }
        if ("history_dataset_collection_id" === requiredObject) {
            result.history_dataset_collection_id = outputId;
        }
    } else if (step) {
        result.job_id = step.job_id;
        result.implicit_collection_jobs_id = step.implicit_collection_jobs_id;
    }
    return result;
}
