<template>
    <ConfigProvider v-slot="{ config }">
        <DatasetProvider :id="datasetId" v-slot="{ item: dataset, loading: isDatasetLoading }">
            <JobDetailsProvider
                v-if="!isDatasetLoading"
                :jobid="dataset.creating_job"
                v-slot="{ result: job, loading: isJobLoading }"
            >
                <div v-if="!isJobLoading">
                    <h2 class="tool-title">{{ job.tool_name }}</h2>
                    <dataset-information :hda_id="datasetId" />
                    <job-parameters dataset_type="hda" :dataset-id="datasetId" />
                    <job-information :job_id="dataset.creating_job" @current_tool_name="tool_name = $event" />
                    <dataset-storage :dataset-id="datasetId" />
                    <inheritance-chain :dataset-id="datasetId" :dataset-name="dataset.name" />
                    <job-metrics v-if="config" :aws_estimate="config.aws_estimate" :dataset-id="datasetId" />
                    <job-destination-params :job-id="dataset.creating_job" />
                    <job-dependencies :dependencies="job.dependencies"></job-dependencies>
                    <div v-if="dataset.peek">
                        <h3>Dataset Peek:</h3>
                        <div v-html="dataset.peek" />
                    </div>
                </div>
            </JobDetailsProvider>
        </DatasetProvider>
    </ConfigProvider>
</template>

<script>
import DatasetInformation from "components/DatasetInformation/DatasetInformation";
import JobInformation from "components/JobInformation/JobInformation";
import JobDestinationParams from "components/JobDestinationParams/JobDestinationParams";
import DatasetStorage from "components/Dataset/DatasetStorage/DatasetStorage";
import InheritanceChain from "../InheritanceChain/InheritanceChain";
import JobParameters from "components/JobParameters/JobParameters";
import JobMetrics from "components/JobMetrics/JobMetrics";
import JobDependencies from "components/JobDependencies/JobDependencies";
import { DatasetProvider } from "components/providers";
import { JobDetailsProvider } from "components/providers/JobProvider";
import ConfigProvider from "components/providers/ConfigProvider";

export default {
    components: {
        JobParameters,
        InheritanceChain,
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
</style>
