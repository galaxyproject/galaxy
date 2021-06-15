/**
 * Vuex store module used for managing search parameters in the grid. Currently
 * only manages the tags that access this store via the new tagging components,
 * but presumably the entire grid search filter criteria will live here one day.
 */

export const gridSearchStore = {
    state: {
        searchTags: new Set(),
    },
    mutations: {
        // TODO: we could write an equivalence comparator here for searchTag
        // Sets and not register a change if the new set is equivalent
        setSearchTags(state, tags) {
            state.searchTags = new Set(tags);
        },
    },
    actions: {
        toggleSearchTag({ state, commit }, { text }) {
            const tags = new Set(state.searchTags);
            tags.has(text) ? tags.delete(text) : tags.add(text);
            commit("setSearchTags", tags);
        },
        removeSearchTag({ state, commit }, { text }) {
            const tags = new Set(state.searchTags);
            tags.delete(text);
            commit("setSearchTags", tags);
        },
        clearSearchTags({ state, commit }) {
            commit("setSearchTags", new Set());
        },
    },
};
