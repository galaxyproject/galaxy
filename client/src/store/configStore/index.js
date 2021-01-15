import { getConfig } from "./queries";

const state = {
    // null if not loaded yet
    config: null,
};

const getters = {
    config({ state }) {
        return state?.config || {};
    },
    configIsLoaded({ state }) {
        return state?.config !== null;
    },
};

const mutations = {
    setConfigs(state, newConfigs = {}) {
        state.config = Object.assign({}, state.config || {}, newConfigs);
    },
};

const actions = {
    setConfigs({ commit }, newConfigs = {}) {
        commit("setConfigs", newConfigs);
    },
    async loadConfigs({ state, commit }, forceReload = false) {
        if (forceReload || state.config == null) {
            const configs = await getConfig();
            commit("setConfigs", configs);
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

export default configStore;
