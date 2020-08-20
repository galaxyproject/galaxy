const WorkflowInputs = ["data_input", "data_collection_input", "parameter_input"];

function isWorkflowInput(stepType) {
    return WorkflowInputs.includes(stepType);
}

export { isWorkflowInput as default };
