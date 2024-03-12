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
                        <DatasetInformation :hda_id="datasetId" />
                        <JobParameters dataset_type="hda" :dataset-id="datasetId" />
                        <JobInformation :job_id="dataset.creating_job" />
                        <DatasetStorage :dataset-id="datasetId" />
                        <InheritanceChain :dataset-id="datasetId" :dataset-name="dataset.name" />
                        <JobMetrics v-if="isConfigLoaded" :dataset-id="datasetId" />
                        <JobDestinationParams v-if="currentUser.is_admin" :job-id="dataset.creating_job" />
                        <JobDependencies :dependencies="job.dependencies"></JobDependencies>
                        <div v-if="dataset.peek">
                            <h2 class="h-md">Dataset Peek</h2>
                            <div v-html="dataset.peek" />
                        </div>
                    </div>
                </JobDetailsProvider>
                <div v-else-if="!isDatasetLoading" class="details">
                    <DatasetInformation :hda_id="datasetId" />
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

<script>
import { mapState } from "pinia";

import Alert from "@/components/Alert";
import DatasetStorage from "@/components/Dataset/DatasetStorage/DatasetStorage";
import DatasetInformation from "@/components/DatasetInformation/DatasetInformation";
import JobDependencies from "@/components/JobDependencies/JobDependencies";
import JobDestinationParams from "@/components/JobDestinationParams/JobDestinationParams";
import JobInformation from "@/components/JobInformation/JobInformation";
import JobMetrics from "@/components/JobMetrics/JobMetrics";
import JobParameters from "@/components/JobParameters/JobParameters";
import LoadingSpan from "@/components/LoadingSpan";
import { DatasetProvider } from "@/components/providers";
import { JobDetailsProvider } from "@/components/providers/JobProvider";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

import InheritanceChain from "../InheritanceChain/InheritanceChain";

export default {
    components: {
        Alert,
        JobParameters,
        InheritanceChain,
        LoadingSpan,
        DatasetStorage,
        DatasetInformation,
        JobInformation,
        JobMetrics,
        JobDependencies,
        JobDestinationParams,
        DatasetProvider,
        JobDetailsProvider,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
    },
};
</script>

<style scoped>
.tool-title {
    text-align: center;
}
.details {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
</style>
