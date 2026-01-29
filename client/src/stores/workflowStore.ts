import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import { GalaxyApi } from "@/api";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";

export const useWorkflowStore = defineStore("workflowStore", () => {
    const workflowsByInstanceId = ref<{ [index: string]: StoredWorkflowDetailed }>({});
    const fullWorkflowsByIdAndVersion = ref(new Map<string, any>());

    /** Cached promises for fetching full workflows to prevent duplicate requests */
    const fullWorkflowPromises = new Map<string, Promise<any>>();

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

    // TODO: A better way? Could use ref<{ [id: string]: { [version: string]: any } }>({});
    function uniqueIdAndVersionKey(workflowId: string, version?: number) {
        return `${workflowId}${version ? `_${version}` : "_latest"}`;
    }

    /**
     * Fetches full workflow details, avoiding multiple fetches occurring simultaneously.
     * If a fetch is already in progress for the same workflow+version, subsequent callers
     * will await the same promise instead of initiating a new request.
     * @param workflowId workflow id
     * @param version optional version number
     */
    async function getFullWorkflowCached(workflowId: string, version?: number) {
        const key = uniqueIdAndVersionKey(workflowId, version);

        // Return cached workflow if already fetched
        if (fullWorkflowsByIdAndVersion.value.has(key)) {
            return fullWorkflowsByIdAndVersion.value.get(key);
        }

        // Check if a fetch is already in progress for this workflow+version
        const existingPromise = fullWorkflowPromises.get(key);
        if (existingPromise) {
            await existingPromise;
            // After the promise resolves, the workflow should be in cache
            return fullWorkflowsByIdAndVersion.value.get(key);
        }

        // Fetch the full workflow and store the promise
        const fetchPromise = getWorkflowFull(workflowId, version);
        fullWorkflowPromises.set(key, fetchPromise);

        try {
            const storedWorkflow = await fetchPromise;
            if (storedWorkflow) {
                fullWorkflowsByIdAndVersion.value.set(key, storedWorkflow);
            }
            return storedWorkflow;
        } finally {
            // Remove promise from tracking map
            fullWorkflowPromises.delete(key);
        }
    }

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
            const promise = GalaxyApi().GET("/api/workflows/{workflow_id}", {
                params: {
                    path: { workflow_id: workflowId },
                    query: { instance: true },
                },
            });
            workflowDetailPromises.set(workflowId, promise);
            const { data, error } = await promise;
            if (error) {
                throw Error(`Failed to retrieve workflow. ${error.err_msg}`);
            }
            set(workflowsByInstanceId.value, workflowId, data);
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
        fetchWorkflowForInstanceId,
        fetchWorkflowForInstanceIdCached,
        getFullWorkflowCached,
        getStoredWorkflowByInstanceId,
        getStoredWorkflowIdByInstanceId,
        getStoredWorkflowNameByInstanceId,
        workflowsByInstanceId,
    };
});
