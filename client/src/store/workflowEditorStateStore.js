export const state = {
    inputTerminals: {},
    outputTerminals: {},
    connections: {},
    activeNode: null,
};

import Vue from "vue";
const getters = {
    getInputTerminalPosition: (state) => (stepId, inputName) => {
        console.log("getting input for", stepId, inputName);
        return state.inputTerminals[stepId]?.[inputName];
    },
    getOutputTerminalPosition: (state) => (stepId, outputName) => {
        return state.outputTerminals[stepId]?.[outputName];
    },
    getActiveNode: (state) => () => {
        return state.activeNode;
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
