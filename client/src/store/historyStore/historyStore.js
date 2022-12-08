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
        // The incoming history list may contain less information than the already stored
        // histories, so we ensure that already available details are not getting lost.
        const enrichedHistories = newHistories.map((history) => {
            const historyState = state.histories[history.id] || {};
            return Object.assign({}, historyState, history);
        });
        // Histories are provided as list but stored as map.
        const newMap = enrichedHistories.reduce((acc, h) => ({ ...acc, [h.id]: h }), {});
        // Ensure that already stored histories, which are not available in the incoming array,
        // are not lost. This happens e.g. with shared histories since they have different owners.
        Object.values(state.histories).forEach((history) => {
            const historyId = history.id;
            if (!newMap[historyId]) {
                newMap[historyId] = history;
            }
        });
        // Update stored histories
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
const isLoadingHistory = new Set();
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
            getHistoryById(id)
                .then((history) => {
                    dispatch("setHistory", history);
                })
                .catch((err) => {
                    console.warn("loadHistoryById error", id, err);
                })
                .finally(() => {
                    isLoadingHistory.delete(id);
                });
            isLoadingHistory.add(id);
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
    async setCurrentHistory({ dispatch }, id) {
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
