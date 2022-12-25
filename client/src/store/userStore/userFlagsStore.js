/**
 * Contains flags for simple options that doesn't fit as full user's preferences.
 * Like permanently acknowledge or dismissing certain messages.
 */

const state = {
    showSelectionQueryBreakWarning: true,
    currentTheme: null,
};

const getters = {
    getShowSelectionQueryBreakWarning: (state) => () => {
        return state.showSelectionQueryBreakWarning;
    },
    getCurrentTheme(state) {
        return state.currentTheme;
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
    setCurrentTheme(state, theme) {
        state.currentTheme = theme;
    },
};

export const userFlagsStore = {
    namespaced: true,
    state,
    getters,
    mutations,
    actions,
};
