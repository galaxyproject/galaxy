export const state = {
    panel: {},
    currentPanelView: null,
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

const getters = {
    panel: (state) => (panelView) => {
        return state.panel[panelView] || [];
    },
    currentPanel: (state) => {
        const effectiveView = state.currentPanelView || "default";
        const val = state.panel[effectiveView] || [];
        return val;
    },
    currentPanelView: (state) => {
        return state.currentPanelView;
    },
};

const actions = {
    initCurrentPanelView: async ({ commit, state, dispatch }, siteDefaultPanelView) => {
        const panelView = state.currentPanelView || siteDefaultPanelView;
        if (state.currentPanelView == null) {
            commit("setCurrentPanelView", { panelView });
        }
        const response = await axios.get(`${getAppRoot()}api/tools?in_panel=true&view=${panelView}`).catch((error) => {
            if (error.response && error.response.status == 400) {
                // Assume the stored panelView disappeared, revert to the panel default for this site.
                dispatch("setCurrentPanelView", siteDefaultPanelView);
            }
        });
        if (response !== undefined) {
            commit("savePanelView", { panelView, panel: response.data });
        }
    },
    setCurrentPanelView: async ({ commit }, panelView) => {
        commit("setCurrentPanelView", { panelView });
        const { data } = await axios.get(`${getAppRoot()}api/tools?in_panel=true&view=${panelView}`);
        commit("savePanelView", { panelView, panel: data });
    },
    fetchPanel: async ({ commit }, panelView) => {
        const { data } = await axios.get(`${getAppRoot()}api/tools?in_panel=true&view=${panelView}`);
        commit("savePanelView", { panelView, panel: data });
    },
};

const mutations = {
    savePanelView: (state, { panelView, panel }) => {
        Vue.set(state.panel, panelView, panel);
    },
    setCurrentPanelView: (state, { panelView }) => {
        state.currentPanelView = panelView;
    },
};

export const panelStore = {
    namespaced: true,
    state,
    getters,
    actions,
    mutations,
};
