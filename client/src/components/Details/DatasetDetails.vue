<template>
    <ConfigProvider v-slot="{ config }">
        <DatasetProvider
            :id="datasetId"
            v-slot="{ item: dataset, loading: isDatasetLoading, error: datasetLoadingError }">
            <div>
                <LoadingSpan v-if="isDatasetLoading" />
                <Alert v-else-if="datasetLoadingError" :message="datasetLoadingError" variant="error" />
                <CurrentUser v-else v-slot="{ user }">
                    <JobDetailsProvider
                        v-if="!isDatasetLoading && dataset.creating_job !== null"
                        :jobid="dataset.creating_job"
                        v-slot="{ result: job, loading: isJobLoading }"
                        :use-cache="false">
                        <div v-if="!isJobLoading">
                            <dataset-information class="detail" :hda_id="datasetId" />
                            <job-parameters class="detail" dataset_type="hda" :dataset-id="datasetId" />
                            <job-information class="detail" :job_id="dataset.creating_job" />
                            <dataset-storage class="detail" :dataset-id="datasetId" />
                            <inheritance-chain class="detail" :dataset-id="datasetId" :dataset-name="dataset.name" />
                            <job-metrics
                                class="detail"
                                v-if="config"
                                :aws_estimate="config.aws_estimate"
                                :dataset-id="datasetId" />
                            <job-destination-params
                                class="detail"
                                v-if="user.is_admin"
                                :job-id="dataset.creating_job" />
                            <job-dependencies class="detail" :dependencies="job.dependencies"></job-dependencies>
                            <div class="detail" v-if="dataset.peek">
                                <h3>Dataset Peek:</h3>
                                <div v-html="dataset.peek" />
                            </div>
                        </div>
                    </JobDetailsProvider>
                    <div v-else-if="!isDatasetLoading">
                        <dataset-information class="detail" :hda_id="datasetId" />
                        <dataset-storage class="detail" :dataset-id="datasetId" />
                        <div>
                            <h3>Job Not Found</h3>
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
.detail {
    padding-top: 0.6rem;
}
</style>
