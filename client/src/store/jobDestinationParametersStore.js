import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";

export const state = {
    jobDestinationParametersByJobId: {},
};

const getters = {
    jobDestinationParams: (state) => (jobId) => {
        return state.jobDestinationParametersByJobId[jobId] || [];
    },
};

const actions = {
    fetchJobDestinationParams: async ({ commit }, jobId) => {
        const { data } = await axios.get(`${getAppRoot()}api/jobs/${jobId}/destination_params`);
        commit("saveJobDestinationParamsForJobId", { jobId, jobDestinationParams: data });
    },
};

const mutations = {
    saveJobDestinationParamsForJobId: (state, { jobId, jobDestinationParams }) => {
        Vue.set(state.jobDestinationParametersByJobId, jobId, jobDestinationParams);
    },
};

export const jobDestinationParametersStore = {
    state,
    getters,
    actions,
    mutations,
};
