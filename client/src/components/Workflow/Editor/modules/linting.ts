import { type DatatypesMapperModel } from "@/components/Datatypes/model";
import { type UntypedParameters } from "@/components/Workflow/Editor/modules/parameters";
import { type useWorkflowStores } from "@/composables/workflowStores";
import { type Step, type Steps } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

import { terminalFactory } from "./terminals";

interface LintState {
    stepId: number;
    stepLabel: string;
    warningLabel: string;
    name?: string;
    inputName?: string;
    autofix?: boolean;
    data?: Record<string, string>;
}

export const bestPracticeWarningAnnotation =
    "This workflow is not annotated. Providing an annotation helps workflow executors understand the purpose and usage of the workflow.";
export const bestPracticeWarningCreator =
    "This workflow does not specify creator(s). This is important metadata for workflows that will be published and/or shared to help workflow executors know how to cite the workflow authors.";
export const bestPracticeWarningLicense =
    "This workflow does not specify a license. This is important metadata for workflows that will be published and/or shared to help workflow executors understand how it may be used.";

export function getDisconnectedInputs(
    steps: Steps = {},
    datatypesMapper: DatatypesMapperModel,
    stores: ReturnType<typeof useWorkflowStores>
) {
    const inputs: LintState[] = [];
    Object.values(steps).forEach((step) => {
        step.inputs.map((inputSource) => {
            const inputTerminal = terminalFactory(step.id, inputSource, datatypesMapper, stores);
            if (!inputTerminal.optional && inputTerminal.connections.length === 0) {
                const inputLabel = inputSource.label || inputSource.name;
                inputs.push({
                    stepId: step.id,
                    stepLabel: step.label || step.content_id || step.name,
                    warningLabel: inputLabel,
                    inputName: inputSource.name,
                    autofix: !inputTerminal.multiple,
                });
            }
        });
    });
    return inputs;
}

function isInput(stepType: Step["type"]) {
    return stepType == "data_input" || stepType == "data_collection_input" || stepType == "parameter_input";
}

export function getMissingMetadata(steps: Steps) {
    const inputs: LintState[] = [];
    Object.values(steps).forEach((step) => {
        if (isInput(step.type)) {
            const noAnnotation = !step.annotation;
            const noLabel = !step.label;
            let warningLabel = null;
            const data = {
                "missing-label": "false",
                "missing-annotation": "false",
            };
            if (noLabel && noAnnotation) {
                warningLabel = "Missing a label and annotation";
                data["missing-label"] = "true";
                data["missing-annotation"] = "true";
            } else if (noLabel) {
                warningLabel = "Missing a label";
                data["missing-label"] = "true";
            } else if (noAnnotation) {
                warningLabel = "Missing an annotation";
                data["missing-annotation"] = "true";
            }
            if (warningLabel) {
                inputs.push({
                    stepId: step.id,
                    stepLabel: step.label || step.content_id || step.name,
                    warningLabel: warningLabel,
                    data: data,
                });
            }
        }
    });
    return inputs;
}

export function dataAttributes(action: LintState): Record<string, string> {
    const result: Record<string, string> = {};
    for (const [key, value] of Object.entries(action.data || {})) {
        result[`data-${key}`] = value;
    }

    return result;
}

export function getUnlabeledOutputs(steps: Steps) {
    const outputs: LintState[] = [];
    Object.values(steps).forEach((step) => {
        if (isInput(step.type)) {
            // For now skip these... maybe should push this logic into linting though
            // since it is fine to have outputs on inputs.
            return;
        }

        const workflowOutputs = step.workflow_outputs || [];
        for (const workflowOutput of workflowOutputs) {
            if (!workflowOutput.label) {
                outputs.push({
                    stepId: step.id,
                    stepLabel: step.label || step.content_id || step.name,
                    warningLabel: workflowOutput.output_name,
                    autofix: true,
                });
            }
        }
    });
    return outputs;
}

export function getUntypedParameters(untypedParameters: UntypedParameters) {
    const items: LintState[] = [];
    if (untypedParameters) {
        untypedParameters.parameters.forEach((parameter) => {
            try {
                const parameterReference = parameter.references[0];
                assertDefined(parameterReference, `Parameter references for ${parameter.name} are empty.`);

                // TODO: Not sure this is right, but I think this may have been broken previously?
                const stepLabel =
                    "toolInput" in parameterReference ? parameterReference.toolInput.label : parameter.name;
                items.push({
                    stepId: parameterReference.stepId,
                    stepLabel: stepLabel,
                    warningLabel: parameter.name,
                    name: parameter.name,
                    autofix: parameter.canExtract(),
                });
            } catch (errorMessage) {
                console.error(errorMessage);
            }
        });
    }
    return items;
}

export function fixAllIssues(
    steps: Steps,
    parameters: UntypedParameters,
    datatypesMapper: DatatypesMapperModel,
    stores: ReturnType<typeof useWorkflowStores>
) {
    const actions = [];
    const untypedParameters = getUntypedParameters(parameters);
    for (const untypedParameter of untypedParameters) {
        if (untypedParameter.autofix) {
            actions.push(fixUntypedParameter(untypedParameter));
        }
    }
    const disconnectedInputs = getDisconnectedInputs(steps, datatypesMapper, stores);
    for (const disconnectedInput of disconnectedInputs) {
        if (disconnectedInput.autofix) {
            actions.push(fixDisconnectedInput(disconnectedInput));
        }
    }
    const unlabeledOutputs = getUnlabeledOutputs(steps);
    if (unlabeledOutputs.length > 0) {
        actions.push(fixUnlabeledOutputs());
    }
    return actions;
}

export function fixUntypedParameter(untypedParameter: LintState) {
    return {
        action_type: "extract_untyped_parameter",
        name: untypedParameter.name,
    };
}

export function fixDisconnectedInput(disconnectedInput: LintState) {
    return {
        action_type: "extract_input",
        input: {
            order_index: disconnectedInput.stepId,
            input_name: disconnectedInput.inputName,
        },
    };
}

export function fixUnlabeledOutputs() {
    return { action_type: "remove_unlabeled_workflow_outputs" };
}
