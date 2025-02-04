import axios from "axios";
import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import { getAppRoot } from "@/onload/loadConfig";
import { type Steps } from "@/stores/workflowStepStore";

export interface Workflow extends Omit<StoredWorkflowDetailed, 'steps'> {
    steps: Steps;
}

export const useWorkflowStore = defineStore("workflowStore", () => {
    const workflowsByInstanceId = ref<{ [index: string]: Workflow }>({});

    const getStoredWorkflowByInstanceId = computed(() => (workflowId: string) => {
        return workflowsByInstanceId.value[workflowId];
    });

    const getStoredWorkflowIdByInstanceId = computed(() => (workflowId: string) => {
        const storedWorkflow = workflowsByInstanceId.value[workflowId];
        return storedWorkflow?.id;
    });

    const getStoredWorkflowNameByInstanceId = computed(() => (workflowId: string, defaultName = "...") => {
        const details = workflowsByInstanceId.value[workflowId];

        if (details && details.name) {
            return details.name;
        } else {
            return defaultName;
        }
    });

    // stores in progress promises to avoid overlapping requests
    const workflowDetailPromises = new Map<string, Promise<unknown>>();

    /**
     * Fetches workflow details, avoiding multiple fetches occurring simultaneously
     * @param workflowId instance id of workflow to fetch
     */
    async function fetchWorkflowForInstanceId(workflowId: string) {
        const promise = workflowDetailPromises.get(workflowId);

        if (promise) {
            console.debug("Workflow details fetching already requested for", workflowId);
            await promise;
        } else {
            console.debug("Fetching workflow details for", workflowId);

            const params = { instance: "true" };
            const promise = axios.get(`${getAppRoot()}api/workflows/${workflowId}`, { params });

            workflowDetailPromises.set(workflowId, promise);

            const { data } = await promise;

            set(workflowsByInstanceId.value, workflowId, data as Workflow);
        }

        workflowDetailPromises.delete(workflowId);
    }

    /**
     * Fetches workflow details only if they are not already in the store
     * @param workflowId instance id of workflow to maybe fetch
     */
    async function fetchWorkflowForInstanceIdCached(workflowId: string) {
        if (!Object.keys(workflowsByInstanceId.value).includes(workflowId)) {
            await fetchWorkflowForInstanceId(workflowId);
        }
    }

    return {
        workflowsByInstanceId,
        getStoredWorkflowByInstanceId,
        getStoredWorkflowIdByInstanceId,
        getStoredWorkflowNameByInstanceId,
        fetchWorkflowForInstanceId,
        fetchWorkflowForInstanceIdCached,
    };
});
