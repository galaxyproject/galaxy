export const state = {
    toolById: {},
    toolsList: [],
    totalToolCount: undefined,
};

import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

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
        ({ filterSettings }) => {
            // if no filters, return all tools
            if (Object.keys(filterSettings).length == 0 || filterSettings == {}) {
                return state.toolsList[0] ? state.toolsList[0] : [];
            }

            const allTools = state.toolsList[0];
            const returnedTools = [];

            for (const tool in allTools) {
                let hasMatches = false;
                for (const [key, filterValue] of Object.entries(filterSettings)) {
                    const actualValue = allTools[tool][key];
                    if (filterValue) {
                        if (!actualValue || !actualValue.toUpperCase().match(filterValue.toUpperCase())) {
                            hasMatches = false;
                            break;
                        } else {
                            hasMatches = true;
                        }
                    }
                }
                if (hasMatches) {
                    returnedTools.push(allTools[tool]);
                }
            }

            return returnedTools;
        },
    getTotalToolCount: (state) => () => state.totalToolCount,
};

const actions = {
    fetchToolForId: async ({ commit }, toolId) => {
        console.log("fetching tool");
        const { data } = await axios.get(`${getAppRoot()}api/tools/${toolId}`);
        commit("saveToolForId", { toolId, toolData: data });
    },
    fetchAllTools: async ({ commit }) => {
        console.log("fetching tools list");
        const { data } = await axios.get(`${getAppRoot()}api/tools?in_panel=False`);
        const toolCount = data.length;
        commit("saveTotalToolCount", { toolCount });
        commit("saveTools", { toolsData: data });
    },
};

const mutations = {
    saveToolForId: (state, { toolId, toolData }) => {
        Vue.set(state.toolById, toolId, toolData);
    },
    saveTools: (state, { toolsData }) => {
        Vue.set(state.toolsList, 0, toolsData);
    },
    saveTotalToolCount: (state, { toolCount }) => {
        state.totalToolCount = toolCount;
    },
};

export const toolStore = {
    state,
    getters,
    actions,
    mutations,
};
