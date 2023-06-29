<template>
    <ConfigProvider v-slot="{ config }">
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
                            <dataset-information :hda_id="datasetId" />
                            <job-parameters dataset_type="hda" :dataset-id="datasetId" />
                            <job-information :job_id="dataset.creating_job" />
                            <dataset-storage :dataset-id="datasetId" />
                            <inheritance-chain :dataset-id="datasetId" :dataset-name="dataset.name" />
                            <job-metrics
                                v-if="config"
                                :should-show-aws-estimate="config.aws_estimate"
                                :dataset-id="datasetId" />
                            <job-destination-params v-if="currentUser.is_admin" :job-id="dataset.creating_job" />
                            <job-dependencies :dependencies="job.dependencies"></job-dependencies>
                            <div v-if="dataset.peek">
                                <h2 class="h-md">Dataset Peek</h2>
                                <div v-html="dataset.peek" />
                            </div>
                        </div>
                    </JobDetailsProvider>
                    <div v-else-if="!isDatasetLoading" class="details">
                        <dataset-information :hda_id="datasetId" />
                        <dataset-storage :dataset-id="datasetId" />
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
    </ConfigProvider>
</template>

<script>
import Alert from "components/Alert";
import DatasetStorage from "components/Dataset/DatasetStorage/DatasetStorage";
import DatasetInformation from "components/DatasetInformation/DatasetInformation";
import JobDependencies from "components/JobDependencies/JobDependencies";
import JobDestinationParams from "components/JobDestinationParams/JobDestinationParams";
import JobInformation from "components/JobInformation/JobInformation";
import JobMetrics from "components/JobMetrics/JobMetrics";
import JobParameters from "components/JobParameters/JobParameters";
import LoadingSpan from "components/LoadingSpan";
import { DatasetProvider } from "components/providers";
import ConfigProvider from "components/providers/ConfigProvider";
import { JobDetailsProvider } from "components/providers/JobProvider";
import { mapState } from "pinia";

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
        ConfigProvider,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
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
