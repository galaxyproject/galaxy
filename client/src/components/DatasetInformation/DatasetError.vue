<template>
    <div>
        <b-alert v-if="errorMessage" variant="danger" show>
            <h4 class="alert-heading">Failed to access Dataset details.</h4>
            {{ errorMessage }}
        </b-alert>
        <DatasetProvider :id="datasetId" v-slot="{ result: dataset, loading: datasetLoading }">
            <JobDetailsProvider
                v-if="!datasetLoading"
                v-slot="{ result: jobDetails, loading }"
                :jobid="dataset.creating_job"
                @error="onError">
                <div v-if="!loading">
                    <div class="page-container edit-attr">
                        <div class="response-message"></div>
                    </div>
                    <h2>Dataset Error Report</h2>
                    <p>
                        An error occurred while running the tool
                        <b id="dataset-error-tool-id" class="text-break">{{ jobDetails.tool_id }}</b
                        >.
                    </p>
                    <DatasetErrorDetails
                        :tool-stderr="jobDetails.tool_stderr"
                        :job-stderr="jobDetails.job_stderr"
                        :job-messages="jobDetails.job_messages" />
                    <JobProblemProvider v-slot="{ result: jobProblems }" :jobid="dataset.creating_job" @error="onError">
                        <div v-if="jobProblems && (jobProblems.has_duplicate_inputs || jobProblems.has_empty_inputs)">
                            <h3 class="common_problems mt-3">Detected Common Potential Problems</h3>
                            <p v-if="jobProblems.has_empty_inputs" id="dataset-error-has-empty-inputs">
                                The tool was executed with one or more empty input datasets. This frequently results in
                                tool errors due to problematic input choices.
                            </p>
                            <p v-if="jobProblems.has_duplicate_inputs" id="dataset-error-has-duplicate-inputs">
                                The tool was executed with one or more duplicate input datasets. This frequently results
                                in tool errors due to problematic input choices.
                            </p>
                        </div>
                    </JobProblemProvider>
                    <h3 class="mt-3">Troubleshooting</h3>
                    <p>
                        There are a number of helpful resources to self diagnose and correct problems.
                        <br />
                        Start here:
                        <b>
                            <a
                                href="https://training.galaxyproject.org/training-material/faqs/galaxy/#troubleshooting-errors"
                                target="_blank">
                                My job ended with an error. What can I do?
                            </a>
                        </b>
                    </p>
                    <h3 class="mb-3">Issue Report</h3>
                    <b-alert
                        v-for="(resultMessage, index) in resultMessages"
                        :key="index"
                        :variant="resultMessage[1]"
                        show
                        >{{ resultMessage[0] }}</b-alert
                    >
                    <div v-if="showForm" id="fieldsAndButton">
                        <FormElement
                            v-if="!jobDetails.user_email"
                            id="dataset-error-email"
                            v-model="email"
                            title="Please provide your email:" />
                        <FormElement
                            id="dataset-error-message"
                            v-model="message"
                            :area="true"
                            title="Please provide detailed information on the activities leading to this issue:" />
                        <b-button
                            id="dataset-error-submit"
                            variant="primary"
                            class="mt-3"
                            @click="submit(dataset, jobDetails.user_email)">
                            <font-awesome-icon icon="bug" class="mr-1" />Report
                        </b-button>
                    </div>
                </div>
            </JobDetailsProvider>
        </DatasetProvider>
    </div>
</template>

<script>
import DatasetErrorDetails from "./DatasetErrorDetails";
import FormElement from "components/Form/FormElement";
import { DatasetProvider } from "components/providers";
import { JobDetailsProvider, JobProblemProvider } from "components/providers/JobProvider";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug } from "@fortawesome/free-solid-svg-icons";
import { sendErrorReport } from "./services";

library.add(faBug);

export default {
    components: {
        DatasetProvider,
        DatasetErrorDetails,
        FontAwesomeIcon,
        FormElement,
        JobDetailsProvider,
        JobProblemProvider,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            message: null,
            email: null,
            errorMessage: null,
            resultMessages: [],
        };
    },
    computed: {
        showForm() {
            const noResult = !this.resultMessages.length;
            const hasError = this.resultMessages.some((msg) => msg[1] === "danger");
            return noResult || hasError;
        },
    },
    methods: {
        onError(err) {
            this.errorMessage = err;
        },
        submit(dataset, userEmail) {
            const email = this.email || userEmail;
            const message = this.message;
            sendErrorReport(dataset, message, email).then(
                (resultMessages) => {
                    this.resultMessages = resultMessages;
                },
                (errorMessage) => {
                    this.errorMessage = errorMessage;
                }
            );
        },
    },
};
</script>
