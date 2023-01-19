import Vue from "vue";
import type { UnwrapRef } from "vue";
import { defineStore } from "pinia";
import type { OutputTerminals } from "@/components/Workflow/Editor/modules/terminals";
import type { UseElementBoundingReturn } from "@vueuse/core";

export interface TerminalPosition {
    startX: number;
    endX: number;
    startY: number;
    endY: number;
}

export interface XYPosition {
    x: number;
    y: number;
}

interface State {
    inputTerminals: { [index: number]: { [index: string]: TerminalPosition } };
    outputTerminals: { [index: number]: { [index: string]: TerminalPosition } };
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
            return (stepId: number, inputName: string) => state.inputTerminals[stepId]?.[inputName];
        },
        getOutputTerminalPosition(state: State) {
            return (stepId: number, outputName: string) => state.outputTerminals[stepId]?.[outputName];
        },
        getStepLoadingState(state: State) {
            return (stepId: number) => state.stepLoadingState[stepId];
        },
    },
    actions: {
        setInputTerminalPosition(stepId: number, inputName: string, position: TerminalPosition) {
            if (this.inputTerminals[stepId]) {
                Vue.set(this.inputTerminals[stepId]!, inputName, position);
            } else {
                Vue.set(this.inputTerminals, stepId, { [inputName]: position });
            }
        },
        setOutputTerminalPosition(stepId: number, outputName: string, position: TerminalPosition) {
            if (this.outputTerminals[stepId]) {
                Vue.set(this.outputTerminals[stepId]!, outputName, position);
            } else {
                Vue.set(this.outputTerminals, stepId, { [outputName]: position });
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
