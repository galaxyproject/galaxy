<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { DatasetDetails } from "@/api";
import { DatasetProvider } from "@/components/providers";
import { JobDetailsProvider, JobProblemProvider } from "@/components/providers/JobProvider";
import { useMarkdown } from "@/composables/markdown";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import { sendErrorReport } from "./services";

import DatasetErrorDetails from "@/components/DatasetInformation/DatasetErrorDetails.vue";
import FormElement from "@/components/Form/FormElement.vue";

library.add(faBug);

interface Props {
    datasetId: string;
}

defineProps<Props>();

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const message = ref("");
const errorMessage = ref("");
const resultMessages = ref<string[][]>([]);

const showForm = computed(() => {
    const noResult = !resultMessages.value.length;
    const hasError = resultMessages.value.some((msg) => msg[1] === "danger");

    return noResult || hasError;
});

function onError(err: string) {
    errorMessage.value = err;
}

function submit(dataset: DatasetDetails, userEmailJob: string) {
    const email = userEmailJob;

    sendErrorReport(dataset.creating_job, { dataset_id: dataset.id, message: message.value, email }).then(
        (resMsg) => {
            resultMessages.value = resMsg;
        },
        (errMsg) => {
            errorMessage.value = errMsg;
        }
    );
}
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" variant="danger" show>
            <h2 class="alert-heading h-sm">Failed to access Dataset details.</h2>
            {{ errorMessage }}
        </BAlert>

        <DatasetProvider :id="datasetId" v-slot="{ result: dataset, loading: datasetLoading }">
            <JobDetailsProvider
                v-if="!datasetLoading"
                v-slot="{ result: jobDetails, loading }"
                :job-id="dataset.creating_job"
                @error="onError">
                <div v-if="!loading">
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

                    <JobProblemProvider
                        v-slot="{ result: jobProblems }"
                        :job-id="dataset.creating_job"
                        @error="onError">
                        <div v-if="jobProblems && (jobProblems.has_duplicate_inputs || jobProblems.has_empty_inputs)">
                            <h4 class="common_problems mt-3 h-md">Detected Common Potential Problems</h4>

                            <p v-if="jobProblems.has_empty_inputs" id="dataset-error-has-empty-inputs">
                                The tool was started with one or more empty input datasets. This frequently results in
                                tool errors due to problematic input choices.
                            </p>

                            <p v-if="jobProblems.has_duplicate_inputs" id="dataset-error-has-duplicate-inputs">
                                The tool was started with one or more duplicate input datasets. This frequently results
                                in tool errors due to problematic input choices.
                            </p>
                        </div>
                    </JobProblemProvider>

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

                    <BAlert
                        v-for="(resultMessage, index) in resultMessages"
                        :key="index"
                        :variant="resultMessage[1]"
                        show>
                        <span v-html="renderMarkdown(resultMessage[0])" />
                    </BAlert>

                    <div v-if="showForm" id="fieldsAndButton">
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
                            @click="submit(dataset, jobDetails.user_email)">
                            <FontAwesomeIcon :icon="faBug" class="mr-1" />
                            Report
                        </BButton>
                    </div>
                </div>
            </JobDetailsProvider>
        </DatasetProvider>
    </div>
</template>
