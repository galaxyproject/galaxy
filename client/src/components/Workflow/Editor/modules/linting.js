export function getDisconnectedInputs(nodes) {
    const inputs = [];
    Object.values(nodes).forEach((node) => {
        Object.entries(node.inputTerminals).forEach(([inputName, inputTerminal]) => {
            if (!(inputTerminal.connectors && inputTerminal.connectors.length > 0) && !inputTerminal.optional) {
                const inputLabel = inputTerminal.attributes.input.label;
                inputs.push({
                    stepId: node.id,
                    stepLabel: node.title, // label but falls back to tool title...
                    warningLabel: inputLabel,
                    inputName: inputName,
                    autofix: !inputTerminal.multiple,
                });
            }
        });
    });
    return inputs;
}

export function getMissingMetadata(nodes) {
    const inputs = [];
    Object.values(nodes).forEach((node) => {
        if (node.isInput) {
            const noAnnotation = !node.annotation;
            const noLabel = !node.label;
            let warningLabel = null;
            if (noLabel && noAnnotation) {
                warningLabel = "Missing a label and annotation";
            } else if (noLabel) {
                warningLabel = "Missing a label";
            } else if (noAnnotation) {
                warningLabel = "Missing an annotation";
            }
            if (warningLabel) {
                inputs.push({
                    stepId: node.id,
                    stepLabel: node.title,
                    warningLabel: warningLabel,
                });
            }
        }
    });
    return inputs;
}

export function getUnlabeledOutputs(nodes) {
    const outputs = [];
    Object.values(nodes).forEach((node) => {
        if (node.isInput) {
            // For now skip these... maybe should push this logic into linting though
            // since it is fine to have outputs on inputs.
            return;
        }
        const activeOutputs = node.activeOutputs;
        for (const outputDef of activeOutputs.getAll()) {
            if (!outputDef.label) {
                outputs.push({
                    stepId: node.id,
                    stepLabel: node.title, // label but falls back to tool title...
                    warningLabel: outputDef.output_name,
                    autofix: true,
                });
            }
        }
    });
    return outputs;
}

export function getUntypedParameters(untypedParameters) {
    const items = [];
    if (untypedParameters) {
        untypedParameters.parameters.forEach((parameter) => {
            items.push({
                stepId: parameter.references[0].nodeId,
                stepLabel: parameter.references[0].toolInput.label,
                warningLabel: parameter.name,
                name: parameter.name,
                autofix: parameter.canExtract(),
            });
        });
    }
    return items;
}

export function fixAllIssues(nodes, parameters) {
    const actions = [];
    const untypedParameters = getUntypedParameters(parameters);
    for (const untypedParameter of untypedParameters) {
        if (untypedParameter.autofix) {
            actions.push(fixUntypedParameter(untypedParameter));
        }
    }
    const disconnectedInputs = getDisconnectedInputs(nodes);
    for (const disconnectedInput of disconnectedInputs) {
        if (disconnectedInput.autofix) {
            actions.push(fixDisconnectedInput(disconnectedInput));
        }
    }
    const unlabeledOutputs = getUnlabeledOutputs(nodes);
    if (unlabeledOutputs.length > 0) {
        actions.push(fixUnlabeledOutputs());
    }
    return actions;
}

export function fixUntypedParameter(untypedParameter) {
    return {
        action_type: "extract_untyped_parameter",
        name: untypedParameter.name,
    };
}

export function fixDisconnectedInput(disconnectedInput) {
    return {
        action_type: "extract_input",
        input: {
            order_index: parseInt(disconnectedInput.stepId),
            input_name: disconnectedInput.inputName,
        },
    };
}

export function fixUnlabeledOutputs() {
    return { action_type: "remove_unlabeled_workflow_outputs" };
}
