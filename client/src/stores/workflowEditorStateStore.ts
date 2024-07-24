import { type UseElementBoundingReturn } from "@vueuse/core";
import { computed, reactive, ref, set, type UnwrapRef } from "vue";

import { type OutputTerminals } from "@/components/Workflow/Editor/modules/terminals";
import reportDefault from "@/components/Workflow/Editor/reportDefault";

import { defineScopedStore } from "./scopedStore";

export interface InputTerminalPosition {
    endX: number;
    endY: number;
}

export interface OutputTerminalPosition {
    startX: number;
    startY: number;
}

export type TerminalPosition = InputTerminalPosition & OutputTerminalPosition;

export interface XYPosition {
    x: number;
    y: number;
}

type InputTerminalPositions = { [index: number]: { [index: string]: InputTerminalPosition } };
type OutputTerminalPositions = { [index: number]: { [index: string]: OutputTerminalPosition } };
type StepPosition = { [index: number]: UnwrapRef<UseElementBoundingReturn> };
type StepLoadingState = { [index: number]: { loading?: boolean; error?: string } };

export type WorkflowReport = {
    markdown?: string;
};

export type WorkflowStateStore = ReturnType<typeof useWorkflowStateStore>;

export const useWorkflowStateStore = defineScopedStore("workflowStateStore", () => {
    const inputTerminals = ref<InputTerminalPositions>({});
    const outputTerminals = ref<OutputTerminalPositions>({});
    const draggingPosition = ref<TerminalPosition | null>(null);
    const draggingTerminal = ref<OutputTerminals | null>(null);
    const activeNodeId = ref<number | null>(null);
    const scale = ref(1);
    const stepPosition = ref<StepPosition>({});
    const stepLoadingState = ref<StepLoadingState>({});
    const multiSelectedSteps = ref<Record<number, boolean>>({});
    const hasChanges = ref(false);
    const report = ref<WorkflowReport>({
        markdown: reportDefault,
    });

    function $reset() {
        inputTerminals.value = {};
        outputTerminals.value = {};
        draggingPosition.value = null;
        draggingTerminal.value = null;
        activeNodeId.value = null;
        scale.value = 1;
        stepPosition.value = {};
        stepLoadingState.value = {};
        multiSelectedSteps.value = {};
        report.value = {
            markdown: reportDefault,
        };
    }

    const getInputTerminalPosition = computed(
        () => (stepId: number, inputName: string) => inputTerminals.value[stepId]?.[inputName]
    );

    const getOutputTerminalPosition = computed(
        () => (stepId: number, outputName: string) => outputTerminals.value[stepId]?.[outputName]
    );

    const getStepLoadingState = computed(() => (stepId: number) => stepLoadingState.value[stepId]);

    const getStepMultiSelected = computed(() => (stepId: number) => Boolean(multiSelectedSteps.value[stepId]));

    const multiSelectedStepIds = computed(() =>
        Object.entries(multiSelectedSteps.value)
            .filter(([_id, selected]) => selected)
            .map(([id]) => parseInt(id))
    );

    function clearStepMultiSelection() {
        multiSelectedSteps.value = {};
    }

    function toggleStepMultiSelected(stepId: number) {
        setStepMultiSelected(stepId, !getStepMultiSelected.value(stepId));
    }

    function setStepMultiSelected(stepId: number, selected: boolean) {
        set(multiSelectedSteps.value, stepId, selected);
    }

    function setInputTerminalPosition(stepId: number, inputName: string, position: InputTerminalPosition) {
        if (!inputTerminals.value[stepId]) {
            set(inputTerminals.value, stepId, {});
        }

        set(inputTerminals.value[stepId]!, inputName, position);
    }

    function setOutputTerminalPosition(stepId: number, outputName: string, position: OutputTerminalPosition) {
        if (!outputTerminals.value[stepId]) {
            set(outputTerminals.value, stepId, reactive({}));
        }

        set(outputTerminals.value[stepId]!, outputName, position);
    }

    function deleteInputTerminalPosition(stepId: number, inputName: string) {
        delete inputTerminals.value[stepId]?.[inputName];
    }

    function deleteOutputTerminalPosition(stepId: number, outputName: string) {
        delete outputTerminals.value[stepId]?.[outputName];
    }

    function setStepPosition(stepId: number, position: UnwrapRef<UseElementBoundingReturn>) {
        set(stepPosition.value, stepId, position);
    }

    function deleteStepPosition(stepId: number) {
        delete stepPosition.value[stepId];
    }

    function deleteStepTerminals(stepId: number) {
        delete inputTerminals.value[stepId];
        delete outputTerminals.value[stepId];
    }

    function setLoadingState(stepId: number, loading: boolean, error: string | undefined) {
        set(stepLoadingState.value, stepId, { loading, error });
    }

    return {
        inputTerminals,
        outputTerminals,
        draggingPosition,
        draggingTerminal,
        activeNodeId,
        scale,
        report,
        hasChanges,
        stepPosition,
        stepLoadingState,
        $reset,
        getInputTerminalPosition,
        getOutputTerminalPosition,
        getStepLoadingState,
        multiSelectedSteps,
        multiSelectedStepIds,
        getStepMultiSelected,
        clearStepMultiSelection,
        toggleStepMultiSelected,
        setStepMultiSelected,
        setInputTerminalPosition,
        setOutputTerminalPosition,
        deleteInputTerminalPosition,
        deleteOutputTerminalPosition,
        deleteStepPosition,
        deleteStepTerminals,
        setStepPosition,
        setLoadingState,
    };
});
