import { getLibraries } from "./queries";

const state = {
    loadPromise: null,
    libraries: [],
};

const getters = {
    busy({ state }) {
        return state.loadPromise !== null;
    },
};

const mutations = {
    setLibraries(state, libraries = []) {
        state.libraries = libraries;
    },
    setLoadPromise(state, loadPromise) {
        state.loadPromise = loadPromise;
    },
};

const actions = {
    loadLibraries({ state, commit }, filters) {
        if (!state.loadPromise) {
            const loadPromise = getLibraries(filters)
                .then((libs) => commit("setLibraries", libs))
                .finally(() => commit("setLoadPromise", null));
            commit("setLoadPromise", loadPromise);
        }
    },
};

export const libraryStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
