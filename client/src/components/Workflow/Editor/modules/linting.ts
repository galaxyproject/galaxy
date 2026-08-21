import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { UntypedParameters } from "@/components/Workflow/Editor/modules/parameters";
import type { useWorkflowStores } from "@/composables/workflowStores";
import type { Step, Steps } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

import { isWorkflowInput } from "../../constants";
import type {
    DanglingGateState,
    DisconnectedInputState,
    DuplicateLabelState,
    ExtractInputAction,
    ExtractUntypedParameter,
    LintState,
    MetadataLintState,
    RemoveUnlabeledWorkflowOutputs,
    UnlabeledOuputState,
    UntypedParameterState,
} from "./lintingTypes";
import { terminalFactory } from "./terminals";
import { analyzeInputReferences } from "./whenExpression";
import { type InputPath, inputPathIsPrefix, resolveConnectionNameToInputPath } from "./workflowInputPath";

export const bestPracticeWarningAnnotation =
    "This workflow does not provide a short description. Providing a short description helps workflow executors understand the purpose and usage of the workflow.";
export const bestPracticeWarningAnnotationLength =
    "This workflow includes a very long short description. The best practice is to break up long descriptions of a workflow into readme and help text and keep the short description field a relatively brief description of the workflow appropriate for displaying in lists of workflows.";
export const bestPracticeWarningCreator =
    "This workflow does not specify creator(s). This is important metadata for workflows that will be published and/or shared to help workflow executors know how to cite the workflow authors.";
export const bestPracticeWarningLicense =
    "This workflow does not specify a license. This is important metadata for workflows that will be published and/or shared to help workflow executors understand how it may be used.";
export const bestPracticeWarningReadme =
    "This workflow does not provide a readme. Providing a detailed readme helps workflow executors understand the details, purpose, and limitations of the workflow.";

export function getDisconnectedInputs(
    steps: Steps = {},
    datatypesMapper: DatatypesMapperModel,
    stores: ReturnType<typeof useWorkflowStores>,
) {
    const inputs: DisconnectedInputState[] = [];
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
                    highlightType: "input",
                    name: inputSource.name,
                });
            }
        });
    });
    return inputs;
}

/**
 * Steps whose `when` expression reads a name nothing supplies.
 *
 * A gate on a disconnected tool parameter evaluates false forever, because the tool
 * state key survives as null; a gate on a disconnected probe raises during evaluation.
 * Neither is visible without this check -- `getDisconnectedInputs` walks `step.inputs`,
 * which never contains a synthesized gate port.
 */
export function getDanglingGates(steps: Steps = {}) {
    const dangling: DanglingGateState[] = [];
    Object.values(steps).forEach((step) => {
        if (!step.when) {
            return;
        }
        if (step.errors?.length) {
            // Nothing loaded, so nothing resolves. The missing tool is the report to make.
            return;
        }
        const references = analyzeInputReferences(step.when);
        if (references.hasDynamicInputsAccess) {
            return;
        }
        const reported = new Set<string>();
        references.staticPaths.forEach((path) => {
            const name = path.join("|");
            const referenceKey = JSON.stringify(path);
            if (reported.has(referenceKey) || gateReferenceIsSatisfied(step, path)) {
                return;
            }
            reported.add(referenceKey);
            dangling.push({
                stepId: step.id,
                stepLabel: step.label || step.content_id || step.name,
                warningLabel: name,
                inputName: name,
                autofix: false,
                highlightType: "input",
                name,
            });
        });
    });
    return dangling;
}

function gateReferenceIsSatisfied(step: Step, path: InputPath): boolean {
    if (connectionNamesIncludePath(step, Object.keys(step.input_connections ?? {}), path)) {
        return true;
    }
    if (
        connectionNamesIncludePath(
            step,
            (step.inputs ?? []).map((input) => input.name),
            path,
        )
    ) {
        // A connectable tool parameter with nothing connected is the dangling case.
        return false;
    }
    // Everything else the expression can legitimately read comes from the step's state.
    const root = path[0]!;
    return typeof root === "string" && Object.prototype.hasOwnProperty.call(step.tool_state ?? {}, root);
}

