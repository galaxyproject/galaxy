export const state = {
    jobMetricsByHdaId: {},
    jobMetricsByLddaId: {},
    jobMetricsByJobId: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    getJobMetricsByDatasetId:
        (state) =>
        (datasetId, datasetType = "hda") => {
            const jobMetricsObject = datasetType == "hda" ? state.jobMetricsByHdaId : state.jobMetricsByLddaId;
            return jobMetricsObject[datasetId] || [];
        },
    getJobMetricsByJobId: (state) => (jobId) => {
        return state.jobMetricsByJobId[jobId] || [];
    },
};

const actions = {
    fetchJobMetricsForDatasetId: async ({ commit }, { datasetId, datasetType }) => {
        const { data } = await axios.get(`${getAppRoot()}api/datasets/${datasetId}/metrics?hda_ldda=${datasetType}`);
        commit("saveJobMetricsForDatasetId", { datasetId, datasetType, jobMetrics: data });
    },
    fetchJobMetricsForJobId: async ({ commit }, jobId) => {
        const { data } = await axios.get(`${getAppRoot()}api/jobs/${jobId}/metrics`);
        commit("saveJobMetricsForJobId", { jobId, jobMetrics: data });
    },
};

const mutations = {
    saveJobMetricsForDatasetId: (state, { datasetId, datasetType, jobMetrics }) => {
        const jobMetricsObject = datasetType == "hda" ? state.jobMetricsByHdaId : state.jobMetricsByLddaId;
        Vue.set(jobMetricsObject, datasetId, jobMetrics);
    },
    saveJobMetricsForJobId: (state, { jobId, jobMetrics }) => {
        Vue.set(state.jobMetricsByJobId, jobId, jobMetrics);
    },
};

export const jobMetricsStore = {
    state,
    getters,
    actions,
    mutations,
};
