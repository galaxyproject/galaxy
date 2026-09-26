/**
 * Cached fetcher for `/api/jobs/{job_id}/parameters_display`. The endpoint
 * carries both the tool parameter tree and the job outputs — naming follows
 * the established `jobStore` convention.
 */

import { defineStore } from "pinia";

import { GalaxyApi } from "@/api";
import type { JobDisplayParametersSummary } from "@/api/jobs";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimpleWithStatus } from "@/utils/simple-error";

export const useJobParametersStore = defineStore("jobParametersStore", () => {
    async function fetchJobParametersById(params: FetchParams): Promise<JobDisplayParametersSummary> {
        const { data, error, response } = await GalaxyApi().GET("/api/jobs/{job_id}/parameters_display", {
            params: { path: { job_id: params.id } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    const {
        fetchItemById: fetchJobParameters,
        getItemById: getJobParameters,
        getItemLoadError: getJobParametersLoadError,
        isLoadingItem: isLoadingJobParameters,
    } = useKeyedCache<JobDisplayParametersSummary>(fetchJobParametersById);

    return {
        fetchJobParameters,
        getJobParameters,
        getJobParametersLoadError,
        isLoadingJobParameters,
    };
});
