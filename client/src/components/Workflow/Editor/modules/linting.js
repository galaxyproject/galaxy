export function getDisconnectedInputs(nodes) {
    const inputs = [];
    Object.values(nodes).forEach((node) => {
        Object.entries(node.inputTerminals).forEach(([inputName, inputTerminal]) => {
            if (!inputTerminal.connectors || !inputTerminal.connectors.length > 0 || !inputTerminal.optional) {
                const inputLabel = inputTerminal.attributes.input.label;
                inputs.push({
                    stepId: node.id,
                    stepLabel: node.title, // label but falls back to tool title...
                    warningLabel: inputLabel,
                    inputName: inputName,
                    canExtract: !inputTerminal.multiple,
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
            } else {
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
            outputs.push({
                stepId: node.id,
                stepLabel: node.title, // label but falls back to tool title...
                warningLabel: outputDef.output_name,
            });
        }
    });
    return outputs;
}

export function getImplicitParameters(implicitParameters) {
    let items = [];
    if (implicitParameters) {
        implicitParameters.parameters.forEach((parameter) => {
            items.push({
                stepId: parameter.references[0].nodeId,
                stepLabel: parameter.references[0].toolInput.label,
                warningLabel: parameter.name,
                name: parameter.name,
            });
        });
    }
    return items;
}
