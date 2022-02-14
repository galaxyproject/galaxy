export const state = {
    invocationDetailsById: {},
    invocationJobsSummaryById: {},
    invocationStepById: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    getInvocationById: (state) => (invocationId) => {
        return state.invocationDetailsById[invocationId];
    },
    getInvocationJobsSummaryById: (state) => (invocationId) => {
        return state.invocationJobsSummaryById[invocationId];
    },
    getInvocationStepById: (state) => (invocationStepId) => {
        return state.invocationStepById[invocationStepId];
    },
};

const actions = {
    fetchInvocationForId: async ({ commit }, invocationId) => {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/${invocationId}`);
        commit("saveInvocationForId", { invocationId, invocationData: data });
    },
    fetchInvocationJobsSummaryForId: async ({ commit }, invocationId) => {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/${invocationId}/jobs_summary`);
        commit("saveInvocationJobsSummaryForId", { invocationId, jobsSummary: data });
    },
    fetchInvocationStepById: async ({ commit }, invocationStepId) => {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/any/steps/${invocationStepId}`);
        commit("saveInvocationStepById", { invocationStepId, invocationStepData: data });
    },
};

const mutations = {
    saveInvocationForId: (state, { invocationId, invocationData }) => {
        Vue.set(state.invocationDetailsById, invocationId, invocationData);
    },
    saveInvocationJobsSummaryForId: (state, { invocationId, jobsSummary }) => {
        Vue.set(state.invocationJobsSummaryById, invocationId, jobsSummary);
    },
    saveInvocationStepById: (state, { invocationStepId, invocationStepData }) => {
        Vue.set(state.invocationStepById, invocationStepId, invocationStepData);
    },
};

export const invocationStore = {
    state,
    getters,
    actions,
    mutations,
};
