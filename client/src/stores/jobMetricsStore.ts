import axios from "axios";
import { defineStore } from "pinia";
import Vue, { computed, ref } from "vue";

import type { JobMetric } from "@/api/jobs";
import { prependPath } from "@/utils/redirect";

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

    async function fetchJobMetricsForDatasetId(datasetId: string, datasetType = "hda") {
        if (jobMetricsByHdaId.value[datasetId] || jobMetricsByLddaId.value[datasetId]) {
            return;
        }

        const path = prependPath(`api/datasets/${datasetId}/metrics?hda_ldda=${datasetType}`);
        const jobMetrics = (await axios.get<JobMetric[]>(path)).data;
        const jobMetricsObject = datasetType == "hda" ? jobMetricsByHdaId : jobMetricsByLddaId;

        Vue.set(jobMetricsObject.value, datasetId, jobMetrics);
    }

    async function fetchJobMetricsForJobId(jobId: string) {
        if (jobMetricsByJobId.value[jobId]) {
            return;
        }

        const path = prependPath(`api/jobs/${jobId}/metrics`);
        const jobMetrics = (await axios.get<JobMetric[]>(path)).data;

        Vue.set(jobMetricsByJobId.value, jobId, jobMetrics);
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
