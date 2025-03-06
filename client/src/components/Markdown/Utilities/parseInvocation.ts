interface Invocation {
    history_id: string;
    inputs: Record<string, { label?: string; id?: string }>;
    outputs: Record<string, { id?: string }>;
    steps: { workflow_step_label?: string; job_id?: string; implicit_collection_jobs_id?: string }[];
    workflow_id: string;
}

interface ParsedAttributes {
    history_id?: string;
    history_target_id?: string;
    input?: string;
    invocation: Invocation;
    implicit_collection_jobs_id?: string;
    job_id?: string;
    name: string;
    output?: string;
    step?: string;
    workflow_id?: string;
}

export function parseInvocation(
    invocation: Invocation,
    workflowId: string,
    name: string,
    attributes: ParsedAttributes
): ParsedAttributes {
    const result: ParsedAttributes = { ...attributes };
    result.invocation = invocation;
    if (name === "history_link") {
        result.history_id = invocation.history_id;
    } else if (["workflow_display", "workflow_image", "workflow_license"].includes(name)) {
        result.workflow_id = workflowId;
    } else if (result.input && invocation.inputs) {
        const inputs = Object.values(invocation.inputs);
        const input = inputs.find((i) => i.label && i.label === result?.input);
        if (input) {
            result.history_target_id = input.id;
        }
    } else if (result.output && invocation.outputs) {
        const output = invocation.outputs[result.output];
        if (output) {
            result.history_target_id = output.id;
        }
    } else if (result.step && invocation.steps) {
        const step = invocation.steps.find((s) => s.workflow_step_label === result.step);
        if (step) {
            result.job_id = step.job_id;
            result.implicit_collection_jobs_id = step.implicit_collection_jobs_id;
        }
    }
    return result;
}
