<script setup lang="ts">
import { storeToRefs } from "pinia";

import { DatasetProvider } from "@/components/providers";
import { JobDetailsProvider } from "@/components/providers/JobProvider";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

import Alert from "@/components/Alert.vue";
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

defineProps<Props>();

const { config, isConfigLoaded } = useConfig(true);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);
</script>

<template>
    <DatasetProvider
        :id="datasetId"
        v-slot="{ result: dataset, loading: isDatasetLoading, error: datasetLoadingError }">
        <div aria-labelledby="dataset-details-heading">
            <h1 id="dataset-details-heading" class="sr-only">Dataset Details</h1>

            <LoadingSpan v-if="isDatasetLoading" />
            <Alert v-else-if="datasetLoadingError" :message="datasetLoadingError" variant="error" />
            <div v-else>
                <JobDetailsProvider
                    v-if="!isDatasetLoading && dataset.creating_job !== null"
                    v-slot="{ result: job, loading: isJobLoading }"
                    :job-id="dataset.creating_job"
                    auto-refresh>
                    <div v-if="!isJobLoading" class="details">
                        <DatasetInformation :hda-id="datasetId" />

                        <JobParameters dataset_type="hda" :dataset-id="datasetId" />

                        <JobInformation :job_id="dataset.creating_job" />

                        <DatasetStorage :dataset-id="datasetId" />

                        <InheritanceChain :dataset-id="datasetId" :dataset-name="dataset.name" />

                        <JobMetrics
                            v-if="isConfigLoaded"
                            :dataset-id="datasetId"
                            :carbon-intensity="config.carbon_intensity"
                            :geographical-server-location-name="config.geographical_server_location_name"
                            :power-usage-effectiveness="config.power_usage_effectiveness"
                            :should-show-aws-estimate="config.aws_estimate"
                            :should-show-carbon-emission-estimates="config.carbon_emission_estimates" />

                        <JobDestinationParams v-if="currentUser?.is_admin" :job-id="dataset.creating_job" />

                        <JobDependencies :dependencies="job.dependencies"></JobDependencies>

                        <div v-if="dataset.peek">
                            <h2 class="h-md">Dataset Peek</h2>

                            <div v-html="dataset.peek" />
                        </div>
                    </div>
                </JobDetailsProvider>
                <div v-else-if="!isDatasetLoading" class="details">
                    <DatasetInformation :hda-id="datasetId" />

                    <DatasetStorage :dataset-id="datasetId" />

                    <div>
                        <h2 class="h-md">Job Not Found</h2>

                        <p>
                            No job associated with this dataset is recorded in Galaxy. Galaxy cannot determine full
                            dataset provenance and history for this dataset.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </DatasetProvider>
</template>

<style scoped>
.details {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
</style>
