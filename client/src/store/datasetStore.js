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
    fetchDataset: async ({ commit }, { id }) => {
        const url = `api/datasets/${id}`;
        const dataset = await urlData({ url });
        commit("saveDataset", { id, dataset });
    },
};

const mutations = {
    saveDataset: (state, { id, dataset }) => {
        Vue.set(state.items, id, dataset);
    },
    saveDatasets: (state, { payload }) => {
        payload.forEach((item) => {
            const id = item.id;
            if (id in state.items) {
                const localItem = state.items[id];
                Object.keys(localItem).forEach((key) => {
                    localItem[key] = item[key];
                });
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
