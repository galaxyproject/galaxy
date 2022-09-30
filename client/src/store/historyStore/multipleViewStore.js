const state = {
    selectedHistories: [],
};

const getters = {
    getSelectedHistories: (state) => () => {
        return state.selectedHistories;
    },
};

const actions = {
    addHistoryToMultipleView: ({ commit }, historyId) => {
        commit("addHistory", { historyId });
    },
    removeHistoryFromMultipleView: ({ commit }, historyId) => {
        commit("removeHistory", { historyId });
    },
};

const mutations = {
    addHistory: (state, { historyId }) => {
        state.selectedHistories.push({ id: historyId });
    },
    removeHistory: (state, { historyId }) => {
        state.selectedHistories = state.selectedHistories.filter((h) => h.id !== historyId);
    },
};

export const multipleViewStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
