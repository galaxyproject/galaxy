import { defineStore } from "pinia";

import { fetchJobDestinationParams, type JobDestinationParams } from "@/api/jobs";
import { useKeyedCache } from "@/composables/keyedCache";

export const useJobDestinationParametersStore = defineStore("jobDestinationParametersStore", () => {
    const { storedItems, getItemById, isLoadingItem } = useKeyedCache<JobDestinationParams>((params) =>
        fetchJobDestinationParams({ job_id: params.id })
    );

    return {
        storedJobDestinationParameters: storedItems,
        getJobDestinationParams: getItemById,
        isLoadingJobDestinationParams: isLoadingItem,
    };
});
