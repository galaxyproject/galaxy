import { defineStore } from "pinia";
import { computed, ref, set } from "vue";

import { GalaxyApi } from "@/api/client";
import type { JobMetric } from "@/api/jobs";
import { rethrowSimpleWithStatus } from "@/utils/simple-error";

export const useJobMetricsStore = defineStore("jobMetricsStore", () => {
    const jobMetricsByHdaId = ref<Record<string, JobMetric[]>>({});
    const jobMetricsByLddaId = ref<Record<string, JobMetric[]>>({});
    const jobMetricsByJobId = ref<Record<string, JobMetric[]>>({});

    const getJobMetricsByDatasetId = computed(() => {
        return (datasetId: string, datasetType = "hda") => {
            const jobMetricsObject = datasetType === "hda" ? jobMetricsByHdaId : jobMetricsByLddaId;
            return jobMetricsObject.value[datasetId] ?? [];
        };
    });

    const getJobMetricsByJobId = computed(() => {
        return (jobId: string) => {
            return jobMetricsByJobId.value[jobId] ?? [];
        };
    });

    async function fetchJobMetricsForDatasetId(datasetId: string, datasetType: "hda" | "ldda" = "hda") {
        if (jobMetricsByHdaId.value[datasetId] || jobMetricsByLddaId.value[datasetId]) {
            return;
        }

        const { data, error, response } = await GalaxyApi().GET("/api/datasets/{dataset_id}/metrics", {
            params: { path: { dataset_id: datasetId }, query: { hda_ldda: datasetType } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        const jobMetricsObject = datasetType === "hda" ? jobMetricsByHdaId : jobMetricsByLddaId;

        set(jobMetricsObject.value, datasetId, data);
    }

    async function fetchJobMetricsForJobId(jobId: string) {
        if (jobMetricsByJobId.value[jobId]) {
            return;
        }

        const { data, error, response } = await GalaxyApi().GET("/api/jobs/{job_id}/metrics", {
            params: { path: { job_id: jobId } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }

        set(jobMetricsByJobId.value, jobId, data);
    }

    return {
        jobMetricsByHdaId,
        jobMetricsByLddaId,
        jobMetricsByJobId,

        getJobMetricsByDatasetId,
        getJobMetricsByJobId,

        fetchJobMetricsForJobId,
        fetchJobMetricsForDatasetId,
    };
});
