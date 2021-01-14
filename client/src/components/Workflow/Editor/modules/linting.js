import _ from "underscore";
import _l from "utils/localization";

export function getDisconnectedInputs(nodes) {
    const inputs = [];
    Object.entries(nodes).forEach(([k, node]) => {
        Object.entries(node.inputTerminals).forEach(([inputName, inputTerminal]) => {
            if (inputTerminal.connectors && inputTerminal.connectors.length > 0) {
                return;
            }
            if (inputTerminal.optional) {
                return;
            }
            const input = {
                inputName: inputName,
                stepId: node.id,
                stepLabel: node.title, // label but falls back to tool title...
                stepIconClass: node.iconClass,
                inputLabel: inputTerminal.attributes.input.label,
                canExtract: !inputTerminal.multiple,
            };
            inputs.push(input);
        });
    });
    return inputs;
}

export function getInputsMissingMetadata(nodes) {
    const inputs = [];
    Object.entries(nodes).forEach(([k, node]) => {
        if (!node.isInput) {
            return;
        }
        const annotation = node.annotation;
        const label = node.label;
        const missingLabel = !label;
        const missingAnnotation = !annotation;

        if (missingLabel || missingAnnotation) {
            const input = {
                stepId: node.id,
                stepLabel: node.title,
                stepIconClass: node.iconClass,
                missingAnnotation: !annotation,
                missingLabel: !label,
            };
            inputs.push(input);
        }
    });
    return inputs;
}

export function getWorkflowOutputs(nodes) {
    const outputs = [];
    Object.entries(nodes).forEach(([k, node]) => {
        if (node.isInput) {
            // For now skip these... maybe should push this logic into linting though
            // since it is fine to have outputs on inputs.
            return;
        }
        const activeOutputs = node.activeOutputs;
        for (const outputDef of activeOutputs.getAll()) {
            const output = {
                outputName: outputDef.output_name,
                outputLabel: outputDef.label,
                stepId: node.id,
                stepLabel: node.title, // label but falls back to tool title...
                stepIconClass: node.iconClass,
            };
            outputs.push(output);
        }
    });
    return outputs;
}
