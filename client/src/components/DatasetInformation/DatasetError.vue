<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { GalaxyApi, type HDADetailed } from "@/api";
import { fetchDatasetDetails } from "@/api/datasets";
import { type JobDetails, type JobInputSummary } from "@/api/jobs";
import { useMarkdown } from "@/composables/markdown";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import DatasetErrorDetails from "@/components/DatasetInformation/DatasetErrorDetails.vue";
import FormElement from "@/components/Form/FormElement.vue";
import GalaxyWizard from "@/components/GalaxyWizard.vue";

library.add(faBug);

interface Props {
    datasetId: string;
}

const props = defineProps<Props>();

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const message = ref("");
const jobLoading = ref(true);
const errorMessage = ref("");
const datasetLoading = ref(false);
const jobDetails = ref<JobDetails>();
const jobProblems = ref<JobInputSummary>();
const resultMessages = ref<string[][]>([]);
const dataset = ref<HDADetailed>();

const showForm = computed(() => {
    const noResult = !resultMessages.value.length;
    const hasError = resultMessages.value.some((msg) => msg[1] === "danger");

    return noResult || hasError;
});

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

async function submit(dataset?: HDADetailed, userEmailJob?: string | null) {
    if (!dataset) {
        errorMessage.value = "No dataset found.";
        return;
    }

    const { data, error } = await GalaxyApi().POST("/api/jobs/{job_id}/error", {
        params: {
            path: { job_id: dataset.creating_job },
        },
        body: {
            dataset_id: dataset.id,
            message: message.value,
            email: userEmailJob,
        },
    });

    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }

    resultMessages.value = data.messages;
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

            <h4 class="mb-3 h-md">What might have happened?</h4>
            <b-card>
                <GalaxyWizard view="error" :query="jobDetails.tool_stderr" context="tool_error" />
            </b-card>

            <h4 class="mb-3 h-md">Issue Report</h4>
            <BAlert v-for="(resultMessage, index) in resultMessages" :key="index" :variant="resultMessage[1]" show>
                <span v-html="renderMarkdown(resultMessage[0])" />
            </BAlert>

            <div v-if="showForm" id="dataset-error-form">
                <span class="mr-2 font-weight-bold">{{ localize("Your email address") }}</span>
                <span v-if="currentUser?.email">{{ currentUser.email }}</span>
                <span v-else>{{ localize("You must be logged in to receive emails") }}</span>

                <FormElement
                    id="dataset-error-message"
                    v-model="message"
                    :area="true"
                    title="Please provide detailed information on the activities leading to this issue:" />

                <BButton
                    id="dataset-error-submit"
                    variant="primary"
                    class="mt-3"
                    @click="submit(dataset, jobDetails?.user_email)">
                    <FontAwesomeIcon :icon="faBug" class="mr-1" />
                    Report
                </BButton>
            </div>
        </div>
    </div>
</template>
