export const state = {
    inputTerminals: {},
    outputTerminals: {},
    connections: {},
};

import Vue from "vue";
const getters = {
    getInputTerminal: (state) => (inputTerminalId) => {
        return state.inputTerminals[inputTerminalId];
    },
    getOutputTerminal: (state) => (outputTerminalId) => {
        return state.outputTerminals[outputTerminalId];
    },
};

const actions = {};

const mutations = {
    setInputTerminal: (state, { inputTerminalId, inputTerminal }) => {
        // TODO: Need to find a better inputTerminalId, terminal.id is just undefined
        console.log(inputTerminalId);
        Vue.set(state.inputTerminals, inputTerminalId, inputTerminal);
    },
    setOutputTerminal: (state, { outputTerminalId, outputTerminal }) => {
        console.log(outputTerminal);
        Vue.set(state.outputTerminals, outputTerminalId, outputTerminal);
    },
    setConnection: (state, { source, target, connection }) => {
        if (!state.connections[source]) {
            state.connections[source] = { target: connection };
        } else {
            state.connections[source][target] = connection;
        }
    },
};

export const workflowStateStore = {
    state,
    getters,
    actions,
    mutations,
};
