import { getConfig } from "./queries";

const state = {
    config: null,
};

const getters = {
    config(state) {
        return state?.config || {};
    },
    configIsLoaded(state) {
        return state?.config !== null;
    },
};

const mutations = {
    setConfigs(state, newConfigs = {}) {
        state.config = Object.assign({}, state.config || {}, newConfigs);
    },
};

// Holds promise for in-flight loads
let loadPromise;

const actions = {
    loadConfigs({ commit }) {
        if (!loadPromise) {
            loadPromise = getConfig()
                .then((configs) => commit("setConfigs", configs))
                .catch((err) => console.warn("loadConfigs error", err))
                .finally(() => (loadPromise = null));
        }
    },
};

export const configStore = {
    namespaced: true,
    getters,
    state,
    mutations,
    actions,
};
