export const state = {
    userTagList: [], // List of recent user tags
    modelTagCache: new Map(), // Maps model id to list of tags
};

export const getters = {
    getTagsById: (state) => (key) => {
        if (state.modelTagCache.has(key)) {
            const tagSet = state.modelTagCache.get(key); //.sort();
            return Array.from(tagSet);
        }
        return [];
    },
};

export const actions = {
    updateTags({ commit }, { key, tags }) {
        commit("setTags", { key, tags });
    },
    initializeTags({ dispatch, state }, { key, tags }) {
        if (!state.modelTagCache.has(key)) {
            dispatch("updateTags", { key, tags });
        }
    },
};

export const mutations = {
    setTags(state, { key, tags }) {
        state.modelTagCache = new Map(state.modelTagCache);
        state.modelTagCache.set(key, new Set(tags));
    },
    reset(state) {
        state.userTagList = [];
        state.modelTagCache = new Map();
    },
};

export const tagStore = {
    state,
    getters,
    actions,
    mutations,
};
