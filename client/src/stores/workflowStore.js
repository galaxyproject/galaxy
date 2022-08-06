import { defineStore } from "pinia";
import axios from "axios";

import { getAppRoot } from "onload/loadConfig";

export const useWorkflowStore = defineStore("workflowStore", {
    state: () => ({
        workflowsByInstanceId: {},
    }),
    getters: {
        getWorkflowByInstanceId: (state) => {
            return (workflowId) => state.workflowsByInstanceId[workflowId];
        },
        getWorkflowNameByInstanceId: (state) => {
            return (workflowId) => {
                const details = state.workflowsByInstanceId[workflowId];
                if (details && details.name) {
                    return details.name;
                } else {
                    return "...";
                }
            };
        },
        getStoredWorkflowIdByInstanceId: (state) => {
            return (workflowId) => {
                const storedWorkflow = state.workflowsByInstanceId[workflowId];
                return storedWorkflow?.id;
            };
        },
    },
    actions: {
        async fetchWorkflowForInstanceId(workflowId) {
            console.debug("Fetching workflow details for", workflowId);
            const params = { instance: "true" };
            const { data } = await axios.get(`${getAppRoot()}api/workflows/${workflowId}`, { params });
            this.$patch({ workflowId: data });
        },
    },
});
