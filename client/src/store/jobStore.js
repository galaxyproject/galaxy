export const state = {
    job: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    job: (state) => (jobId) => {
        return state.job[jobId];
    },
};

const actions = {
    fetchJob: async ({ commit }, jobId) => {
        const { data } = await axios.get(`${getAppRoot()}api/jobs/${jobId}?full=true`);
        commit("saveJobForJobId", { jobId, job: data });
    },
};

const mutations = {
    saveJobForJobId: (state, { jobId, job }) => {
        Vue.set(state.job, jobId, job);
    },
};

export const jobStore = {
    state,
    getters,
    actions,
    mutations,
};
