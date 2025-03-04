interface Invocation {
    inputs?: Record<string, { label?: string; id?: string }>;
    outputs?: Record<string, { id?: string }>;
    steps?: { workflow_step_label?: string; job_id?: string; implicit_collection_jobs_id?: string }[];
}

interface ParsedAttributes {
    invocation: Invocation;
    history_target_id?: string;
    implicit_collection_jobs_id?: string;
    input?: string;
    job_id?: string;
    output?: string;
    step?: string;
}

export function parseInvocation(invocation: Invocation, attributes: ParsedAttributes): ParsedAttributes {
    const result: ParsedAttributes = { ...attributes };
    result.invocation = invocation;
    if (result.input && invocation.inputs) {
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
