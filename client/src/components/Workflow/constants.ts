import type { Step } from "@/stores/workflowStepStore";

const WorkflowInputs = ["data_input", "data_collection_input", "parameter_input"];

export function isWorkflowInput(stepType: Step["type"]): boolean {
    return WorkflowInputs.includes(stepType);
}

/** Unset data and collection inputs are omitted from a run request, so the server falls back to
 * the step's default (if any); an explicit `null` would run with no value instead. */
export function omitUnsetWorkflowInput(stepType: Step["type"], value: unknown): boolean {
    return (stepType === "data_input" || stepType === "data_collection_input") && value == null;
}
