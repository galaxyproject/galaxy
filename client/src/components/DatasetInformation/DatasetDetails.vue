<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { onMounted, onUnmounted, ref } from "vue";

import { GalaxyApi, type HDADetailed, isAdminUser } from "@/api";
import { fetchDatasetDetails } from "@/api/datasets";
import { type JobDetails } from "@/api/jobs";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";
import { stateIsTerminal } from "@/utils/utils";

import DatasetStorage from "@/components/Dataset/DatasetStorage/DatasetStorage.vue";
import DatasetInformation from "@/components/DatasetInformation/DatasetInformation.vue";
import InheritanceChain from "@/components/InheritanceChain//InheritanceChain.vue";
import JobDependencies from "@/components/JobDependencies/JobDependencies.vue";
import JobDestinationParams from "@/components/JobDestinationParams/JobDestinationParams.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";
import JobMetrics from "@/components/JobMetrics/JobMetrics.vue";
import JobParameters from "@/components/JobParameters/JobParameters.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    datasetId: string;
}

const props = defineProps<Props>();

const { config, isConfigLoaded } = useConfig(true);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const loading = ref(false);
const jobTimeOut = ref<any>(null);
const jobDetails = ref<JobDetails>();
const dataset = ref<HDADetailed | null>(null);
const jobLoadingError = ref<string | null>(null);
const datasetLoadingError = ref<string | null>(null);

async function getDatasetDetails() {
    loading.value = true;
    try {
        const data = await fetchDatasetDetails({ id: props.datasetId });
        dataset.value = data;
    } catch (e) {
        datasetLoadingError.value = errorMessageAsString(e) || "Unable to fetch available dataset details.";
    } finally {
        loading.value = false;
    }
}

async function loadJobDetails() {
    const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}", {
        params: {
            path: { job_id: dataset.value?.creating_job! },
            query: { full: true },
        },
    });

    if (error) {
        jobLoadingError.value = errorMessageAsString(error);
        return;
    }

    if (stateIsTerminal(data)) {
        clearTimeout(jobTimeOut.value);
    } else {
        jobTimeOut.value = setTimeout(loadJobDetails, 3000);
    }

    jobDetails.value = data;
}

onMounted(async () => {
    await getDatasetDetails();

    const creatingJobId = dataset.value?.creating_job;
    if (creatingJobId) {
        await loadJobDetails();
    }
});

onUnmounted(() => {
    clearTimeout(jobTimeOut.value);
});
</script>

<template>
    <div aria-labelledby="dataset-details-heading">
        <h1 id="dataset-details-heading" class="sr-only">Dataset Details</h1>

        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan message="Loading dataset details..." />
        </BAlert>
        <BAlert v-else-if="datasetLoadingError" variant="error">
            {{ datasetLoadingError }}
        </BAlert>
        <div v-else-if="dataset">
            <div v-if="dataset.creating_job" class="details">
                <DatasetInformation :dataset="dataset" />

                <JobParameters dataset_type="hda" :dataset-id="datasetId" />

                <JobInformation :job_id="dataset.creating_job" />

                <DatasetStorage :dataset-id="datasetId" />

                <InheritanceChain :dataset-id="datasetId" :dataset-name="dataset.name ?? ''" />

                <JobMetrics
                    v-if="isConfigLoaded"
                    :dataset-id="datasetId"
                    :carbon-intensity="config.carbon_intensity"
                    :geographical-server-location-name="config.geographical_server_location_name"
                    :power-usage-effectiveness="config.power_usage_effectiveness"
                    :should-show-aws-estimate="config.aws_estimate"
                    :should-show-carbon-emission-estimates="config.carbon_emission_estimates" />

                <JobDestinationParams v-if="isAdminUser(currentUser)" :job-id="dataset.creating_job" />

                <span v-if="jobDetails && 'dependencies' in jobDetails">
                    <JobDependencies v-if="jobDetails.dependencies" :dependencies="jobDetails.dependencies" />
                </span>

                <div v-if="dataset.peek">
                    <h2 class="h-md">Dataset Peek</h2>

                    <div class="dataset-peek" v-html="dataset.peek" />
                </div>
            </div>

            <div v-if="!dataset.creating_job" class="details">
                <DatasetInformation :dataset="dataset" />

                <DatasetStorage :dataset-id="datasetId" />

                <div>
                    <h2 class="h-md">Job Not Found</h2>

                    <p>
                        No job associated with this dataset is recorded in Galaxy. Galaxy cannot determine full dataset
                        provenance and history for this dataset.
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.details {
    display: flex;
    flex-direction: column;
    gap: 1rem;

    .dataset-peek {
        word-break: break-all;
    }
}
</style>
