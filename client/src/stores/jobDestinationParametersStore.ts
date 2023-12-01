import { defineStore } from "pinia";
import { computed, del, ref, set } from "vue";

import { fetchJobDestinationParams, type JobDestinationParams } from "@/api/jobs";

export const useJobDestinationParametersStore = defineStore("jobDestinationParametersStore", () => {
    const storedJobDestinationParameters = ref<{ [key: string]: JobDestinationParams }>({});
    const loadingParameters = ref<{ [key: string]: boolean }>({});

    const getJobDestinationParams = computed(() => {
        return (jobId: string) => {
            const destinationParams = storedJobDestinationParameters.value[jobId];
            if (!destinationParams && !loadingParameters.value[jobId]) {
                fetchJobDestinationParamsByJobId({ id: jobId });
            }
            return destinationParams ?? null;
        };
    });

    const isLoadingJobDestinationParams = computed(() => {
        return (jobId: string) => {
            return loadingParameters.value[jobId] ?? false;
        };
    });

    async function fetchJobDestinationParamsByJobId(params: { id: string }) {
        const jobId = params.id;
        set(loadingParameters.value, jobId, true);
        try {
            const { data: destinationParams } = await fetchJobDestinationParams({ job_id: jobId });
            set(storedJobDestinationParameters.value, jobId, destinationParams);
            return destinationParams;
        } finally {
            del(loadingParameters.value, jobId);
        }
    }

    return {
        storedJobDestinationParameters,
        getJobDestinationParams,
        isLoadingJobDestinationParams,
    };
});
