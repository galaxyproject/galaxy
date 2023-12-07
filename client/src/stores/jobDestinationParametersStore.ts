import { defineStore } from "pinia";

import { fetchJobDestinationParams, type JobDestinationParams } from "@/api/jobs";
import { useSimpleStore } from "@/composables/simpleStore";

export const useJobDestinationParametersStore = defineStore("jobDestinationParametersStore", () => {
    const { storedItems, getItemById, isLoadingItem } = useSimpleStore<JobDestinationParams>((params) =>
        fetchJobDestinationParams({ job_id: params.id })
    );

    return {
        storedJobDestinationParameters: storedItems,
        getJobDestinationParams: getItemById,
        isLoadingJobDestinationParams: isLoadingItem,
    };
});
