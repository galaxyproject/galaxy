export const state = {
    datasetExtFilesById: {},
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    getDatasetExtFiles: (state) => (history_dataset_id) => {
        return state.datasetExtFilesById[history_dataset_id] || null;
    },
};

const actions = {
    fetchDatasetExtFiles: async ({ commit }, history_dataset_id) => {
        const { data } = await axios.get(
            `${getAppRoot()}api/histories/${history_dataset_id}/contents/${history_dataset_id}/extra_files`
        );
        commit("saveDatasetExtFiles", { history_dataset_id, datasetExtFiles: data });
    },
};

const mutations = {
    saveDatasetExtFiles: (state, { history_dataset_id, datasetExtFiles }) => {
        Vue.set(state.datasetExtFilesById, history_dataset_id, datasetExtFiles);
    },
};

export const datasetExtFilesStore = {
    state,
    getters,
    actions,
    mutations,
};
