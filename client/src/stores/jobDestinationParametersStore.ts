import { defineStore } from "pinia";

import { GalaxyApi } from "@/api";
import { type JobDestinationParams } from "@/api/jobs";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimple } from "@/utils/simple-error";

export const useJobDestinationParametersStore = defineStore("jobDestinationParametersStore", () => {
    async function fetchJobDestinationParams(params: FetchParams): Promise<JobDestinationParams> {
        const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}/destination_params", {
            params: {
                path: { job_id: params.id },
            },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    const { storedItems, getItemById, isLoadingItem } = useKeyedCache<JobDestinationParams>(fetchJobDestinationParams);

    return {
        storedJobDestinationParameters: storedItems,
        getJobDestinationParams: getItemById,
        isLoadingJobDestinationParams: isLoadingItem,
    };
});
