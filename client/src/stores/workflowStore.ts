import { defineStore } from "pinia";
import axios from "axios";
import type { Steps } from "@/stores/workflowStepStore";
import { getAppRoot } from "@/onload/loadConfig";

interface Workflow {
    [index: string]: any;
    steps: Steps;
}

export const useWorkflowStore = defineStore("workflowStore", {
    state: () => ({
        workflowsByInstanceId: {} as { [index: string]: Workflow },
    }),
    getters: {
        getWorkflowByInstanceId: (state) => {
            return (workflowId: string) => {
                return state.workflowsByInstanceId[workflowId];
            };
        },
        getWorkflowNameByInstanceId: (state) => {
            return (workflowId: string) => {
                const details = state.workflowsByInstanceId[workflowId];
                if (details && details.name) {
                    return details.name;
                } else {
                    return "...";
                }
            };
        },
        getStoredWorkflowIdByInstanceId: (state) => {
            return (workflowId: string) => {
                const storedWorkflow = state.workflowsByInstanceId[workflowId];
                return storedWorkflow?.id;
            };
        },
    },
    actions: {
        async fetchWorkflowForInstanceId(workflowId: string) {
            console.debug("Fetching workflow details for", workflowId);
            const params = { instance: "true" };
            const { data } = await axios.get(`${getAppRoot()}api/workflows/${workflowId}`, { params });
            this.$patch((state) => {
                state.workflowsByInstanceId[workflowId] = data as Workflow;
            });
        },
    },
});
