<template>
    <ConfigProvider v-slot="{ config }">
        <DatasetProvider
            :id="datasetId"
            v-slot="{ result: dataset, loading: isDatasetLoading, error: datasetLoadingError }">
            <div aria-labelledby="dataset-details-heading">
                <h1 id="dataset-details-heading" class="sr-only">Dataset Details</h1>
                <LoadingSpan v-if="isDatasetLoading" />
                <Alert v-else-if="datasetLoadingError" :message="datasetLoadingError" variant="error" />
                <CurrentUser v-else v-slot="{ user }">
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
                            <job-metrics v-if="config" :aws_estimate="config.aws_estimate" :dataset-id="datasetId" />
                            <job-destination-params v-if="user.is_admin" :job-id="dataset.creating_job" />
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
                </CurrentUser>
            </div>
        </DatasetProvider>
    </ConfigProvider>
</template>

<script>
import DatasetInformation from "components/DatasetInformation/DatasetInformation";
import JobInformation from "components/JobInformation/JobInformation";
import JobDestinationParams from "components/JobDestinationParams/JobDestinationParams";
import LoadingSpan from "components/LoadingSpan";
import DatasetStorage from "components/Dataset/DatasetStorage/DatasetStorage";
import InheritanceChain from "../InheritanceChain/InheritanceChain";
import JobParameters from "components/JobParameters/JobParameters";
import JobMetrics from "components/JobMetrics/JobMetrics";
import JobDependencies from "components/JobDependencies/JobDependencies";
import { DatasetProvider } from "components/providers";
import { JobDetailsProvider } from "components/providers/JobProvider";
import ConfigProvider from "components/providers/ConfigProvider";
import CurrentUser from "components/providers/CurrentUser";
import Alert from "components/Alert";

export default {
    components: {
        Alert,
        CurrentUser,
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
