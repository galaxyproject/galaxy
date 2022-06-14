export const state = {
    workflowsByInstanceId: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    getWorkflowByInstanceId: (state) => (workflowId) => {
        return state.workflowsByInstanceId[workflowId];
    },
    getWorkflowNameByInstanceId: (state) => (workflowId) => {
        const details = state.workflowsByInstanceId[workflowId];
        if (details && details.name) {
            return details.name;
        } else {
            return "...";
        }
    },
    getStoredWorkflowIdByInstanceId: (state) => (workflowId) => {
        const storedWorkflow = state.workflowsByInstanceId[workflowId];
        return storedWorkflow?.id;
    },
};

const actions = {
    fetchWorkflowForInstanceId: async ({ commit }, workflowId) => {
        const params = { instance: "true" };
        const { data } = await axios.get(`${getAppRoot()}api/workflows/${workflowId}`, { params });
        commit("saveWorkflowForInstanceId", { workflowId, workflowData: data });
    },
};

const mutations = {
    saveWorkflowForInstanceId: (state, { workflowId, workflowData }) => {
        Vue.set(state.workflowsByInstanceId, workflowId, workflowData);
    },
};

export const workflowStore = {
    state,
    getters,
    actions,
    mutations,
};
