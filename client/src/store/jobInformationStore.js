export const state = {
    jobInformationJobId: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    jobInformation: (state) => (jobId) => {
        return state.jobInformationJobId[jobId] || [];
    },
};

const actions = {
    fetchJobInformation: async ({ commit }, jobId) => {
        const { data } = await axios.get(`${getAppRoot()}api/jobs/${jobId}/job_information`);
        commit("saveJobInformationForJobId", { jobId, jobInformation: data });
    },
};

const mutations = {
    saveJobInformationForJobId: (state, { jobId, jobInformation }) => {
        Vue.set(state.jobInformationJobId, jobId, jobInformation);
    },
};

export const jobInformationStore = {
    state,
    getters,
    actions,
    mutations,
};
