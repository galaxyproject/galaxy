export const state = {
    datasetByHDAId: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    dataset: (state) => (hda_id) => {
        return state.datasetByHDAId[hda_id] || [];
    },
};

const actions = {
    fetchDataset: async ({ commit }, hda_id) => {
        const { data } = await axios.get(`${getAppRoot()}api/datasets/${hda_id}`);
        commit("saveDatasetForHDAId", { hda_id, dataset: data });
    },
};

const mutations = {
    saveDatasetForHDAId: (state, { hda_id, dataset }) => {
        Vue.set(state.datasetByHDAId, hda_id, dataset);
    },
};

export const datasetsStore = {
    state,
    getters,
    actions,
    mutations,
};
