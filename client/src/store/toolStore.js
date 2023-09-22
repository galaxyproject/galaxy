export const state = {
    toolById: {},
    toolResults: [],
    allTools: [],
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { filterTools, createWhooshQuery } from "components/Panels/utilities";

const getters = {
    getToolForId: (state) => (toolId) => {
        return state.toolById[toolId];
    },
    getToolNameById: (state) => (toolId) => {
        const details = state.toolById[toolId];
        if (details && details.name) {
            return details.name;
        } else {
            return "...";
        }
    },
    getTools:
        (state) =>
        ({ filterSettings, toolbox }) => {
            if (Object.keys(filterSettings).length === 0) {
                return state.allTools;
            } else {
                return filterTools(toolbox, state.toolResults);
            }
        },
};

const actions = {
    fetchToolForId: async ({ commit }, toolId) => {
        console.log("fetching tool");
        const { data } = await axios.get(`${getAppRoot()}api/tools/${toolId}`);
        commit("saveToolForId", { toolId, toolData: data });
    },
    fetchAllTools: async ({ commit }, { filterSettings, panelView, toolbox }) => {
        if (Object.keys(filterSettings).length !== 0) {
            // Parsing filterSettings to Whoosh query
            const q = createWhooshQuery(filterSettings, panelView, toolbox);
            const { data } = await axios.get(`${getAppRoot()}api/tools`, { params: { q } });
            commit("saveToolResults", { toolsData: data });
        } else if (state.allTools.length === 0) {
            const { data } = await axios.get(`${getAppRoot()}api/tools?in_panel=False`);
            commit("saveAllTools", { toolsData: data });
        }
    },
};

const mutations = {
    saveToolForId: (state, { toolId, toolData }) => {
        Vue.set(state.toolById, toolId, toolData);
    },
    saveToolResults: (state, { toolsData }) => {
        state.toolResults = toolsData;
    },
    saveAllTools: (state, { toolsData }) => {
        state.allTools = toolsData;
    },
};

export const toolStore = {
    state,
    getters,
    actions,
    mutations,
};
