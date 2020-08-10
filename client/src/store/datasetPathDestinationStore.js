export const state = {
    datasetPathDestination: {},
};

import { getPathDestination } from "components/Dataset/compositeDatasetUtils";

const getters = {
    pathDestination: (state) => (history_dataset_id, path) => {
        if (state.datasetPathDestination[history_dataset_id]) {
            return state.datasetPathDestination[history_dataset_id][path];
        } else {
            return;
        }
    },
};

const actions = {
    fetchPathDestination: async ({ commit }, { history_dataset_id, path }) => {
        const data = await getPathDestination(history_dataset_id, path);
        commit("savePathDestination", { history_dataset_id, path, pathDestination: data });
    },
};

const mutations = {
    savePathDestination: (state, { history_dataset_id, path, pathDestination }) => {
        state.datasetPathDestination[history_dataset_id] = { [path]: pathDestination };
    },
};

export const datasetPathDestinationStore = {
    state,
    getters,
    actions,
    mutations,
};
