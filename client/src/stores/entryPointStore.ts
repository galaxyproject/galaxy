import { defineStore } from "pinia";
import { rethrowSimple } from "@/utils/simple-error";
import axios from "axios";
import isEqual from "lodash.isequal";
import { ref, type Ref } from "vue";

// Temporary Typedef. Replace with API types, as soon as endpoint is migrated
export type EntryPoint = {
    job_id: string;
    output_datasets_ids: string[];
    target: string;
    [key: string]: unknown;
};

export const useEntryPointStore = defineStore("entryPointStore", () => {
    const entryPoints: Ref<EntryPoint[]> = ref([]);
    const pollTimeout: Ref<ReturnType<typeof setTimeout> | null> = ref(null);

    function getEntryPointsForJob(jobId: string) {
        return entryPoints.value.filter((entryPoint) => entryPoint["job_id"] === jobId);
    }

    function getEntryPointsForHda(hdaId: string) {
        return entryPoints.value.filter((entryPoint) => entryPoint["output_datasets_ids"].includes(hdaId));
    }

    async function ensurePollingEntryPoints() {
        await fetchEntryPoints();
        pollTimeout.value = setTimeout(() => {
            ensurePollingEntryPoints();
        }, 10000);
    }

    function stopPollingEntryPoints() {
        if (pollTimeout.value) {
            clearTimeout(pollTimeout.value);
        }
        pollTimeout.value = null;
    }

    async function fetchEntryPoints() {
        stopPollingEntryPoints();
        const url = new URL(`api/entry_points`);
        const params = { running: true };

        try {
            const response = await axios.get(url.toString(), { params: params });
            updateEntryPoints(response.data);
        } catch (e) {
            rethrowSimple(e);
        }
    }

    function updateEntryPoints(data: EntryPoint[]) {
        const mergeEntryPoints = (original: EntryPoint, updated: EntryPoint) => {
            return { ...original, ...updated };
        };

        let hasChanged = entryPoints.value.length !== data.length ? true : false;

        if (entryPoints.value.length === 0) {
            entryPoints.value = data;
        } else {
            const newEntryPoints: EntryPoint[] = [];

            for (const ep of data) {
                const olderEntryPoint = entryPoints.value.filter((item) => item.id === ep.id)[0];
                if (!hasChanged && !isEqual(olderEntryPoint, ep)) {
                    hasChanged = true;
                }
                if (olderEntryPoint) {
                    newEntryPoints.push(mergeEntryPoints(olderEntryPoint, ep));
                }
            }

            if (hasChanged) {
                entryPoints.value = newEntryPoints;
            }
        }
    }

    function removeEntryPoint(toolId: string) {
        const index = entryPoints.value.findIndex((ep) => {
            return ep.id === toolId ? true : false;
        });

        if (index >= 0) {
            entryPoints.value.splice(index, 1);
        }
    }

    return {
        getEntryPointsForJob,
        getEntryPointsForHda,
        ensurePollingEntryPoints,
        stopPollingEntryPoints,
        fetchEntryPoints,
        updateEntryPoints,
        removeEntryPoint,
    };
});
