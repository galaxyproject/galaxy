import {
    createNewHistory,
    deleteHistoryById,
    getHistoryList,
    getHistoryById,
    getCurrentHistoryFromServer,
    setCurrentHistoryOnServer,
    updateHistoryFields,
} from "../queries";

import Vue from "vue";
import { sortByObjectProp } from "utils/sorting";

export const state = {
    currentHistoryId: null,
    histories: {},
};

export const mutations = {
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
        const newMap = newHistories.reduce((acc, h) => ({ ...acc, [h.id]: h }), {});
        Vue.set(state, "histories", newMap);
    },
};

export const getters = {
    currentHistoryId: (state, getters) => {
        const { histories, currentHistoryId: id } = state;
        return id in histories ? id : getters.firstHistoryId;
    },
    firstHistoryId: (state, getters) => {
        const { histories } = getters;
        return histories.length ? histories[0].id : null;
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
};

export const actions = {
    async loadUserHistories({ dispatch, commit }) {
        const myHistories = await getHistoryList();
        const currentHistory = await getCurrentHistoryFromServer();
        commit("setHistories", myHistories);
        await dispatch("selectHistory", currentHistory);
    },
    async loadHistoryById({ commit, getters }, id) {
        const existing = getters.getHistoryById(id);
        const lastUpdated = existing?.update_time || null;
        const history = await getHistoryById(id, lastUpdated);
        commit("setHistory", history);
    },
    async setCurrentHistoryId({ dispatch }, id) {
        const nextHistory = await setCurrentHistoryOnServer(id);
        await dispatch("selectHistory", nextHistory);
    },
    async createNewHistory({ dispatch }) {
        const newHistory = await createNewHistory();
        await dispatch("selectHistory", newHistory);
    },
    async updateHistory({ commit }, { id, ...updateFields }) {
        // save new history params should be an object with an id property and any additional
        // properties that are to be updated on the server. A full history object is not required
        const saveResult = await updateHistoryFields(id, updateFields);
        commit("setHistory", saveResult);
    },
    async deleteHistory({ commit }, { history, purge = false }) {
        const deletedHistory = await deleteHistoryById(history.id, purge);
        commit("deleteHistory", deletedHistory);
        commit("setCurrentHistoryId", null);
    },
    // set in store w/o updating
    setHistory({ commit }, history) {
        commit("setHistory", history);
    },
    selectHistory({ commit }, history) {
        commit("setHistory", history);
        commit("setCurrentHistoryId", history.id);
    },
    reset({ commit }) {
        commit("setHistories", []);
        commit("setCurrentHistoryId", null);
    },
};

export const historyStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
