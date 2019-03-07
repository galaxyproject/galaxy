export const tagStore = {
    state: {
        userTagList: [], // List of recent user tags
        modelTagCache: new Map() // Maps model id to list of tags
    },
    getters: {
        getTagsById: (state) => (key) => {
            if (state.modelTagCache.has(key)) {
                let tagSet = state.modelTagCache.get(key); //.sort();
                return Array.from(tagSet);
            }
            return [];
        }
    },
    actions: {
        updateTags({ commit }, { key, tags }) {
            commit('setTags', { key, tags });
        }
    },
    mutations: {
        setTags(state, { key, tags }) {
            state.modelTagCache = new Map(state.modelTagCache);
            state.modelTagCache.set(key, new Set(tags));
        }
    }
}
