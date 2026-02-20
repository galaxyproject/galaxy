import type { components } from "@/api";

export type ExtractInputAction = components["schemas"]["ExtractInputAction"];
export type ExtractUntypedParameter = components["schemas"]["ExtractUntypedParameter"];
export type RemoveUnlabeledWorkflowOutputs = components["schemas"]["RemoveUnlabeledWorkflowOutputs"];

/** Base linting state interface */
interface LintStateBase {
    stepId: number;
    stepLabel: string;
    warningLabel: string;
}

/** Lint state for disconnected input issues */
export interface DisconnectedInputState extends LintStateBase {
    autofix: boolean;
    highlightType: "input";
    inputName: string;
    name: string;
}

/** Lint state for duplicate label issues */
export interface DuplicateLabelState extends LintStateBase {
    highlightType: "output";
    name: string;
}

/** Lint state with metadata */
export interface MetadataLintState extends LintStateBase {
    data: {
        "missing-annotation": "true" | "false";
        "missing-label": "true" | "false";
    };
}

/** Lint state for unlabeled output issues */
export interface UnlabeledOuputState extends LintStateBase {
    autofix: true;
    highlightType: "output";
    name: string;
}

/** Lint state for untyped parameter issues */
export interface UntypedParameterState extends LintStateBase {
    autofix: boolean;
    name: string;
}

/** Union type for all linting states */
export type LintState =
    | DisconnectedInputState
    | DuplicateLabelState
    | MetadataLintState
    | UnlabeledOuputState
    | UntypedParameterState;
