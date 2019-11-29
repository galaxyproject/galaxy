import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const state = {
    historyDetailsById: {}
};

const getters = {
    getHistoryNameById: state => historyId => {
        const details = state.historyDetailsById[historyId];
        if (details && details.name) {
            return details.name;
        } else {
            return "Unavailable";
        }
    }
};

const actions = {
    fetchHistories: async ({ commit }) => {
        const { data } = await axios.get(`${getAppRoot()}api/histories`);
        commit("saveHistories", { histories: data });
    }
};

const mutations = {
    saveHistories: (state, { histories }) => {
        const historyDetailsById = {};
        histories.forEach( x => {
            historyDetailsById[x.id] = x;
        });
        state.historyDetailsById = historyDetailsById;
    }
};

export const historyStore = {
    state,
    getters,
    actions,
    mutations
};
