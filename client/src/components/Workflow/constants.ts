const WorkflowInputs = ["data_input", "data_collection_input", "parameter_input"];

export function isWorkflowInput(stepType: string): boolean {
    return WorkflowInputs.includes(stepType);
}
