import { defineStore } from "pinia";
import axios from "axios";
import type { Steps } from "@/stores/workflowStepStore";
import { createWorkflowQuery } from "@/components/Panels/utilities";
import { getAppRoot } from "@/onload/loadConfig";

export interface Workflow {
    [index: string]: any;
    steps: Steps;
}

export const useWorkflowStore = defineStore("workflowStore", {
    state: () => ({
        allWorkflows: [] as Workflow[],
        workflowResults: [] as Workflow[],
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
        getWorkflows: (state) => {
            return (filterSettings: Record<string, string | boolean>) => {
                if (Object.keys(filterSettings).length === 0) {
                    return state.allWorkflows;
                } else {
                    return state.workflowResults;
                }
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
        async fetchWorkflows(filterSettings: Record<string, string | boolean>) {
            if (Object.keys(filterSettings).length !== 0) {
                const query = createWorkflowQuery(filterSettings); // remove from here?
                const { data } = await axios.get(`${getAppRoot()}api/workflows`, {
                    params: { search: query, skip_step_counts: true },
                });
                this.workflowResults = data;
            } else if (this.allWorkflows.length === 0) {
                // TODO: add all params: ?limit=50&offset=0&search=&skip_step_counts=true
                const { data } = await axios.get(`${getAppRoot()}api/workflows`, {
                    params: { skip_step_counts: true },
                });
                this.allWorkflows = data;
            }
        },
    },
});
