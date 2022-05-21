import Vue from "vue";
import { urlData } from "utils/url";

const state = {
    items: {},
};

const getters = {
    getDataset:
        (state) =>
        ({ id }) => {
            return state.items[id] || { hid: 0, name: "Wait..." };
        },
};

const actions = {
    fetchDataset: async ({ state, commit }, { id }) => {
        if (!state.items[id]) {
            const url = `api/datasets/${id}`;
            const dataset = await urlData({ url });
            commit("saveDataset", { id, dataset });
        }
    },
};

const mutations = {
    /**
     * Adds a new dataset.
     * @param {Array} dataset as returned by the datasets api (detailed serialization)
     */
    saveDataset: (state, { id, dataset }) => {
        Vue.set(state.items, id, dataset);
    },
    /**
     * Updates existing datasets. This is called by the history changed items store.
     * @param {Array} payload as returned by the history contents api (detailed serialization)
     */
    saveDatasets: (state, { payload }) => {
        payload.forEach((item) => {
            if (item.history_content_type == "dataset") {
                const id = item.id;
                if (state.items[id]) {
                    const localItem = state.items[id];
                    Object.keys(localItem).forEach((key) => {
                        localItem[key] = item[key];
                    });
                }
            }
        });
    },
};

export const datasetStore = {
    state,
    getters,
    actions,
    mutations,
};
