export const state = {
    biocomputeDetailsById: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    getBioComputeById: (state) => (invocationId) => {
        return state.biocomputeDetailsById[invocationId];
    },
};

const actions = {
    fetchIBiocomputeForId: async ({ commit }, invocationId) => {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/${invocationId}/export_bco`);
        commit("saveBiocomputeForId", { invocationId, biocomputeData: data });
    },
};

const mutations = {
    saveBiocomputeForId: (state, { invocationId, biocomputeData }) => {
        Vue.set(state.biocomputeDetailsById, invocationId, biocomputeData);
    },
};

export const biocomputeStore = {
    state,
    getters,
    actions,
    mutations,
};
