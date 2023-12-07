import { defineStore } from "pinia";

import { fetchJobDestinationParams, type JobDestinationParams } from "@/api/jobs";
import { useSimpleKeyStore } from "@/composables/simpleKeyStore";

export const useJobDestinationParametersStore = defineStore("jobDestinationParametersStore", () => {
    const { storedItems, getItemById, isLoadingItem } = useSimpleKeyStore<JobDestinationParams>((params) =>
        fetchJobDestinationParams({ job_id: params.id })
    );

    return {
        storedJobDestinationParameters: storedItems,
        getJobDestinationParams: getItemById,
        isLoadingJobDestinationParams: isLoadingItem,
    };
});
