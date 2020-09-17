import { getConfig } from "./queries";

const defaultConfigs = {};

const state = {
    config: Object.assign({}, defaultConfigs),
};

const mutations = {
    setConfigs(state, newConfigs = {}) {
        state.config = Object.assign({}, defaultConfigs, state.config, newConfigs);
    },
};

const actions = {
    async loadConfigs({ commit }) {
        const configs = await getConfig();
        commit("setConfigs", configs);
    },
    async $init({ dispatch }) {
        await dispatch("loadConfigs");
    },
};

export const configStore = {
    namespaced: true,
    state,
    mutations,
    actions,
};

export default configStore;