/** True when `path` names a candidate connection or one of its ancestors. */
function connectionNamesIncludePath(step: Step, candidates: string[], path: InputPath): boolean {
    return candidates.some((candidate) => {
        const candidatePath = resolveConnectionNameToInputPath(candidate, step.tool_state);
        return candidatePath ? inputPathIsPrefix(path, candidatePath) : false;
    });
}

/** Gate checks only make sense once something in the workflow is gated. */
export function hasGatedSteps(steps: Steps = {}): boolean {
    return Object.values(steps).some((step) => Boolean(step.when));
}

export function getMissingMetadata(steps: Steps) {
    const inputs: MetadataLintState[] = [];
    Object.values(steps).forEach((step) => {
        if (isWorkflowInput(step.type)) {
            const noAnnotation = !step.annotation;
            const noLabel = !step.label;
            let warningLabel = null;
            const data: MetadataLintState["data"] = {
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

// TODO: Maybe type of action should already be `MetadataLintState`?
export function dataAttributes(action: LintState) {
    const result: Record<string, "true" | "false"> = {};
    // Ensure we have an attributes lint state (`MetadataLintState` with data)
    if (isMetadataLintState(action)) {
        for (const [key, value] of Object.entries(action.data)) {
            result[`data-${key}`] = value;
        }
    }

    return result;
}

export function getDuplicateLabels(steps: Steps, stores: ReturnType<typeof useWorkflowStores>) {
    const duplicates: DuplicateLabelState[] = [];

    const { stepStore } = stores;
    const labels = stepStore.duplicateLabels;

    labels.forEach((label) => {
        Object.values(steps).forEach((step) => {
            const workflowOutputs = step.workflow_outputs || [];
            workflowOutputs.forEach((workflowOutput) => {
                if (workflowOutput.label === label) {
                    duplicates.push({
                        stepId: step.id,
                        stepLabel: step.label || step.content_id || step.name,
                        warningLabel: workflowOutput.output_name,
                        name: workflowOutput.output_name,
                        highlightType: "output",
                    });
                }
            });
        });
    });

    return duplicates;
}

export function getUnlabeledOutputs(steps: Steps) {
    const outputs: UnlabeledOuputState[] = [];
    Object.values(steps).forEach((step) => {
        if (isWorkflowInput(step.type)) {
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
                    highlightType: "output",
                    name: workflowOutput.output_name,
                });
            }
        }
    });
    return outputs;
}

export function getUntypedParameters(untypedParameters: UntypedParameters) {
    const items: UntypedParameterState[] = [];
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
    untypedParameters: UntypedParameterState[],
    disconnectedInputs: DisconnectedInputState[],
    unlabeledOutputs: UnlabeledOuputState[],
) {
    const actions = [];
    for (const untypedParameter of untypedParameters) {
        if (untypedParameter.autofix) {
            actions.push(fixUntypedParameter(untypedParameter));
        }
    }
    for (const disconnectedInput of disconnectedInputs) {
        if (disconnectedInput.autofix) {
            actions.push(fixDisconnectedInput(disconnectedInput));
        }
    }
    if (unlabeledOutputs.length > 0) {
        actions.push(fixUnlabeledOutputs());
    }
    return actions;
}

export function fixUntypedParameter(untypedParameter: UntypedParameterState): ExtractUntypedParameter {
    return {
        action_type: "extract_untyped_parameter",
        name: untypedParameter.name,
    };
}

export function fixDisconnectedInput(disconnectedInput: DisconnectedInputState): ExtractInputAction {
    return {
        action_type: "extract_input",
        input: {
            order_index: disconnectedInput.stepId,
            input_name: disconnectedInput.inputName,
        },
    };
}

export function fixUnlabeledOutputs(): RemoveUnlabeledWorkflowOutputs {
    return { action_type: "remove_unlabeled_workflow_outputs" };
}

export function isDisconnectedInputState(state: LintState): state is DisconnectedInputState {
    return isStateForInputOrOutput(state) && state.highlightType === "input";
}

function isMetadataLintState(state: LintState): state is MetadataLintState {
    return "data" in state;
}

/** Type guard for linting states that are for a workflow step input or output. */
export function isStateForInputOrOutput(
    state: LintState,
): state is DanglingGateState | DisconnectedInputState | DuplicateLabelState | UnlabeledOuputState {
    return "highlightType" in state;
}
