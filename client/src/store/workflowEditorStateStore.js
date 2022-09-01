export const state = {
    inputTerminals: {},
    outputTerminals: {},
    connections: {},
    activeNode: null,
};

import Vue from "vue";
const getters = {
    getInputTerminal: (state) => (inputTerminalId) => {
        return state.inputTerminals[inputTerminalId];
    },
    getOutputTerminal: (state) => (outputTerminalId) => {
        return state.outputTerminals[outputTerminalId];
    },
    getActiveNode: (state) => () => {
        return state.activeNode;
    },
};

const actions = {};

const mutations = {
    setInputTerminal: (state, { inputTerminalId, inputTerminal }) => {
        Vue.set(state.inputTerminals, inputTerminalId, inputTerminal);
    },
    setOutputTerminal: (state, { outputTerminalId, outputTerminal }) => {
        Vue.set(state.outputTerminals, outputTerminalId, outputTerminal);
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
};

export const workflowStateStore = {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
