import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const state = {
    historyDetailsById: {},
    historyById: {},
};

const getters = {
    getHistoryById: (state) => (historyId) => {
        return state.historyById[historyId];
    },
    getHistoryNameById: (state) => (historyId) => {
        const details = state.historyById[historyId];
        if (details && details.name) {
            return details.name;
        } else {
            return "...";
        }
    },
};

const actions = {
    fetchHistories: async ({ commit }) => {
        const { data } = await axios.get(`${getAppRoot()}api/histories`);
        commit("saveHistories", { histories: data });
    },
    fetchHistoryForId: async ({ commit }, historyId) => {
        const params = {};
        const { data } = await axios.get(`${getAppRoot()}api/histories/${historyId}`, { params });
        commit("saveHistoryForId", { historyId, historyData: data });
    },
};

const mutations = {
    saveHistories: (state, { histories }) => {
        const historyDetailsById = {};
        histories.forEach((x) => {
            historyDetailsById[x.id] = x;
        });
        state.historyDetailsById = historyDetailsById;
    },
    saveHistoryForId: (state, { historyId, historyData }) => {
        Vue.set(state.historyById, historyId, historyData);
    },
};

export const historyStore = {
    state,
    getters,
    actions,
    mutations,
};
