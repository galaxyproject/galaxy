import Vue, { shallowRef, type ShallowRef } from "vue";
import type { UnwrapRef } from "vue";
import { defineStore } from "pinia";
import type { OutputTerminals } from "@/components/Workflow/Editor/modules/terminals";
import type { UseElementBoundingReturn } from "@vueuse/core";

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

interface State {
    inputTerminals: { [index: number]: { [index: string]: ShallowRef<InputTerminalPosition> } };
    outputTerminals: { [index: number]: { [index: string]: ShallowRef<OutputTerminalPosition> } };
    draggingPosition: TerminalPosition | null;
    draggingTerminal: OutputTerminals | null;
    activeNodeId: number | null;
    scale: number;
    stepPosition: { [index: number]: UnwrapRef<UseElementBoundingReturn> };
    stepLoadingState: { [index: number]: { loading?: boolean; error?: string } };
}

export const useWorkflowStateStore = defineStore("workflowStateStore", {
    state: (): State => ({
        inputTerminals: {},
        outputTerminals: {},
        draggingPosition: null,
        draggingTerminal: null,
        activeNodeId: null,
        scale: 1,
        stepPosition: {},
        stepLoadingState: {},
    }),
    getters: {
        getInputTerminalPosition(state: State) {
            return (stepId: number, inputName: string) => {
                return state.inputTerminals[stepId]?.[inputName] as ShallowRef<InputTerminalPosition> | undefined;
            };
        },
        getOutputTerminalPosition(state: State) {
            return (stepId: number, outputName: string) => {
                return state.outputTerminals[stepId]?.[outputName] as ShallowRef<OutputTerminalPosition> | undefined;
            };
        },
        getStepLoadingState(state: State) {
            return (stepId: number) => state.stepLoadingState[stepId];
        },
    },
    actions: {
        setInputTerminalPosition(stepId: number, inputName: string, position: InputTerminalPosition) {
            if (!this.inputTerminals[stepId]) {
                this.inputTerminals[stepId] = {};
            }

            if (!this.inputTerminals[stepId][inputName]) {
                this.inputTerminals[stepId][inputName] = shallowRef(position);
            } else {
                this.inputTerminals[stepId][inputName].value = position;
            }
        },
        setOutputTerminalPosition(stepId: number, outputName: string, position: OutputTerminalPosition) {
            if (!this.outputTerminals[stepId]) {
                this.outputTerminals[stepId] = {};
            }

            if (!this.outputTerminals[stepId][outputName]) {
                this.outputTerminals[stepId][outputName] = shallowRef(position);
            } else {
                this.outputTerminals[stepId][outputName].value = position;
            }
        },
        deleteInputTerminalPosition(stepId: number, inputName: string) {
            delete this.inputTerminals[stepId]?.[inputName];
        },
        deleteOutputTerminalPosition(stepId: number, outputName: string) {
            delete this.outputTerminals[stepId]?.[outputName];
        },
        setActiveNode(nodeId: number | null) {
            this.activeNodeId = nodeId;
        },
        setScale(scale: number) {
            this.scale = scale;
        },
        setStepPosition(stepId: number, position: UnwrapRef<UseElementBoundingReturn>) {
            Vue.set(this.stepPosition, stepId, position);
        },
        deleteStepPosition(stepId: number) {
            delete this.stepPosition[stepId];
        },
        setLoadingState(stepId: number, loading: boolean, error: string | undefined) {
            Vue.set(this.stepLoadingState, stepId, { loading, error });
        },
    },
});
