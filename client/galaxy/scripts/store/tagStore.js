export const tagStore = {
    state: {
        userTagList: [], // List of recent user tags
        modelTagCache: new Map() // Maps model id to list of tags
    },
    getters: {
        getTagsById: (state) => (key) => {
            return state.modelTagCache.get(key).sort();
        }
    },
    actions: {
        updateTags({ commit }, { key, tags }) {
            commit('setTags', { key, tags });
        }
    },
    mutations: {
        setTags(state, { key, tags }) {
            // Have to reset the object to a whole new object or the observable
            // will not trigger a change. Just setting a new property on
            // an object instance is not enough
            state.modelTagCache = new Map(state.modelTagCache);
            state.modelTagCache.set(key, tags);
        }
    }
}
