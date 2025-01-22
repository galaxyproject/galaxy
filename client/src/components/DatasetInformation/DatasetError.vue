<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug } from "@fortawesome/free-solid-svg-icons";
import { BAlert, BCard } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { GalaxyApi, type HDADetailed } from "@/api";
import { fetchDatasetDetails } from "@/api/datasets";
import { type JobDetails, type JobInputSummary } from "@/api/jobs";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import UserReportingError from "../Collections/common/UserReportingError.vue";
import DatasetErrorDetails from "@/components/DatasetInformation/DatasetErrorDetails.vue";
import GalaxyWizard from "@/components/GalaxyWizard.vue";

library.add(faBug);

interface Props {
    datasetId: string;
}

const props = defineProps<Props>();
const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const { config, isConfigLoaded } = useConfig();

const jobLoading = ref(true);
const errorMessage = ref("");
const datasetLoading = ref(false);
const jobDetails = ref<JobDetails>();
const jobProblems = ref<JobInputSummary>();
const dataset = ref<HDADetailed>();

const showWizard = computed(() => isConfigLoaded && config.value?.llm_api_configured);

async function getDatasetDetails() {
    datasetLoading.value = true;
    try {
        const data = await fetchDatasetDetails({ id: props.datasetId });
        dataset.value = data;
    } catch (e) {
        errorMessage.value = errorMessageAsString(e) || "Unable to fetch available dataset details.";
    } finally {
        datasetLoading.value = false;
    }
}

async function getJobDetails(jobId: string) {
    jobLoading.value = true;
    try {
        const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}", {
            params: {
                path: { job_id: jobId },
                query: { full: true },
            },
        });

        if (error) {
            errorMessage.value = errorMessageAsString(error) || "Unable to fetch job details.";
            return;
        }

        jobDetails.value = data;
    } finally {
        jobLoading.value = false;
    }
}

async function getJobProblems(jobId: string) {
    const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}/common_problems", {
        params: {
            path: { job_id: jobId },
        },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error) || "Unable to fetch job problems.";
        return;
    }
    jobProblems.value = data;
}

function onMissingJobId() {
    errorMessage.value = "No job ID found for this dataset.";
}

onMounted(async () => {
    await getDatasetDetails();

    const creatingJobId = dataset.value?.creating_job;
    if (!creatingJobId) {
        onMissingJobId();
        return;
    }
    await getJobDetails(creatingJobId);
    await getJobProblems(creatingJobId);
});
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" variant="danger" show>
            <h2 class="alert-heading h-sm">Failed to access Dataset details.</h2>
            {{ errorMessage }}
        </BAlert>

        <div v-if="!datasetLoading && !jobLoading && dataset && jobDetails">
            <div class="page-container edit-attr">
                <div class="response-message"></div>
            </div>

            <h3 class="h-lg">Dataset Error Report</h3>

            <p>
                An error occurred while running the tool
                <b id="dataset-error-tool-id" class="text-break">{{ jobDetails.tool_id }}</b
                >.
            </p>
            <template v-if="showWizard">
                <h4 class="mb-3 h-md">Possible Causes</h4>
                <p>
                    <span>
                        We can use AI to analyze the issue and suggest possible fixes. Please note that the diagnosis
                        may not always be accurate.
                    </span>
                </p>
                <BCard class="mb-2">
                    <GalaxyWizard
                        view="error"
                        :query="jobDetails.tool_stderr"
                        context="tool_error"
                        :job-id="jobDetails.id" />
                </BCard>
            </template>

            <DatasetErrorDetails
                :tool-stderr="jobDetails.tool_stderr"
                :job-stderr="jobDetails.job_stderr"
                :job-messages="jobDetails.job_messages" />

            <div v-if="jobProblems && (jobProblems.has_duplicate_inputs || jobProblems.has_empty_inputs)">
                <h4 class="common_problems mt-3 h-md">Detected Common Potential Problems</h4>

                <p v-if="jobProblems.has_empty_inputs" id="dataset-error-has-empty-inputs">
                    The tool was started with one or more empty input datasets. This frequently results in tool errors
                    due to problematic input choices.
                </p>

                <p v-if="jobProblems.has_duplicate_inputs" id="dataset-error-has-duplicate-inputs">
                    The tool was started with one or more duplicate input datasets. This frequently results in tool
                    errors due to problematic input choices.
                </p>
            </div>

            <h4 class="mt-3 h-md">Troubleshooting</h4>

            <p>
                There are a number of helpful resources to self diagnose and correct problems.
                <br />
                Start here:
                <b>
                    <a
                        href="https://training.galaxyproject.org/training-material/faqs/galaxy/analysis_troubleshooting.html"
                        target="_blank">
                        My job ended with an error. What can I do?
                    </a>
                </b>
            </p>

            <h4 class="mb-3 h-md">Issue Report</h4>
            <UserReportingError
                report-type="dataset"
                :reportable-data="dataset"
                :reporting-email="currentUser?.email" />
        </div>
    </div>
</template>
