import Vue from "vue";
import VuexPersistence from "vuex-persist";
import { History } from "./History";
import { getHistoriesForCurrentUser, getCurrentHistoryFromServer, setCurrentHistoryOnServer } from "./queries";
// import { changeGalaxyHistory } from "../adapters/changeGalaxyHistory";

const persist = new VuexPersistence();
Vue.use(persist);

// default state
export const state = {
    currentHistoryId: null,
    histories: [],
};

export const mutations = {
    setCurrentHistoryId(state, id) {
        state.currentHistoryId = id;
    },
    setHistory(state, rawHistory) {
        const history = new History(rawHistory);
        const newHistories = new Map(state.histories);
        state.histories = newHistories.set(history.id, new History(history));
    },
    setHistories(state, list) {
        const newHistories = list.reduce((histories, rawHistory) => {
            const h = new History(rawHistory);
            return histories.set(h.id, h);
        }, new Map());
        state.histories = newHistories;
    },
};

export const getters = {
    histories: (state) => {
        return Array.from(state.histories.values());
    },

    activeHistories: (state, getters) => {
        const list = Array.from(getters.histories);
        const okHistory = (h) => !h.deleted && !h.purged;
        const activeHistories = list.filter(okHistory);
        return activeHistories;
    },

    currentHistoryId: (state, getters) => {
        const activeHistories = getters.activeHistories;
        const validIds = activeHistories.map((h) => h.id);

        if (state.currentHistoryId && validIds.includes(state.currentHistoryId)) {
            return state.currentHistoryId;
        }
        if (validIds.length) {
            return validIds[0];
        }
        return null;
    },

    currentHistory: (state, getters) => {
        const currentId = getters.currentHistoryId;
        return getters.getHistoryById(currentId);
    },

    getHistoryById: (state) => (historyId) => {
        const raw = state.histories.get(historyId);
        const history = raw ? new History(raw) : null;
        return history;
    },
};

export const actions = {
    async $init({ dispatch }, { store }) {
        store.watch(
            (state) => state.user.currentUser,
            async () => {
                const myHistories = await getHistoriesForCurrentUser();
                dispatch("storeHistories", myHistories);
            },
            { immediate: true }
        );
        dispatch("loadCurrentHistoryId");
    },

    async loadCurrentHistoryId({ dispatch }) {
        const serverSaysWhat = await getCurrentHistoryFromServer();
        if (serverSaysWhat && serverSaysWhat.id) {
            dispatch("storeCurrentHistoryId", serverSaysWhat.id);
        }
    },

    async storeCurrentHistoryId({ commit, getters }, id) {
        if (id == getters.currentHistoryId) return;
        const rawHistory = await setCurrentHistoryOnServer(id);
        if (rawHistory && rawHistory.id) {
            // tell legacy code that we changed the history,
            // remove when the backbone history management is not required
            // changeGalaxyHistory(rawHistory.id);
            commit("setCurrentHistoryId", rawHistory.id);
        }
    },

    // boilerplate (tm): let's think of 3 names for functions
    // that all do the same thing

    async storeHistories({ commit }, list) {
        commit("setHistories", list);
    },

    async storeHistory({ commit }, history) {
        commit("setHistory", history);
    },
};

export const historyStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};

/**
 * Localstorage plugin
 *
 * Caches simple user settings like "currentHistory" in localStorage instead
 * of having the server do that. Hopefully doing this in the client
 * will mean we can move closer towards a completely stateless REST api.
 */

export const historyPersist = new VuexPersistence({
    key: "vuex-state-history",
    modules: ["betaHistory"],
    reducer: (state) => {
        return {
            history: {
                currentHistoryId: state.betaHistory.currentHistoryId,
            },
        };
    },
});
