export const state = {
    inputTerminals: {},
    outputTerminals: {},
    connections: {},
    activeNode: null,
    scale: 1,
    nodes: {},
};

import Vue from "vue";
const getters = {
    getInputTerminalPosition: (state) => (stepId, inputName) => {
        return state.inputTerminals[stepId]?.[inputName];
    },
    getOutputTerminalPosition: (state) => (stepId, outputName) => {
        return state.outputTerminals[stepId]?.[outputName];
    },
    getActiveNode: (state) => {
        return state.activeNode;
    },
    getScale: (state) => {
        return state.scale;
    },
    getNode: (state) => (nodeId) => {
        return state.nodes[nodeId];
    },
    getNodes: (state) => {
        return state.nodes;
    },
};

const actions = {};

const mutations = {
    setInputTerminalPosition: (state, { stepId, inputName, position }) => {
        if (!state.inputTerminals[stepId]) {
            Vue.set(state.inputTerminals, stepId, { [inputName]: position });
        } else {
            Vue.set(state.inputTerminals[stepId], inputName, position);
        }
    },
    setOutputTerminalPosition: (state, { stepId, outputName, position }) => {
        if (!state.outputTerminals[stepId]) {
            Vue.set(state.outputTerminals, stepId, { [outputName]: position });
        } else {
            Vue.set(state.outputTerminals[stepId], outputName, position);
        }
    },
    deleteInputTerminalPosition: (state, { stepId, inputName }) => {
        delete state.inputTerminals[stepId][inputName];
    },
    deleteOutputTerminalPosition: (state, { stepId, outputName }) => {
        delete state.outputTerminals[stepId][outputName];
    },
    setConnection: (state, { source, target, connection }) => {
        if (!state.connections[source]) {
            state.connections[source] = { target: connection };
        } else {
            state.connections[source][target] = connection;
        }
    },
    setActiveNode: (state, nodeId) => {
        state.activeNode = nodeId;
    },
    setScale: (state, scale) => {
        state.scale = scale;
    },
    setNode: (state, node) => {
        Vue.set(state.nodes, node.id, node);
    },
    deleteNode: (state, nodeId) => {
        delete state.nodes[nodeId];
    },
};

export const workflowStateStore = {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
