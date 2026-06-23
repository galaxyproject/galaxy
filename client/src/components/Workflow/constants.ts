import type { Step } from "@/stores/workflowStepStore";

const WorkflowInputs = ["data_input", "data_collection_input", "parameter_input"];

export function isWorkflowInput(stepType: Step["type"]): boolean {
    return WorkflowInputs.includes(stepType);
}
