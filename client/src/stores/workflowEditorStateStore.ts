import Vue from "vue";
import { defineStore } from "pinia";
import type { BaseTerminal } from "./workflowConnectionStore";
import type { OutputTerminals } from "@/components/Workflow/Editor/modules/terminals";

export const state = {
    inputTerminals: {},
    outputTerminals: {},
    activeNode: null,
    scale: 1,
    nodes: {},
};

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
    nodes: { [index: number]: any };
}

export const useWorkflowStateStore = defineStore("workflowStateStore", {
    state: (): State => ({
        inputTerminals: {},
        outputTerminals: {},
        draggingPosition: null,
        draggingTerminal: null,
        activeNodeId: null,
        scale: 1,
        nodes: {},
    }),
    getters: {
        getInputTerminalPosition(state: State) {
            return (stepId: number, inputName: string) => state.inputTerminals[stepId]?.[inputName];
        },
        getOutputTerminalPosition(state: State) {
            return (stepId: number, outputName: string) => state.outputTerminals[stepId]?.[outputName];
        },
        getNode(state: State) {
            return (nodeId: number) => state.nodes[nodeId];
        },
        activeNode(state: State) {
            if (state.activeNodeId !== null) {
                return state.nodes[state.activeNodeId];
            }
            return null;
        },
    },
    actions: {
        setInputTerminalPosition(stepId: number, inputName: string, position: TerminalPosition) {
            if (!this.inputTerminals[stepId]) {
                Vue.set(this.inputTerminals, stepId, { [inputName]: position });
            } else {
                Vue.set(this.inputTerminals[stepId], inputName, position);
            }
        },
        setOutputTerminalPosition(stepId: number, outputName: string, position: TerminalPosition) {
            if (!this.outputTerminals[stepId]) {
                Vue.set(this.outputTerminals, stepId, { [outputName]: position });
            } else {
                Vue.set(this.outputTerminals[stepId], outputName, position);
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
        setNode(node: any) {
            Vue.set(this.nodes, node.id, node);
        },
        deleteNode(nodeId: number) {
            delete this.nodes[nodeId];
        },
    },
});
