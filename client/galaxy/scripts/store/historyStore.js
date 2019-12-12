export const state = {
    historiesById: {}
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    getHistoryById: state => historyId => {
        return state.historiesById[historyId];
    }
};

const actions = {
    fetchHistoryForId: async ({ commit }, historyId) => {
        const params = {};
        const { data } = await axios.get(`${getAppRoot()}api/histories/${historyId}`, { params });
        commit("saveHistoryForId", { historyId, historyData: data });
    }
};

const mutations = {
    saveHistoryForId: (state, { historyId, historyData }) => {
        Vue.set(state.historiesById, historyId, historyData);
    }
};

export const historyStore = {
    state,
    getters,
    actions,
    mutations
};
