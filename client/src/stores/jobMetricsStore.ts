import axios from "axios";
import { defineStore } from "pinia";
import { prependPath } from "@/utils/redirect";
import Vue, { computed, ref } from "vue";

interface JobMertic {
    title: string;
    value: string;
    plugin: string;
    name: string;
    raw_value: string;
}

export const useJobMetricsStore = defineStore("jobMetricsStore", () => {
    const jobMetricsByHdaId = ref<Record<string, JobMertic[]>>({});
    const jobMetricsByLddaId = ref<Record<string, JobMertic[]>>({});
    const jobMetricsByJobId = ref<Record<string, JobMertic[]>>({});

    const getJobMetricsByDatasetId = computed(() => {
        return (datasetId: string, datasetType = "hda") => {
            const jobMetricsObject = datasetType == "hda" ? jobMetricsByHdaId : jobMetricsByLddaId;
            return jobMetricsObject.value[datasetId] || ([] as JobMertic[]);
        };
    });

    const getJobMetricsByJobId = computed(() => {
        return (jobId: string) => {
            return jobMetricsByJobId.value[jobId] || ([] as JobMertic[]);
        };
    });

    async function fetchJobMetricsForDatasetId(datasetId: string, datasetType = "hda") {
        if (jobMetricsByHdaId.value[datasetId] || jobMetricsByLddaId.value[datasetId]) {
            return;
        }

        const jobMetrics = (await axios.get(prependPath(`api/datasets/${datasetId}/metrics?hda_ldda=${datasetType}`)))
            .data as JobMertic[];
        const jobMetricsObject = datasetType == "hda" ? jobMetricsByHdaId : jobMetricsByLddaId;

        Vue.set(jobMetricsObject.value, datasetId, jobMetrics);
    }

    async function fetchJobMetricsForJobId(jobId: string) {
        if (jobMetricsByJobId.value[jobId]) {
            return;
        }

        const jobMetrics = (await axios.get(prependPath(`api/jobs/${jobId}/metrics`))).data as JobMertic[];

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
