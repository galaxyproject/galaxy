/**
 * Contains flags for simple options that doesn't fit as full user's preferences.
 * Like permanently acknowledge or dismissing certain messages.
 */

const state = {
    showSelectionQueryBreakWarning: true,
};

const getters = {
    getShowSelectionQueryBreakWarning: (state) => () => {
        return state.showSelectionQueryBreakWarning;
    },
};

const actions = {
    ignoreSelectionQueryBreakWarning: ({ commit }) => {
        commit("saveShowSelectionQueryBreakWarningFlag", { show: false });
    },
};

const mutations = {
    saveShowSelectionQueryBreakWarningFlag: (state, { show }) => {
        state.showSelectionQueryBreakWarning = show;
    },
};

export const userFlagsStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
