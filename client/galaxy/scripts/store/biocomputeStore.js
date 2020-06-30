export const state = {
    biocomputeDetailsById: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    getBioComputeById: (state) => (invocationId) => {
        return state.invocationDetailsById[invocationId];
    },
};

const actions = {
    fetchInvocationForId: async ({ commit }, invocationId) => {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/${invocationId}`);
        commit("saveInvocationForId", { invocationId, invocationData: data });
    },
};

const mutations = {
    saveInvocationForId: (state, { invocationId, invocationData }) => {
        Vue.set(state.invocationDetailsById, invocationId, invocationData);
    },
};

export const invocationStore = {
    state,
    getters,
    actions,
    mutations,
};
