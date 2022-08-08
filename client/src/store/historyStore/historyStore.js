import Vue from "vue";
import { sortByObjectProp } from "utils/sorting";

import {
    createNewHistory,
    deleteHistoryById,
    getHistoryList,
    getHistoryById,
    getCurrentHistoryFromServer,
    setCurrentHistoryOnServer,
    updateHistoryFields,
    cloneHistory,
    secureHistory,
} from "./model/queries";

const state = {
    // selected history
    currentHistoryId: null,
    // histories for current user
    histories: {},
    historiesLoading: false,
};

const mutations = {
    setCurrentHistoryId(state, id) {
        state.currentHistoryId = id;
    },
    setHistory(state, newHistory) {
        Vue.set(state.histories, newHistory.id, newHistory);
    },
    deleteHistory(state, doomed) {
        Vue.delete(state.histories, doomed.id);
    },
    setHistories(state, newHistories = []) {
        const currentHistoryId = state.currentHistoryId;
        const currentHistory = state.histories[currentHistoryId];
        const newMap = newHistories.reduce((acc, h) => ({ ...acc, [h.id]: h }), {});
        if (currentHistory) {
            // The incoming history list contains less information than the current history
            // so we restore the existing current history since it gets updated regularly anyway
            newMap[currentHistoryId] = currentHistory;
        }
        Vue.set(state, "histories", newMap);
    },
    setHistoriesLoading(state, isLoading) {
        state.historiesLoading = isLoading;
    },
};

const getters = {
    currentHistoryId: (state, getters) => {
        const { histories, currentHistoryId: id } = state;
        return id in histories ? id : getters.firstHistoryId;
    },
    firstHistory: (state, getters) => {
        const { histories } = getters;
        return histories.length ? histories[0] : null;
    },
    firstHistoryId: (state, getters) => {
        return getters?.firstHistory?.id || null;
    },
    currentHistory: (state, getters) => {
        const { currentHistoryId: id } = getters;
        return id ? getters.getHistoryById(id) : null;
    },
    histories: (state) => {
        return Object.values(state.histories).sort(sortByObjectProp("name"));
    },
    getHistoryById: (state) => (id) => {
        return id in state.histories ? state.histories[id] : null;
    },
    getHistoryNameById: (state) => (id) => {
        const details = state.histories[id];
        if (details && details.name) {
            return details.name;
        } else {
            return "...";
        }
    },
    historiesLoading: (state) => {
        return state.historiesLoading;
    },
};

// flags to keep track of loading states
const isLoadingHistory = new Map();
let isLoadingHistories = false;

const actions = {
    async copyHistory({ dispatch }, { history, name, copyAll }) {
        const newHistory = await cloneHistory(history, name, copyAll);
        return dispatch("selectHistory", newHistory);
    },
    async createNewHistory({ dispatch }) {
        // create history, then select it as current at the same time
        const newHistory = await createNewHistory();
        return dispatch("selectHistory", newHistory);
    },
    async deleteHistory({ dispatch, commit, getters }, { history, purge = false }) {
        const deletedHistory = await deleteHistoryById(history.id, purge);
        commit("deleteHistory", deletedHistory);
        if (getters.firstHistoryId) {
            return dispatch("setCurrentHistory", getters.firstHistoryId);
        } else {
            return dispatch("createNewHistory");
        }
    },
    async loadCurrentHistory({ dispatch }) {
        return getCurrentHistoryFromServer().then((history) => dispatch("selectHistory", history));
    },
    loadHistories({ commit }) {
        if (!isLoadingHistories) {
            commit("setHistoriesLoading", true);
            isLoadingHistories = getHistoryList()
                .then((list) => {
                    commit("setHistories", list);
                })
                .catch((err) => {
                    console.warn("loadHistories error", err);
                })
                .finally(() => {
                    isLoadingHistories = false;
                    commit("setHistoriesLoading", false);
                });
        }
    },
    loadHistoryById({ dispatch }, id) {
        if (!isLoadingHistory.has(id)) {
            const p = getHistoryById(id)
                .then((history) => {
                    dispatch("setHistory", history);
                })
                .catch((err) => {
                    console.warn("loadHistoryById error", id, err);
                })
                .finally(() => {
                    isLoadingHistory.delete(id);
                });
            isLoadingHistory.set(id, p);
        }
    },
    resetHistory({ commit }) {
        commit("setHistories", []);
        commit("setCurrentHistoryId", null);
    },
    async secureHistory({ commit }, history) {
        const updatedHistory = await secureHistory(history);
        commit("setHistory", updatedHistory);
    },
    selectHistory({ commit }, history) {
        commit("setHistory", history);
        commit("setCurrentHistoryId", history.id);
    },
    async setCurrentHistory({ dispatch, getters }, id) {
        const changedHistory = await setCurrentHistoryOnServer(id);
        return dispatch("selectHistory", changedHistory);
    },
    setHistory({ commit }, history) {
        commit("setHistory", history);
    },
    async updateHistory({ commit }, { id, ...updateFields }) {
        // save new history params should be an object with an id property and any additional
        // properties that are to be updated on the server. A full history object is not required
        const saveResult = await updateHistoryFields(id, updateFields);
        commit("setHistory", saveResult);
    },
};

export const historyStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
