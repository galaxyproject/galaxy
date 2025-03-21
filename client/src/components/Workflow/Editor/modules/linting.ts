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
}

export const bestPracticeWarningAnnotation =
    "此工作流没有提供简短描述。提供简短描述有助于工作流执行者理解工作流的目的和用法。";
export const bestPracticeWarningAnnotationLength =
    "此工作流包含非常长的简短描述。最佳实践是将工作流的长描述分解为自述文件和帮助文本，保持简短描述字段相对简洁，适合在工作流列表中显示。";
export const bestPracticeWarningCreator =
    "此工作流未指定创建者。这对于将要发布和/或共享的工作流来说是重要的元数据，有助于工作流执行者了解如何引用工作流作者。";
export const bestPracticeWarningLicense =
    "此工作流未指定许可证。这对于将要发布和/或共享的工作流来说是重要的元数据，有助于工作流执行者了解如何使用它。";
export const bestPracticeWarningReadme =
    "此工作流没有提供自述文件。提供详细的自述文件有助于工作流执行者了解工作流的细节、目的和限制。";

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
            if (noLabel && noAnnotation) {
                warningLabel = "缺少标签和注释";
            } else if (noLabel) {
                warningLabel = "缺少标签";
            } else if (noAnnotation) {
                warningLabel = "缺少注释";
            }
            if (warningLabel) {
                inputs.push({
                    stepId: step.id,
                    stepLabel: step.label || step.content_id || step.name,
                    warningLabel: warningLabel,
                });
            }
        }
    });
    return inputs;
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
                assertDefined(parameterReference, `${parameter.name} 的参数引用为空.`);

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
